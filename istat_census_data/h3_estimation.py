"""H3 area-weighted estimation for ISTAT census section indicators."""

from __future__ import annotations

import importlib
import logging
from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
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
DEFAULT_PARALLEL_BACKEND = "thread"
PARALLEL_BACKENDS = ("thread", "process", "dask")

GeoInput: TypeAlias = BaseGeometry | gpd.GeoDataFrame | gpd.GeoSeries

logger = logging.getLogger(__name__)


def generate_h3_grid(
    aoi: GeoInput,
    h3_resolution: int = REQUIRED_H3_RESOLUTION,
    *,
    aoi_crs: str | int | None = WGS84_CRS,
    area_crs: str | int = DEFAULT_AREA_CRS,
    boundary_ring_size: int = 1,
    output_crs: str | int = WGS84_CRS,
) -> gpd.GeoDataFrame:
    """Generate H3 cell polygons intersecting an area of interest.

    H3 polygon filling uses cell centres. This function expands the filled cells
    by one neighbour ring by default and then keeps only cells that intersect the
    AOI, so boundary cells are retained for area-weighted overlays.

    Args:
        aoi: Area of interest as a Shapely geometry, GeoSeries, or GeoDataFrame.
        h3_resolution: Required H3 resolution. This implementation supports
            only level 11.
        aoi_crs: CRS to use when `aoi` is a plain Shapely geometry or when a
            GeoSeries/GeoDataFrame has no CRS. Defaults to EPSG:4326.
        area_crs: Projected CRS used to calculate `h3_cell_area_sqm`.
        boundary_ring_size: Number of H3 neighbour rings added around filled
            cells before final AOI intersection filtering.
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
    boundary_ring_size: int = 1,
    include_density: bool = True,
    clip_output: bool = False,
    output_crs: str | int = WGS84_CRS,
    output_path: str | Path | None = None,
    output_layer: str | None = None,
    conservation_tolerance: float = 1e-6,
    workers: int = DEFAULT_H3_WORKERS,
    chunk_size: int = DEFAULT_H3_CHUNK_SIZE,
    parallel_backend: str = DEFAULT_PARALLEL_BACKEND,
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
            final AOI filtering.
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

    Returns:
        GeoDataFrame with one row per H3 cell, estimated index columns, density
        columns when requested, and coverage metadata. The `attrs` dictionary
        contains `source_totals`, `h3_totals`, and `total_validation`.

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
    source = _read_census_layer(census_data_path=census_data_path, year=year, layer_name=layer_name)
    source = _filter_municipality_codes(source=source, municipality_codes=municipality_codes)
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
    )
    total_validation = _build_total_validation(
        source_area=source_area,
        result=result_area,
        index_columns=index_columns,
        tolerance=conservation_tolerance,
    )
    result = result_area.to_crs(output_crs)
    result.attrs["source_totals"] = {
        row["index"]: row["source_total"] for row in total_validation.to_dict("records")
    }
    result.attrs["h3_totals"] = {
        row["index"]: row["h3_total"] for row in total_validation.to_dict("records")
    }
    result.attrs["total_validation"] = total_validation
    result.attrs["estimation_method"] = "area_weighted_uniform_density"
    result.attrs["area_crs"] = str(area_crs)
    result.attrs["workers"] = selected_workers
    result.attrs["chunk_size"] = selected_chunk_size
    result.attrs["parallel_backend"] = selected_backend

    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_file(
            filename=str(output_file),
            driver="GPKG",
            layer=output_layer or f"h3_census{year}_r{h3_resolution}",
        )

    return result.reset_index(drop=True)


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
) -> gpd.GeoDataFrame:
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
    intersections["intersection_area_sqm"] = intersections.geometry.area
    intersections = intersections[intersections["intersection_area_sqm"] > 0].copy()

    result = grid_area[
        [
            "h3_index",
            "h3_resolution",
            "h3_cell_area_sqm",
            "aoi_intersection_area_sqm",
            "h3_geometry",
            "geometry",
        ]
    ].copy()
    result["year"] = year

    if intersections.empty:
        for index_column in index_columns:
            result[index_column] = 0.0
        result["source_intersection_area_sqm"] = 0.0
        result["aoi_coverage_ratio"] = 0.0
        result["intersects_special_section"] = False
        result["special_section_policy"] = special_section_policy
        if include_density:
            for index_column in index_columns:
                result[f"{index_column}_density_per_sq_km"] = 0.0
        return _sort_result(_finalize_result_geometry(result=result, clip_output=clip_output))

    contribution_columns = []
    for index_column in index_columns:
        contribution_column = f"__{index_column}_contribution"
        intersections[contribution_column] = (
            intersections[index_column]
            * intersections["intersection_area_sqm"]
            / intersections["source_cell_area_sqm"]
        )
        contribution_columns.append(contribution_column)

    value_totals = intersections.groupby("h3_index", as_index=False)[contribution_columns].sum()
    value_totals = value_totals.rename(
        columns={
            contribution_column: index_column
            for contribution_column, index_column in zip(contribution_columns, index_columns)
        }
    )
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
    for index_column in index_columns:
        result[index_column] = result[index_column].fillna(0.0)
    result["source_intersection_area_sqm"] = result["source_intersection_area_sqm"].fillna(0.0)
    result["intersects_special_section"] = result["intersects_special_section"].fillna(False)
    result["aoi_coverage_ratio"] = (
        result["source_intersection_area_sqm"] / result["aoi_intersection_area_sqm"]
    ).fillna(0.0)
    result["special_section_policy"] = special_section_policy

    if include_density:
        area_sq_km = result["aoi_intersection_area_sqm"] / 1_000_000
        for index_column in index_columns:
            result[f"{index_column}_density_per_sq_km"] = (result[index_column] / area_sq_km).where(
                area_sq_km > 0, 0.0
            )

    return _sort_result(_finalize_result_geometry(result=result, clip_output=clip_output))


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
    try:
        dask_module = importlib.import_module("dask")
    except ImportError as exc:
        raise ImportError(
            "parallel_backend='dask' requires Dask. Install it with "
            "`pip install 'istat-census-data[dask]'`."
        ) from exc

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

    code_values = {str(code).strip() for code in municipality_codes}
    if not code_values:
        raise ValueError("municipality_codes must contain at least one value when provided.")

    municipality_column = _find_first_column(source.columns, MUNICIPALITY_CODE_COLUMNS)
    if municipality_column is None:
        candidates = ", ".join(MUNICIPALITY_CODE_COLUMNS)
        raise ValueError(f"No municipality-code column found. Expected one of: {candidates}.")

    filtered = source[source[municipality_column].astype(str).str.strip().isin(code_values)].copy()
    if filtered.empty:
        raise ValueError("No census rows match the requested municipality_codes.")

    return filtered


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
