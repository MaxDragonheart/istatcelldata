"""H3 area-weighted estimation for ISTAT census section indicators."""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import math
import tempfile
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeAlias

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from istat_census_data.catalog import get_census_index_catalog

WGS84_CRS = "EPSG:4326"
DEFAULT_AREA_CRS = "EPSG:3035"
REQUIRED_H3_RESOLUTION = 11
DEFAULT_SPECIAL_SECTION_POLICY = "exclude"
SPECIAL_SECTION_POLICIES = ("include", "exclude", "raise")
# ISTAT special or fictitious census-section codes. These rows can contain valid
# census variables, but their geometry is conventional or administrative rather
# than a normal residential section. See package geodata docs for details.
SPECIAL_SECTION_MARKERS = ("7777777", "888888", "999999")
SECTION_CODE_COLUMNS = (
    "SEZ2021",
    "SEZ2011",
    "SEZ2001",
    "SEZ1991",
    "SEZ21_ID",
    "SEZ21",
    "NSEZ",
    "SEZ",
)
MUNICIPALITY_CODE_COLUMNS = ("PRO_COM", "PROCOM", "PRO_COM_T", "CODCOM", "COD_COM")
DEFAULT_H3_WORKERS = 1
DEFAULT_H3_CHUNK_SIZE = 5000
DEFAULT_BOUNDARY_RING_SIZE = 3
DEFAULT_PARALLEL_BACKEND = "thread"
PARALLEL_BACKENDS = ("thread", "process", "dask")
DEFAULT_INTERMEDIATE_STORAGE = "parquet"
INTERMEDIATE_STORAGE_MODES = ("memory", "parquet")
INTERMEDIATE_SCHEMA_VERSION = 2

GeoInput: TypeAlias = BaseGeometry | gpd.GeoDataFrame | gpd.GeoSeries

logger = logging.getLogger(__name__)


def generate_h3_grid(
    aoi: GeoInput,
    h3_resolution: int = REQUIRED_H3_RESOLUTION,
    *,
    aoi_crs: str | int | None = WGS84_CRS,
    area_crs: str | int = DEFAULT_AREA_CRS,
    boundary_ring_size: int = DEFAULT_BOUNDARY_RING_SIZE,
    output_crs: str | int = WGS84_CRS,
) -> gpd.GeoDataFrame:
    """Generate H3 cell polygons intersecting an area of interest.

    H3 polygon filling uses cell centres. This function expands the filled cells
    by neighbour rings and then keeps only cells that intersect the AOI, so
    boundary cells are retained for area-weighted overlays.

    Args:
        aoi: Area of interest as a Shapely geometry, GeoSeries, or GeoDataFrame.
        h3_resolution: Required H3 resolution. This implementation supports
            only level 11.
        aoi_crs: CRS to use when `aoi` is a plain Shapely geometry or when a
            GeoSeries/GeoDataFrame has no CRS. Defaults to EPSG:4326.
        area_crs: Projected CRS used to calculate `h3_cell_area_sqm`.
        boundary_ring_size: Number of H3 neighbour rings added around filled
            cells before final AOI intersection filtering. Defaults to 3 to
            retain boundary cells reliably for real administrative AOIs.
        output_crs: CRS for returned cell geometries. Defaults to EPSG:4326.

    Returns:
        GeoDataFrame with `h3_index`, `h3_resolution`, `h3_cell_area_sqm`, and
        polygon geometries.

    Raises:
        TypeError: If the AOI input type is unsupported.
        ValueError: If the AOI is empty, CRS is missing, or the resolution is invalid.
    """
    _validate_h3_resolution(h3_resolution)
    if boundary_ring_size < 0:
        raise ValueError("boundary_ring_size must be greater than or equal to 0.")

    aoi_gdf = _normalize_aoi(aoi=aoi, aoi_crs=aoi_crs)
    aoi_wgs84 = aoi_gdf.to_crs(WGS84_CRS)
    aoi_geometry_wgs84 = _union_geometry(aoi_wgs84.geometry)

    candidate_cells = _candidate_h3_cells(
        aoi_geometry=aoi_geometry_wgs84,
        h3_resolution=h3_resolution,
        boundary_ring_size=boundary_ring_size,
    )
    rows = []
    for h3_index in sorted(candidate_cells):
        cell_geometry = _h3_cell_to_polygon(h3_index)
        if cell_geometry.intersects(aoi_geometry_wgs84):
            rows.append({"h3_index": h3_index, "geometry": cell_geometry})

    if not rows:
        raise ValueError("No H3 cells intersect the AOI at the requested resolution.")

    grid_wgs84 = gpd.GeoDataFrame(rows, geometry="geometry", crs=WGS84_CRS)
    grid_area = grid_wgs84.to_crs(area_crs)
    grid_wgs84["h3_resolution"] = h3_resolution
    grid_wgs84["h3_cell_area_sqm"] = grid_area.geometry.area

    return grid_wgs84.to_crs(output_crs).reset_index(drop=True)


def estimate_h3_census_indexes(
    census_data_path: str | Path,
    year: int,
    aoi: GeoInput,
    h3_resolution: int = REQUIRED_H3_RESOLUTION,
    *,
    indexes: str | Iterable[str] | None = "all_additive",
    aoi_crs: str | int | None = WGS84_CRS,
    area_crs: str | int = DEFAULT_AREA_CRS,
    layer_name: str | None = None,
    municipality_codes: Iterable[int | str] | None = None,
    special_section_policy: str = DEFAULT_SPECIAL_SECTION_POLICY,
    boundary_ring_size: int = DEFAULT_BOUNDARY_RING_SIZE,
    include_density: bool = True,
    clip_output: bool = False,
    output_crs: str | int = WGS84_CRS,
    output_path: str | Path | None = None,
    output_layer: str | None = None,
    conservation_tolerance: float = 1e-6,
    workers: int = DEFAULT_H3_WORKERS,
    chunk_size: int = DEFAULT_H3_CHUNK_SIZE,
    parallel_backend: str = DEFAULT_PARALLEL_BACKEND,
    intermediate_storage: str = DEFAULT_INTERMEDIATE_STORAGE,
    intermediate_dir: str | Path | None = None,
    keep_intermediates: bool = False,
    reuse_intermediates: bool = False,
) -> gpd.GeoDataFrame:
    """Estimate additive census indicators on an H3 grid.

    Values are distributed from source census sections to H3 cells using uniform
    density inside each source section:

    ```text
    contribution = source_value * intersection_area / source_cell_area
    ```

    Args:
        census_data_path: Path to the finalized `census_data.gpkg` file.
        year: Census year to read from layer `census<year>` unless `layer_name`
            is provided.
        aoi: Area of interest as a Shapely geometry, GeoSeries, or GeoDataFrame.
        h3_resolution: Required H3 resolution. This implementation supports
            only level 11.
        indexes: Source index codes or canonical catalogue IDs to estimate. The
            default `"all_additive"` selects additive source codes present in the
            layer using the packaged census index catalogue. An empty iterable
            also selects all available additive indexes.
        aoi_crs: CRS to use when `aoi` is a plain Shapely geometry or lacks CRS.
        area_crs: Projected CRS used for area calculations.
        layer_name: Optional source layer name. Defaults to `census<year>`.
        municipality_codes: Optional municipality codes used to filter source
            rows through the first available municipality-code column.
        special_section_policy: How to handle special/fictitious sections. The
            default `"exclude"` removes them before estimation. Use `"include"`
            to keep and flag them, or `"raise"` to fail if any intersects the AOI.
        boundary_ring_size: H3 neighbour rings added around filled cells before
            final AOI filtering. Defaults to 3 to avoid missing boundary cells in
            real administrative AOIs.
        include_density: If True, add `<index>_density_per_sq_km` columns based
            on the H3/AOI intersection area.
        clip_output: If True, output geometries are clipped to the AOI. Otherwise
            full H3 cell geometries are returned.
        output_crs: CRS for returned geometries. Defaults to EPSG:4326.
        output_path: Optional GeoPackage path to write.
        output_layer: Optional output layer name. Defaults to
            `h3_census<year>_r<h3_resolution>`.
        conservation_tolerance: Relative tolerance stored in validation metadata.
        workers: Number of parallel workers used for H3-cell chunks. The default
            `1` uses the serial implementation.
        chunk_size: Maximum number of H3 cells in each parallel chunk.
        parallel_backend: Standard-library executor backend for `workers > 1`.
            Use `"thread"` to avoid copying GeoDataFrames between processes,
            `"process"` for process-based execution when serialization overhead
            is acceptable, or `"dask"` after installing the optional Dask extra.
        intermediate_storage: Intermediate execution mode. Use `"parquet"` to
            store prepared GeoParquet inputs and Parquet chunk outputs on disk,
            or `"memory"` for the legacy in-memory path. Defaults to `"parquet"`.
        intermediate_dir: Optional directory used for H3 intermediate files. When
            omitted, a temporary directory is created automatically.
        keep_intermediates: If True, keep generated intermediate files after the
            run. Temporary files are removed by default.
        reuse_intermediates: If True, reuse matching chunk result files in
            `intermediate_dir` when they already exist.

    Returns:
        GeoDataFrame with one row per H3 cell, integer estimated index columns,
        density columns when requested, and coverage metadata. The `attrs`
        dictionary contains continuous `source_totals`, `h3_totals`, and
        `total_validation`, plus `integer_total_validation` for the final
        integer output columns.

    Raises:
        FileNotFoundError: If `census_data_path` does not exist.
        ValueError: If CRS, AOI, requested indexes, parallel options, or source
            geometry are invalid.
    """
    selected_workers, selected_chunk_size, selected_backend = _normalize_parallel_options(
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
    )
    selected_storage = _normalize_intermediate_storage(intermediate_storage)
    if reuse_intermediates and intermediate_dir is None:
        raise ValueError("reuse_intermediates requires intermediate_dir.")

    selected_municipality_codes = (
        list(municipality_codes) if municipality_codes is not None else None
    )
    source = _read_census_layer(census_data_path=census_data_path, year=year, layer_name=layer_name)
    source = _filter_municipality_codes(
        source=source,
        municipality_codes=selected_municipality_codes,
    )
    index_columns = _resolve_index_columns(source=source, year=year, indexes=indexes)
    source = _coerce_numeric_indexes(source=source, index_columns=index_columns)

    aoi_gdf = _normalize_aoi(aoi=aoi, aoi_crs=aoi_crs)
    grid_wgs84 = generate_h3_grid(
        aoi=aoi_gdf,
        h3_resolution=h3_resolution,
        area_crs=area_crs,
        boundary_ring_size=boundary_ring_size,
        output_crs=WGS84_CRS,
    )

    source_area = _prepare_source_cells(
        source=source,
        aoi=aoi_gdf,
        area_crs=area_crs,
        index_columns=index_columns,
        year=year,
        special_section_policy=special_section_policy,
    )
    grid_area = _prepare_h3_overlay_grid(
        grid_wgs84=grid_wgs84,
        aoi=aoi_gdf,
        area_crs=area_crs,
    )
    intermediate_metadata = _build_intermediate_metadata(
        census_data_path=census_data_path,
        layer_name=layer_name or f"census{year}",
        year=year,
        h3_resolution=h3_resolution,
        index_columns=index_columns,
        municipality_codes=selected_municipality_codes,
        special_section_policy=special_section_policy,
        boundary_ring_size=boundary_ring_size,
        include_density=include_density,
        clip_output=clip_output,
        area_crs=area_crs,
        output_crs=output_crs,
        source_area=source_area,
        grid_area=grid_area,
    )

    result_area = _estimate_intersections(
        source_area=source_area,
        grid_area=grid_area,
        index_columns=index_columns,
        year=year,
        h3_resolution=h3_resolution,
        special_section_policy=special_section_policy,
        include_density=include_density,
        clip_output=clip_output,
        workers=selected_workers,
        chunk_size=selected_chunk_size,
        parallel_backend=selected_backend,
        intermediate_storage=selected_storage,
        intermediate_dir=intermediate_dir,
        keep_intermediates=keep_intermediates,
        reuse_intermediates=reuse_intermediates,
        intermediate_metadata=intermediate_metadata,
    )
    continuous_total_validation = _build_total_validation(
        source_area=source_area,
        result=result_area,
        index_columns=index_columns,
        tolerance=conservation_tolerance,
    )
    result_area = _integerize_index_columns(
        result=result_area,
        index_columns=index_columns,
        source_totals={
            row["index"]: row["source_total"]
            for row in continuous_total_validation.to_dict("records")
        },
    )
    integer_total_validation = _build_integer_total_validation(
        continuous_total_validation=continuous_total_validation,
        result=result_area,
        index_columns=index_columns,
    )
    if include_density:
        result_area = _append_density_columns(result=result_area, index_columns=index_columns)
    result_area_attrs = dict(result_area.attrs)
    result = result_area.to_crs(output_crs)
    result.attrs.update(result_area_attrs)
    result.attrs["source_totals"] = {
        row["index"]: row["source_total"] for row in continuous_total_validation.to_dict("records")
    }
    result.attrs["h3_totals"] = {
        row["index"]: row["h3_total"] for row in continuous_total_validation.to_dict("records")
    }
    result.attrs["integer_source_totals"] = {
        row["index"]: row["source_total"] for row in integer_total_validation.to_dict("records")
    }
    result.attrs["integer_h3_totals"] = {
        row["index"]: row["h3_total"] for row in integer_total_validation.to_dict("records")
    }
    result.attrs["total_validation"] = continuous_total_validation
    result.attrs["integer_total_validation"] = integer_total_validation
    result.attrs["estimation_method"] = "area_weighted_uniform_density"
    result.attrs["area_crs"] = str(area_crs)
    result.attrs["boundary_ring_size"] = boundary_ring_size
    result.attrs["workers"] = selected_workers
    result.attrs["chunk_size"] = selected_chunk_size
    result.attrs["parallel_backend"] = selected_backend
    result.attrs["intermediate_storage"] = selected_storage

    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_file(
            filename=str(output_file),
            driver="GPKG",
            layer=output_layer or f"h3_census{year}_r{h3_resolution}",
        )

    final_result = result.reset_index(drop=True)
    final_result.attrs.update(result.attrs)
    return final_result


def _read_census_layer(
    census_data_path: str | Path,
    year: int,
    layer_name: str | None,
) -> gpd.GeoDataFrame:
    source_path = Path(census_data_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Census GeoPackage was not found: {source_path}")

    selected_layer = layer_name or f"census{year}"
    source = gpd.read_file(filename=str(source_path), layer=selected_layer)
    if source.crs is None:
        raise ValueError(f"Layer {selected_layer} in {source_path} does not define a CRS.")
    if source.empty:
        raise ValueError(f"Layer {selected_layer} in {source_path} does not contain any rows.")

    return source


def _normalize_aoi(aoi: GeoInput, aoi_crs: str | int | None) -> gpd.GeoDataFrame:
    if isinstance(aoi, gpd.GeoDataFrame):
        aoi_gdf = aoi[[aoi.geometry.name]].copy()
        aoi_gdf = aoi_gdf.set_geometry(aoi.geometry.name)
    elif isinstance(aoi, gpd.GeoSeries):
        aoi_gdf = gpd.GeoDataFrame(geometry=aoi.copy(), crs=aoi.crs)
    elif isinstance(aoi, BaseGeometry):
        aoi_gdf = gpd.GeoDataFrame(geometry=[aoi], crs=aoi_crs)
    else:
        raise TypeError("aoi must be a Shapely geometry, GeoSeries, or GeoDataFrame.")

    if aoi_gdf.crs is None:
        if aoi_crs is None:
            raise ValueError("AOI CRS is required when the AOI object has no CRS.")
        aoi_gdf = aoi_gdf.set_crs(aoi_crs)

    valid_geometries = [
        _valid_geometry(geometry)
        for geometry in aoi_gdf.geometry
        if geometry is not None and not geometry.is_empty
    ]
    if not valid_geometries:
        raise ValueError("AOI does not contain any non-empty geometry.")

    return gpd.GeoDataFrame(geometry=valid_geometries, crs=aoi_gdf.crs)


def _candidate_h3_cells(
    aoi_geometry: BaseGeometry,
    h3_resolution: int,
    boundary_ring_size: int,
) -> set[str]:
    seed_cells = set(h3.geo_to_cells(aoi_geometry, h3_resolution))
    if not seed_cells:
        representative_point = aoi_geometry.representative_point()
        seed_cells.add(
            h3.latlng_to_cell(
                lat=representative_point.y,
                lng=representative_point.x,
                res=h3_resolution,
            )
        )

    if boundary_ring_size == 0:
        return seed_cells

    candidate_cells = set(seed_cells)
    for h3_index in seed_cells:
        candidate_cells.update(h3.grid_disk(h3_index, boundary_ring_size))

    return candidate_cells


def _h3_cell_to_polygon(h3_index: str) -> Polygon:
    boundary = h3.cell_to_boundary(h3_index)
    return Polygon((lng, lat) for lat, lng in boundary)


def _prepare_source_cells(
    source: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
    index_columns: list[str],
    year: int,
    special_section_policy: str,
) -> gpd.GeoDataFrame:
    if special_section_policy not in SPECIAL_SECTION_POLICIES:
        policies = ", ".join(SPECIAL_SECTION_POLICIES)
        raise ValueError(f"special_section_policy must be one of: {policies}.")

    aoi_area = aoi.to_crs(area_crs)
    aoi_geometry = _union_geometry(aoi_area.geometry)
    source_area = source.to_crs(area_crs).copy()
    source_area["geometry"] = source_area.geometry.map(_valid_geometry)
    source_area = source_area[source_area.geometry.notna() & ~source_area.geometry.is_empty].copy()
    if source_area.empty:
        raise ValueError("Source census layer does not contain usable geometries.")

    source_area["source_cell_area_sqm"] = source_area.geometry.area
    source_area = source_area[source_area["source_cell_area_sqm"] > 0].copy()
    if source_area.empty:
        raise ValueError("Source census layer contains only zero-area geometries.")

    source_area["is_special_section"] = _find_special_sections(source=source_area, year=year)
    source_area = source_area[source_area.geometry.intersects(aoi_geometry)].copy()
    if source_area.empty:
        raise ValueError("No census cells intersect the AOI.")

    if special_section_policy == "raise" and source_area["is_special_section"].any():
        raise ValueError("Special/fictitious census sections intersect the AOI.")
    if special_section_policy == "exclude":
        source_area = source_area[~source_area["is_special_section"]].copy()
        if source_area.empty:
            raise ValueError("Only special/fictitious census sections intersect the AOI.")

    source_area["geometry"] = source_area.geometry.intersection(aoi_geometry)
    source_area["source_aoi_area_sqm"] = source_area.geometry.area
    source_area = source_area[source_area["source_aoi_area_sqm"] > 0].copy()
    if source_area.empty:
        raise ValueError("No positive-area census cell intersection remains inside the AOI.")

    return source_area[
        [
            *index_columns,
            "source_cell_area_sqm",
            "source_aoi_area_sqm",
            "is_special_section",
            "geometry",
        ]
    ]


def _prepare_h3_overlay_grid(
    grid_wgs84: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
) -> gpd.GeoDataFrame:
    aoi_geometry = _union_geometry(aoi.to_crs(area_crs).geometry)
    grid_area = grid_wgs84.to_crs(area_crs).copy()
    grid_area["h3_geometry"] = grid_area.geometry
    grid_area["geometry"] = grid_area.geometry.intersection(aoi_geometry)
    grid_area["aoi_intersection_area_sqm"] = grid_area.geometry.area
    grid_area = grid_area[grid_area["aoi_intersection_area_sqm"] > 0].copy()
    if grid_area.empty:
        raise ValueError("No positive-area H3 cell intersection remains inside the AOI.")

    return grid_area


def _estimate_intersections(
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
    intermediate_storage: str,
    intermediate_dir: str | Path | None,
    keep_intermediates: bool,
    reuse_intermediates: bool,
    intermediate_metadata: dict[str, Any],
) -> gpd.GeoDataFrame:
    if intermediate_storage == "parquet":
        return _estimate_intersections_parquet(
            source_area=source_area,
            grid_area=grid_area,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=workers,
            chunk_size=chunk_size,
            parallel_backend=parallel_backend,
            intermediate_dir=intermediate_dir,
            keep_intermediates=keep_intermediates,
            reuse_intermediates=reuse_intermediates,
            intermediate_metadata=intermediate_metadata,
        )

    if workers == 1 or len(grid_area) <= chunk_size:
        return _estimate_intersections_serial(
            source_area=source_area,
            grid_area=grid_area,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
        )

    return _estimate_intersections_parallel(
        source_area=source_area,
        grid_area=grid_area,
        index_columns=index_columns,
        year=year,
        h3_resolution=h3_resolution,
        special_section_policy=special_section_policy,
        include_density=include_density,
        clip_output=clip_output,
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
    )


def _estimate_intersections_serial(
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
) -> gpd.GeoDataFrame:
    intersections = gpd.overlay(
        source_area[[*index_columns, "source_cell_area_sqm", "is_special_section", "geometry"]],
        grid_area[["h3_index", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    intersections = intersections.assign(intersection_area_sqm=intersections.geometry.area)
    intersections = intersections[intersections["intersection_area_sqm"] > 0].copy()

    result = _base_h3_result(
        grid_area=grid_area,
        year=year,
        special_section_policy=special_section_policy,
    )

    if intersections.empty:
        result = _append_zero_index_columns(
            result=result,
            index_columns=index_columns,
            include_density=include_density,
        )
        return _sort_result(_finalize_result_geometry(result=result, clip_output=clip_output))

    weights = intersections["intersection_area_sqm"] / intersections["source_cell_area_sqm"]
    contribution_values = intersections[index_columns].mul(weights, axis=0)
    value_totals = contribution_values.groupby(intersections["h3_index"]).sum().reset_index()
    coverage = (
        intersections.groupby("h3_index", as_index=False)
        .agg(
            source_intersection_area_sqm=("intersection_area_sqm", "sum"),
            intersects_special_section=("is_special_section", "max"),
        )
        .astype({"intersects_special_section": bool})
    )

    result = result.merge(value_totals, how="left", on="h3_index")
    result = result.merge(coverage, how="left", on="h3_index")
    result[index_columns] = result[index_columns].fillna(0.0)
    result["source_intersection_area_sqm"] = result["source_intersection_area_sqm"].fillna(0.0)
    result["intersects_special_section"] = result["intersects_special_section"].fillna(False)
    coverage_ratio = (
        result["source_intersection_area_sqm"] / result["aoi_intersection_area_sqm"]
    ).fillna(0.0)
    coverage_ratio.name = "aoi_coverage_ratio"
    result = gpd.GeoDataFrame(
        pd.concat([result, coverage_ratio], axis=1),
        geometry="geometry",
        crs=result.crs,
    )

    return _sort_result(_finalize_result_geometry(result=result, clip_output=clip_output))


def _base_h3_result(
    grid_area: gpd.GeoDataFrame,
    year: int,
    special_section_policy: str,
) -> gpd.GeoDataFrame:
    base = grid_area[
        [
            "h3_index",
            "h3_resolution",
            "h3_cell_area_sqm",
            "aoi_intersection_area_sqm",
            "h3_geometry",
            "geometry",
        ]
    ].reset_index(drop=True)
    metadata = pd.DataFrame(
        {
            "year": year,
            "special_section_policy": special_section_policy,
        },
        index=base.index,
    )
    result = pd.concat([base, metadata], axis=1)
    return gpd.GeoDataFrame(result, geometry="geometry", crs=grid_area.crs)


def _append_zero_index_columns(
    result: gpd.GeoDataFrame,
    index_columns: list[str],
    include_density: bool,
) -> gpd.GeoDataFrame:
    index_values = pd.DataFrame(0.0, index=result.index, columns=index_columns)
    coverage = pd.DataFrame(
        {
            "source_intersection_area_sqm": 0.0,
            "aoi_coverage_ratio": 0.0,
            "intersects_special_section": False,
        },
        index=result.index,
    )
    frames: list[pd.DataFrame] = [result, index_values, coverage]
    merged = pd.concat(frames, axis=1)
    zero_result = gpd.GeoDataFrame(merged, geometry="geometry", crs=result.crs)
    zero_result.attrs.update(result.attrs)
    return zero_result


def _append_density_columns(
    result: gpd.GeoDataFrame,
    index_columns: list[str],
) -> gpd.GeoDataFrame:
    area_sq_km = result["aoi_intersection_area_sqm"] / 1_000_000
    density_values = result[index_columns].div(area_sq_km, axis=0).where(area_sq_km > 0, 0.0)
    density_values.columns = [f"{index_column}_density_per_sq_km" for index_column in index_columns]
    merged = pd.concat([result, density_values], axis=1)
    density_result = gpd.GeoDataFrame(merged, geometry="geometry", crs=result.crs)
    density_result.attrs.update(result.attrs)
    return density_result


def _estimate_intersections_parquet(
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
    intermediate_dir: str | Path | None,
    keep_intermediates: bool,
    reuse_intermediates: bool,
    intermediate_metadata: dict[str, Any],
) -> gpd.GeoDataFrame:
    metadata_fingerprint = _metadata_fingerprint(intermediate_metadata)
    with _h3_intermediate_workspace(
        intermediate_dir=intermediate_dir,
        keep_intermediates=keep_intermediates,
        reuse_intermediates=reuse_intermediates,
        metadata_fingerprint=metadata_fingerprint,
    ) as workspace:
        if parallel_backend == "dask" and workers > 1 and len(grid_area) > chunk_size:
            _import_dask_module()
        _write_intermediate_metadata(
            workspace=workspace,
            metadata=intermediate_metadata,
            metadata_fingerprint=metadata_fingerprint,
        )
        source_path = workspace / "prepared_source.parquet"
        grid_path = workspace / "h3_grid.parquet"
        source_area.to_parquet(source_path, index=False)
        grid_area.to_parquet(grid_path, index=False)

        grid_chunk_paths = _write_grid_chunk_parquets(
            grid_area=grid_area,
            workspace=workspace,
            chunk_size=chunk_size,
        )
        result_chunk_paths = _estimate_parquet_chunk_paths(
            source_path=source_path,
            grid_chunk_paths=grid_chunk_paths,
            workspace=workspace,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=workers,
            parallel_backend=parallel_backend,
            reuse_intermediates=reuse_intermediates,
        )
        result_frames = [gpd.read_parquet(result_path) for result_path in result_chunk_paths]
        merged = pd.concat(result_frames, ignore_index=True)
        result = _sort_result(gpd.GeoDataFrame(merged, geometry="geometry", crs=grid_area.crs))
        result.attrs["h3_intermediate_dir"] = str(workspace)
        result.attrs["h3_intermediate_fingerprint"] = metadata_fingerprint
        result.attrs["h3_intermediates_retained"] = keep_intermediates or reuse_intermediates
        return result


def _estimate_intersections_parallel(
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
) -> gpd.GeoDataFrame:
    chunks = _chunk_geodataframe(frame=grid_area, chunk_size=chunk_size)
    if len(chunks) == 1:
        return _estimate_intersections_serial(
            source_area=source_area,
            grid_area=chunks[0],
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
        )

    active_workers = min(workers, len(chunks))
    logger.info(
        "Estimating H3 intersections with %s %s worker(s), chunk_size=%s, chunks=%s.",
        active_workers,
        parallel_backend,
        chunk_size,
        len(chunks),
    )

    if parallel_backend == "dask":
        completed_results = _estimate_intersections_with_dask(
            source_area=source_area,
            chunks=chunks,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=active_workers,
        )
    else:
        completed_results = _estimate_intersections_with_executor(
            source_area=source_area,
            chunks=chunks,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=active_workers,
            parallel_backend=parallel_backend,
        )

    ordered_results = [result for result in completed_results if result is not None]
    merged = pd.concat(ordered_results, ignore_index=True)
    return _sort_result(gpd.GeoDataFrame(merged, geometry="geometry", crs=grid_area.crs))


def _estimate_intersections_with_executor(
    source_area: gpd.GeoDataFrame,
    chunks: list[gpd.GeoDataFrame],
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    parallel_backend: str,
) -> list[gpd.GeoDataFrame | None]:
    executor_class = ThreadPoolExecutor if parallel_backend == "thread" else ProcessPoolExecutor
    completed_results: list[gpd.GeoDataFrame | None] = [None] * len(chunks)
    with executor_class(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(
                _estimate_intersections_serial,
                source_area=source_area,
                grid_area=chunk,
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
            ): chunk_index
            for chunk_index, chunk in enumerate(chunks)
        }
        for completed_count, future in enumerate(as_completed(future_to_index), start=1):
            chunk_index = future_to_index[future]
            completed_results[chunk_index] = future.result()
            logger.info(
                "Completed H3 estimation chunk %s/%s.",
                completed_count,
                len(chunks),
            )

    return completed_results


def _estimate_intersections_with_dask(
    source_area: gpd.GeoDataFrame,
    chunks: list[gpd.GeoDataFrame],
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
) -> list[gpd.GeoDataFrame]:
    dask_module = _import_dask_module()
    delayed = dask_module.delayed
    compute = dask_module.compute
    tasks = [
        delayed(_estimate_intersections_serial)(
            source_area=source_area,
            grid_area=chunk,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
        )
        for chunk in chunks
    ]
    return list(compute(*tasks, scheduler="threads", num_workers=workers))


def _estimate_parquet_chunk_paths(
    source_path: Path,
    grid_chunk_paths: list[Path],
    workspace: Path,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    parallel_backend: str,
    reuse_intermediates: bool,
) -> list[Path]:
    result_dir = workspace / "result_chunks"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_chunk_paths = [
        result_dir / f"result_chunk_{chunk_index:05d}.parquet"
        for chunk_index in range(len(grid_chunk_paths))
    ]

    if workers == 1 or len(grid_chunk_paths) == 1:
        for chunk_index, grid_chunk_path in enumerate(grid_chunk_paths):
            _estimate_intersections_chunk_to_parquet(
                source_path=source_path,
                grid_chunk_path=grid_chunk_path,
                result_path=result_chunk_paths[chunk_index],
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
                reuse_intermediates=reuse_intermediates,
            )
            logger.info(
                "Completed H3 estimation chunk %s/%s.",
                chunk_index + 1,
                len(grid_chunk_paths),
            )
        return result_chunk_paths

    active_workers = min(workers, len(grid_chunk_paths))
    logger.info(
        "Estimating H3 intersections with %s %s worker(s), chunk_size persisted, chunks=%s.",
        active_workers,
        parallel_backend,
        len(grid_chunk_paths),
    )

    if parallel_backend == "dask":
        return _estimate_parquet_chunk_paths_with_dask(
            source_path=source_path,
            grid_chunk_paths=grid_chunk_paths,
            result_chunk_paths=result_chunk_paths,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=active_workers,
            reuse_intermediates=reuse_intermediates,
        )

    return _estimate_parquet_chunk_paths_with_executor(
        source_path=source_path,
        grid_chunk_paths=grid_chunk_paths,
        result_chunk_paths=result_chunk_paths,
        index_columns=index_columns,
        year=year,
        h3_resolution=h3_resolution,
        special_section_policy=special_section_policy,
        include_density=include_density,
        clip_output=clip_output,
        workers=active_workers,
        parallel_backend=parallel_backend,
        reuse_intermediates=reuse_intermediates,
    )


def _estimate_parquet_chunk_paths_with_executor(
    source_path: Path,
    grid_chunk_paths: list[Path],
    result_chunk_paths: list[Path],
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    parallel_backend: str,
    reuse_intermediates: bool,
) -> list[Path]:
    executor_class = ThreadPoolExecutor if parallel_backend == "thread" else ProcessPoolExecutor
    completed_paths: list[Path | None] = [None] * len(grid_chunk_paths)
    with executor_class(max_workers=workers) as executor:
        future_to_index = {
            executor.submit(
                _estimate_intersections_chunk_to_parquet,
                source_path=source_path,
                grid_chunk_path=grid_chunk_path,
                result_path=result_chunk_paths[chunk_index],
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
                reuse_intermediates=reuse_intermediates,
            ): chunk_index
            for chunk_index, grid_chunk_path in enumerate(grid_chunk_paths)
        }
        for completed_count, future in enumerate(as_completed(future_to_index), start=1):
            chunk_index = future_to_index[future]
            completed_paths[chunk_index] = future.result()
            logger.info(
                "Completed H3 estimation chunk %s/%s.",
                completed_count,
                len(grid_chunk_paths),
            )

    return [path for path in completed_paths if path is not None]


def _estimate_parquet_chunk_paths_with_dask(
    source_path: Path,
    grid_chunk_paths: list[Path],
    result_chunk_paths: list[Path],
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    workers: int,
    reuse_intermediates: bool,
) -> list[Path]:
    dask_module = _import_dask_module()
    delayed = dask_module.delayed
    compute = dask_module.compute
    tasks = [
        delayed(_estimate_intersections_chunk_to_parquet)(
            source_path=source_path,
            grid_chunk_path=grid_chunk_path,
            result_path=result_chunk_paths[chunk_index],
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            reuse_intermediates=reuse_intermediates,
        )
        for chunk_index, grid_chunk_path in enumerate(grid_chunk_paths)
    ]
    return list(compute(*tasks, scheduler="threads", num_workers=workers))


def _import_dask_module() -> Any:
    try:
        return importlib.import_module("dask")
    except ImportError as exc:
        raise ImportError(
            "parallel_backend='dask' requires Dask. Install it with "
            "`pip install 'istat-census-data[dask]'`."
        ) from exc


def _estimate_intersections_chunk_to_parquet(
    source_path: Path,
    grid_chunk_path: Path,
    result_path: Path,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    reuse_intermediates: bool,
) -> Path:
    if reuse_intermediates and result_path.exists():
        return result_path

    source_area = gpd.read_parquet(source_path)
    grid_chunk = gpd.read_parquet(grid_chunk_path)
    result = _estimate_intersections_serial(
        source_area=source_area,
        grid_area=grid_chunk,
        index_columns=index_columns,
        year=year,
        h3_resolution=h3_resolution,
        special_section_policy=special_section_policy,
        include_density=include_density,
        clip_output=clip_output,
    )
    result.to_parquet(result_path, index=False)
    return result_path


def _write_grid_chunk_parquets(
    grid_area: gpd.GeoDataFrame,
    workspace: Path,
    chunk_size: int,
) -> list[Path]:
    chunk_dir = workspace / "grid_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths = []
    chunks = _chunk_geodataframe(frame=grid_area, chunk_size=chunk_size)
    for chunk_index, chunk in enumerate(chunks):
        chunk_path = chunk_dir / f"grid_chunk_{chunk_index:05d}.parquet"
        chunk.to_parquet(chunk_path, index=False)
        chunk_paths.append(chunk_path)
    return chunk_paths


@contextmanager
def _h3_intermediate_workspace(
    intermediate_dir: str | Path | None,
    keep_intermediates: bool,
    reuse_intermediates: bool,
    metadata_fingerprint: str,
):
    if intermediate_dir is None:
        if keep_intermediates:
            workspace = Path(tempfile.mkdtemp(prefix=f"istat_h3_{metadata_fingerprint[:12]}_"))
            yield workspace
            return
        with tempfile.TemporaryDirectory(prefix=f"istat_h3_{metadata_fingerprint[:12]}_") as tmp:
            yield Path(tmp)
            return

    root = Path(intermediate_dir)
    root.mkdir(parents=True, exist_ok=True)
    if keep_intermediates or reuse_intermediates:
        workspace = root / metadata_fingerprint
        workspace.mkdir(parents=True, exist_ok=True)
        yield workspace
        return

    with tempfile.TemporaryDirectory(prefix=f"{metadata_fingerprint[:12]}_", dir=root) as tmp:
        yield Path(tmp)


def _write_intermediate_metadata(
    workspace: Path,
    metadata: dict[str, Any],
    metadata_fingerprint: str,
) -> None:
    metadata_path = workspace / "metadata.json"
    metadata_record = {
        "fingerprint": metadata_fingerprint,
        "metadata": metadata,
    }
    metadata_path.write_text(
        json.dumps(metadata_record, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _chunk_geodataframe(frame: gpd.GeoDataFrame, chunk_size: int) -> list[gpd.GeoDataFrame]:
    return [
        frame.iloc[start : start + chunk_size].copy() for start in range(0, len(frame), chunk_size)
    ]


def _sort_result(result: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return result.sort_values("h3_index").reset_index(drop=True)


def _finalize_result_geometry(result: gpd.GeoDataFrame, clip_output: bool) -> gpd.GeoDataFrame:
    if not clip_output:
        result["geometry"] = result["h3_geometry"]
    result = result.drop(columns=["h3_geometry"])
    return gpd.GeoDataFrame(result, geometry="geometry", crs=result.crs)


def _build_total_validation(
    source_area: gpd.GeoDataFrame,
    result: gpd.GeoDataFrame,
    index_columns: list[str],
    tolerance: float,
) -> pd.DataFrame:
    records = []
    for index_column in index_columns:
        source_total = (
            source_area[index_column]
            * source_area["source_aoi_area_sqm"]
            / source_area["source_cell_area_sqm"]
        ).sum()
        h3_total = result[index_column].sum()
        absolute_difference = h3_total - source_total
        relative_difference = (
            abs(absolute_difference) / abs(source_total)
            if source_total
            else abs(absolute_difference)
        )
        records.append(
            {
                "index": index_column,
                "source_total": source_total,
                "h3_total": h3_total,
                "absolute_difference": absolute_difference,
                "relative_difference": relative_difference,
                "within_tolerance": abs(relative_difference) <= tolerance,
            }
        )

    return pd.DataFrame.from_records(records)


def _integerize_index_columns(
    result: gpd.GeoDataFrame,
    index_columns: list[str],
    source_totals: dict[str, float],
) -> gpd.GeoDataFrame:
    integer_data = {}
    for index_column in index_columns:
        values = result[index_column].astype(float).fillna(0.0)
        target_total = _round_half_up(source_totals[index_column])
        integer_data[index_column] = _apportion_integer_values(
            values=values,
            target_total=target_total,
        )

    integer_values = pd.DataFrame(integer_data, index=result.index)
    converted = result.copy()
    converted[index_columns] = integer_values[index_columns]
    integer_result = gpd.GeoDataFrame(converted, geometry="geometry", crs=result.crs)
    integer_result.attrs.update(result.attrs)
    return integer_result


def _apportion_integer_values(values: pd.Series, target_total: int) -> pd.Series:
    if values.empty:
        return pd.Series(dtype="int64", index=values.index)
    if (values < 0).any():
        return values.round().astype("int64")

    floored = values.map(math.floor).astype("int64")
    remainder_count = target_total - int(floored.sum())
    if remainder_count <= 0:
        return floored

    fractional_parts = (values - floored).sort_values(ascending=False, kind="mergesort")
    apportioned = floored.copy()
    while remainder_count > 0:
        selected_indexes = fractional_parts.index[: min(remainder_count, len(fractional_parts))]
        apportioned.loc[selected_indexes] = apportioned.loc[selected_indexes] + 1
        remainder_count -= len(selected_indexes)

    return apportioned.astype("int64")


def _round_half_up(value: float) -> int:
    numeric_value = float(value)
    if numeric_value >= 0:
        return int(math.floor(numeric_value + 0.5))
    return int(math.ceil(numeric_value - 0.5))


def _build_integer_total_validation(
    continuous_total_validation: pd.DataFrame,
    result: gpd.GeoDataFrame,
    index_columns: list[str],
) -> pd.DataFrame:
    source_totals = {
        str(row["index"]): _round_half_up(float(row["source_total"]))
        for row in continuous_total_validation.to_dict("records")
    }
    records = []
    for index_column in index_columns:
        source_total = source_totals[index_column]
        h3_total = int(result[index_column].sum())
        absolute_difference = h3_total - source_total
        relative_difference = (
            abs(absolute_difference) / abs(source_total)
            if source_total
            else abs(absolute_difference)
        )
        records.append(
            {
                "index": index_column,
                "source_total": source_total,
                "h3_total": h3_total,
                "absolute_difference": absolute_difference,
                "relative_difference": relative_difference,
                "within_tolerance": absolute_difference == 0,
            }
        )

    return pd.DataFrame.from_records(records)


def _resolve_index_columns(
    source: gpd.GeoDataFrame,
    year: int,
    indexes: str | Iterable[str] | None,
) -> list[str]:
    catalog = get_census_index_catalog(year=year)
    additive_catalog = catalog[catalog["is_additive"].astype(bool)].copy()

    if indexes is None or indexes == "all_additive":
        return _available_additive_indexes(
            source=source,
            year=year,
            additive_catalog=additive_catalog,
        )

    requested_indexes = [indexes] if isinstance(indexes, str) else list(indexes)
    if not requested_indexes:
        return _available_additive_indexes(
            source=source,
            year=year,
            additive_catalog=additive_catalog,
        )

    resolved_indexes: list[str] = []
    for requested_index in requested_indexes:
        source_code = _resolve_single_index(
            requested_index=str(requested_index),
            source_columns=source.columns,
            additive_catalog=additive_catalog,
        )
        if source_code not in resolved_indexes:
            resolved_indexes.append(source_code)

    return resolved_indexes


def _available_additive_indexes(
    source: gpd.GeoDataFrame,
    year: int,
    additive_catalog: pd.DataFrame,
) -> list[str]:
    available_indexes = [
        str(source_code)
        for source_code in additive_catalog["source_code"].tolist()
        if source_code in source.columns
    ]
    if not available_indexes:
        raise ValueError(
            f"Layer does not contain additive catalogue indexes for census year {year}."
        )
    return available_indexes


def _resolve_single_index(
    requested_index: str,
    source_columns: Iterable[Any],
    additive_catalog: pd.DataFrame,
) -> str:
    source_column_set = {str(column) for column in source_columns}
    source_code_set = {str(source_code) for source_code in additive_catalog["source_code"].tolist()}
    requested_source_code = requested_index.upper()

    if requested_source_code in source_code_set:
        if requested_source_code not in source_column_set:
            raise ValueError(
                f"Requested index {requested_source_code} is not present in the layer."
            )
        return requested_source_code

    matching_canonical = additive_catalog[additive_catalog["canonical_id"] == requested_index]
    matching_source_codes = [
        str(source_code)
        for source_code in matching_canonical["source_code"].tolist()
        if source_code in source_column_set
    ]
    if matching_source_codes:
        return matching_source_codes[0]

    raise ValueError(
        f"Requested index {requested_index} is not an additive catalogue source code or "
        "canonical ID present in the layer."
    )


def _coerce_numeric_indexes(
    source: gpd.GeoDataFrame,
    index_columns: list[str],
) -> gpd.GeoDataFrame:
    source = source.copy()
    for index_column in index_columns:
        source[index_column] = pd.to_numeric(source[index_column], errors="coerce").fillna(0.0)
    return source


def _filter_municipality_codes(
    source: gpd.GeoDataFrame,
    municipality_codes: Iterable[int | str] | None,
) -> gpd.GeoDataFrame:
    if municipality_codes is None:
        return source

    code_values = {
        normalized_code
        for code in municipality_codes
        if (normalized_code := _normalize_municipality_code_value(code))
    }
    if not code_values:
        raise ValueError("municipality_codes must contain at least one value when provided.")

    municipality_column = _find_first_column(source.columns, MUNICIPALITY_CODE_COLUMNS)
    if municipality_column is None:
        candidates = ", ".join(MUNICIPALITY_CODE_COLUMNS)
        raise ValueError(f"No municipality-code column found. Expected one of: {candidates}.")

    source_codes = source[municipality_column].map(_normalize_municipality_code_value)
    filtered = source[source_codes.isin(code_values)].copy()
    if filtered.empty:
        raise ValueError("No census rows match the requested municipality_codes.")

    return filtered


def _normalize_municipality_code_value(value: object) -> str:
    if pd.isna(value):
        return ""

    code = str(value).strip()
    if not code:
        return ""

    try:
        numeric_code = float(code)
    except ValueError:
        return code

    if math.isfinite(numeric_code) and numeric_code.is_integer():
        return str(int(numeric_code))
    return code


def _find_special_sections(source: gpd.GeoDataFrame, year: int) -> pd.Series:
    section_column = _find_first_column(source.columns, (f"SEZ{year}", *SECTION_CODE_COLUMNS))
    if section_column is None:
        return pd.Series(False, index=source.index)

    section_codes = source[section_column].astype(str).str.strip()
    return section_codes.map(
        lambda section_code: any(marker in section_code for marker in SPECIAL_SECTION_MARKERS)
    )


def _find_first_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    column_set = {str(column) for column in columns}
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return None


def _union_geometry(geometries: gpd.GeoSeries) -> BaseGeometry:
    if hasattr(geometries, "union_all"):
        return geometries.union_all()
    return geometries.unary_union


def _valid_geometry(geometry: BaseGeometry) -> BaseGeometry:
    valid_geometry = make_valid(geometry)
    if valid_geometry.is_empty:
        return valid_geometry
    return valid_geometry


def _validate_h3_resolution(h3_resolution: int) -> None:
    if not isinstance(h3_resolution, int) or isinstance(h3_resolution, bool):
        raise ValueError("h3_resolution must be the integer 11.")
    if h3_resolution != REQUIRED_H3_RESOLUTION:
        raise ValueError("This estimator requires h3_resolution=11.")


def _normalize_intermediate_storage(intermediate_storage: str) -> str:
    if intermediate_storage not in INTERMEDIATE_STORAGE_MODES:
        modes = ", ".join(INTERMEDIATE_STORAGE_MODES)
        raise ValueError(f"intermediate_storage must be one of: {modes}.")
    return intermediate_storage


def _build_intermediate_metadata(
    census_data_path: str | Path,
    layer_name: str,
    year: int,
    h3_resolution: int,
    index_columns: list[str],
    municipality_codes: Iterable[int | str] | None,
    special_section_policy: str,
    boundary_ring_size: int,
    include_density: bool,
    clip_output: bool,
    area_crs: str | int,
    output_crs: str | int,
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
) -> dict[str, Any]:
    source_path = Path(census_data_path)
    source_stat = source_path.stat() if source_path.exists() else None
    return {
        "schema_version": INTERMEDIATE_SCHEMA_VERSION,
        "census_data_path": str(source_path),
        "census_data_size": source_stat.st_size if source_stat is not None else None,
        "census_data_mtime_ns": source_stat.st_mtime_ns if source_stat is not None else None,
        "layer_name": layer_name,
        "year": year,
        "h3_resolution": h3_resolution,
        "index_columns": index_columns,
        "municipality_codes": _metadata_sequence(municipality_codes),
        "special_section_policy": special_section_policy,
        "boundary_ring_size": boundary_ring_size,
        "include_density": include_density,
        "clip_output": clip_output,
        "area_crs": str(area_crs),
        "output_crs": str(output_crs),
        "source_crs": str(source_area.crs),
        "grid_crs": str(grid_area.crs),
        "source_rows": len(source_area),
        "grid_rows": len(grid_area),
        "source_total_bounds": _metadata_bounds(source_area),
        "grid_total_bounds": _metadata_bounds(grid_area),
    }


def _metadata_sequence(values: Iterable[Any] | None) -> list[str] | None:
    if values is None:
        return None
    return sorted(str(value) for value in values)


def _metadata_bounds(frame: gpd.GeoDataFrame) -> list[float]:
    return [float(value) for value in frame.total_bounds.tolist()]


def _metadata_fingerprint(metadata: dict[str, Any]) -> str:
    serialized = json.dumps(metadata, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalize_parallel_options(
    workers: int,
    chunk_size: int,
    parallel_backend: str,
) -> tuple[int, int, str]:
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ValueError("workers must be an integer greater than or equal to 1.")
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size < 1:
        raise ValueError("chunk_size must be an integer greater than or equal to 1.")
    if parallel_backend not in PARALLEL_BACKENDS:
        backends = ", ".join(PARALLEL_BACKENDS)
        raise ValueError(f"parallel_backend must be one of: {backends}.")
    return workers, chunk_size, parallel_backend
