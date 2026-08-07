"""H3 area-weighted estimation for ISTAT census section indicators."""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import math
import sqlite3
import tempfile
from collections.abc import Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, TypeAlias

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from shapely import from_wkb, intersects, prepare
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
INTERMEDIATE_SCHEMA_VERSION = 4
H3_GRID_METADATA_SCHEMA_VERSION = 1
H3_GRID_PROGRESS_LOG_INTERVAL = 250_000
H3_GRID_FILTER_CHUNK_SIZE = H3_GRID_PROGRESS_LOG_INTERVAL
H3_CHUNK_FINALIZATION_INDEX_BATCH_SIZE = 8
H3_INDEX_COLUMN = "h3_index"

GeoInput: TypeAlias = BaseGeometry | gpd.GeoDataFrame | gpd.GeoSeries

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _H3ChunkExportResult:
    """Summary returned after streaming retained H3 chunks to a GeoPackage."""

    output_path: Path
    output_layer: str
    row_count: int
    chunk_count: int
    total_validation: pd.DataFrame
    integer_total_validation: pd.DataFrame


@dataclass(frozen=True)
class _H3ParquetChunkRun:
    """Parquet-backed H3 chunk workspace produced by the estimator."""

    workspace: Path
    metadata_fingerprint: str
    result_chunk_paths: list[Path]
    intermediates_retained: bool


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
        polygon geometries. The `attrs` dictionary contains `h3_grid_metadata`
        and `h3_grid_fingerprint` for safe same-AOI reuse.

    Raises:
        TypeError: If the AOI input type is unsupported.
        ValueError: If the AOI is empty, CRS is missing, or the resolution is invalid.
    """
    _validate_h3_resolution(h3_resolution)
    if boundary_ring_size < 0:
        raise ValueError("boundary_ring_size must be greater than or equal to 0.")

    logger.info(
        "Starting H3 grid generation: resolution=%s, boundary_ring_size=%s, "
        "area_crs=%s, output_crs=%s.",
        h3_resolution,
        boundary_ring_size,
        area_crs,
        output_crs,
    )
    aoi_gdf = _normalize_aoi(aoi=aoi, aoi_crs=aoi_crs)
    aoi_wgs84 = aoi_gdf.to_crs(WGS84_CRS)
    aoi_geometry_wgs84 = _union_geometry(aoi_wgs84.geometry)
    logger.info(
        "Prepared H3 AOI geometry: geometries=%s, bounds=%s.",
        len(aoi_gdf),
        _metadata_bounds(aoi_wgs84),
    )

    candidate_cells = _candidate_h3_cells(
        aoi_geometry=aoi_geometry_wgs84,
        h3_resolution=h3_resolution,
        boundary_ring_size=boundary_ring_size,
    )
    candidate_count = len(candidate_cells)
    logger.info(
        "Filtering H3 candidate cells by AOI intersection: candidates=%s.",
        candidate_count,
    )
    retained_h3_indexes, retained_geometries = _filter_h3_candidate_cells(
        candidate_cells=candidate_cells,
        aoi_geometry=aoi_geometry_wgs84,
    )
    logger.info(
        "Filtered H3 candidate cells: retained=%s of %s.",
        len(retained_h3_indexes),
        candidate_count,
    )

    if not retained_h3_indexes:
        raise ValueError("No H3 cells intersect the AOI at the requested resolution.")

    grid_wgs84 = gpd.GeoDataFrame(
        {H3_INDEX_COLUMN: retained_h3_indexes},
        geometry=retained_geometries,
        crs=WGS84_CRS,
    )
    logger.info(
        "Calculating H3 cell areas: cells=%s, area_crs=%s.",
        len(grid_wgs84),
        area_crs,
    )
    grid_area = grid_wgs84.to_crs(area_crs)
    grid_wgs84["h3_resolution"] = h3_resolution
    grid_wgs84["h3_cell_area_sqm"] = grid_area.geometry.area

    grid = grid_wgs84.to_crs(output_crs).reset_index(drop=True)
    h3_grid_metadata = _build_h3_grid_metadata(
        aoi=aoi_gdf,
        h3_resolution=h3_resolution,
        area_crs=area_crs,
        boundary_ring_size=boundary_ring_size,
        grid_crs=output_crs,
    )
    grid.attrs["h3_grid_metadata"] = h3_grid_metadata
    h3_grid_fingerprint = _metadata_fingerprint(h3_grid_metadata)
    grid.attrs["h3_grid_fingerprint"] = h3_grid_fingerprint
    logger.info(
        "Completed H3 grid generation: cells=%s, fingerprint=%s.",
        len(grid),
        h3_grid_fingerprint,
    )
    return grid


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
    max_in_flight_chunks: int | None = None,
    stream_output: bool = False,
    h3_grid: gpd.GeoDataFrame | None = None,
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
        chunk_size: Maximum number of H3 cells in each parallel chunk. In the
            default Parquet mode this also bounds H3 overlay grid preparation.
        parallel_backend: Standard-library executor backend for `workers > 1`.
            Use `"thread"` to avoid copying GeoDataFrames between processes,
            `"process"` for process-based execution when serialization overhead
            is acceptable, or `"dask"` after installing the optional Dask extra.
        intermediate_storage: Intermediate execution mode. Use `"parquet"` to
            prepare the H3 overlay grid in bounded chunks, store prepared
            GeoParquet inputs, and write Parquet chunk outputs on disk. Use
            `"memory"` for the legacy in-memory path. Defaults to `"parquet"`.
        intermediate_dir: Optional directory used for H3 intermediate files. When
            omitted, a temporary directory is created automatically.
        keep_intermediates: If True, keep generated intermediate files after the
            run. Temporary files are removed by default.
        reuse_intermediates: If True, reuse matching chunk result files in
            `intermediate_dir` when they already exist.
        max_in_flight_chunks: Maximum number of chunks submitted or computed at
            once. Defaults to the active worker count, which bounds queue memory
            for thread, process, and Dask execution. Increase only after
            benchmarking if scheduling overhead dominates memory pressure.
        stream_output: If True, require Parquet intermediate storage and
            `output_path`, then stream finalized result chunks directly to the
            GeoPackage instead of materializing the full output GeoDataFrame.
            The returned GeoDataFrame is metadata-only; its `attrs` contain
            `row_count`, validation tables, and output information.
        h3_grid: Optional precomputed H3 grid returned by `generate_h3_grid()`
            for the same AOI, H3 resolution, `boundary_ring_size`, `area_crs`,
            and internal grid CRS. When supplied, the estimator validates the
            stored grid fingerprint before reusing it.

    Returns:
        GeoDataFrame with one row per H3 cell, integer estimated index columns,
        density columns when requested, and coverage metadata. When
        `stream_output=True`, returns a metadata-only GeoDataFrame after writing
        the GeoPackage layer. The `attrs` dictionary contains continuous
        `source_totals`, `h3_totals`, and `total_validation`, plus
        `integer_total_validation` for the final integer output columns.

    Raises:
        FileNotFoundError: If `census_data_path` does not exist.
        ValueError: If CRS, AOI, requested indexes, parallel options, or source
            geometry are invalid.
    """
    _validate_h3_resolution(h3_resolution)
    (
        selected_workers,
        selected_chunk_size,
        selected_backend,
        selected_max_in_flight_chunks,
    ) = _normalize_parallel_options(
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
        max_in_flight_chunks=max_in_flight_chunks,
    )
    selected_storage = _normalize_intermediate_storage(intermediate_storage)
    if reuse_intermediates and intermediate_dir is None:
        raise ValueError("reuse_intermediates requires intermediate_dir.")
    if stream_output and selected_storage != "parquet":
        raise ValueError("stream_output requires intermediate_storage='parquet'.")
    if stream_output and output_path is None:
        raise ValueError("stream_output requires output_path.")

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
    logger.info(
        "Starting H3 census estimation for year %s: source_rows=%s, indexes=%s.",
        year,
        len(source),
        len(index_columns),
    )

    aoi_gdf = _normalize_aoi(aoi=aoi, aoi_crs=aoi_crs)
    grid_wgs84, h3_grid_metadata, h3_grid_fingerprint, h3_grid_reused = _select_h3_grid(
        aoi=aoi_gdf,
        h3_resolution=h3_resolution,
        area_crs=area_crs,
        boundary_ring_size=boundary_ring_size,
        h3_grid=h3_grid,
    )

    source_area = _prepare_source_cells(
        source=source,
        aoi=aoi_gdf,
        area_crs=area_crs,
        index_columns=index_columns,
        year=year,
        special_section_policy=special_section_policy,
    )
    if selected_storage == "parquet":
        intermediate_metadata = _build_chunked_intermediate_metadata(
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
            h3_grid_fingerprint=h3_grid_fingerprint,
            source_area=source_area,
            grid_wgs84=grid_wgs84,
            grid_chunk_size=selected_chunk_size,
        )
        if stream_output:
            if output_path is None:
                raise ValueError("stream_output requires output_path.")
            streamed_result = _estimate_intersections_parquet_prepared_grid_stream_output(
                source_area=source_area,
                grid_wgs84=grid_wgs84,
                aoi=aoi_gdf,
                area_crs=area_crs,
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
                output_crs=output_crs,
                output_path=Path(output_path),
                output_layer=output_layer or f"h3_census{year}_r{h3_resolution}",
                conservation_tolerance=conservation_tolerance,
                workers=selected_workers,
                chunk_size=selected_chunk_size,
                parallel_backend=selected_backend,
                intermediate_dir=intermediate_dir,
                keep_intermediates=keep_intermediates,
                reuse_intermediates=reuse_intermediates,
                max_in_flight_chunks=selected_max_in_flight_chunks,
                intermediate_metadata=intermediate_metadata,
                boundary_ring_size=boundary_ring_size,
                selected_storage=selected_storage,
                h3_grid_reused=h3_grid_reused,
                h3_grid_fingerprint=h3_grid_fingerprint,
                h3_grid_metadata=h3_grid_metadata,
            )
            logger.info(
                "Completed streamed H3 census estimation for year %s: rows=%s.",
                year,
                streamed_result.attrs["row_count"],
            )
            return streamed_result

        result_area = _estimate_intersections_parquet_prepared_grid(
            source_area=source_area,
            grid_wgs84=grid_wgs84,
            aoi=aoi_gdf,
            area_crs=area_crs,
            index_columns=index_columns,
            year=year,
            h3_resolution=h3_resolution,
            special_section_policy=special_section_policy,
            include_density=include_density,
            clip_output=clip_output,
            workers=selected_workers,
            chunk_size=selected_chunk_size,
            parallel_backend=selected_backend,
            intermediate_dir=intermediate_dir,
            keep_intermediates=keep_intermediates,
            reuse_intermediates=reuse_intermediates,
            max_in_flight_chunks=selected_max_in_flight_chunks,
            intermediate_metadata=intermediate_metadata,
        )
    else:
        grid_area = _prepare_h3_overlay_grid(
            grid_wgs84=grid_wgs84,
            aoi=aoi_gdf,
            area_crs=area_crs,
            chunk_size=selected_chunk_size,
        )
        logger.info(
            "Prepared H3 overlay inputs for year %s: source_features=%s, h3_cells=%s.",
            year,
            len(source_area),
            len(grid_area),
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
            h3_grid_fingerprint=h3_grid_fingerprint,
            source_area=source_area,
            grid_area=grid_area,
            grid_chunk_size=selected_chunk_size,
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
            max_in_flight_chunks=selected_max_in_flight_chunks,
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
    result.attrs["max_in_flight_chunks"] = selected_max_in_flight_chunks
    result.attrs["h3_grid_reused"] = h3_grid_reused
    result.attrs["h3_grid_fingerprint"] = h3_grid_fingerprint
    result.attrs["h3_grid_metadata"] = h3_grid_metadata
    result.attrs["stream_output"] = False

    if output_path is not None:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_file(
            filename=str(output_file),
            driver="GPKG",
            layer=output_layer or f"h3_census{year}_r{h3_resolution}",
        )
        logger.info(
            "Wrote H3 output for year %s: path=%s, layer=%s, rows=%s.",
            year,
            output_file,
            output_layer or f"h3_census{year}_r{h3_resolution}",
            len(result),
        )

    final_result = result.reset_index(drop=True)
    final_result.attrs.update(result.attrs)
    logger.info(
        "Completed H3 census estimation for year %s: rows=%s.",
        year,
        len(final_result),
    )
    return final_result


def finalize_h3_result_chunks_to_geopackage(
    intermediate_workspace: str | Path,
    output_path: str | Path,
    *,
    output_layer: str | None = None,
    conservation_tolerance: float = 1e-6,
    index_batch_size: int = H3_CHUNK_FINALIZATION_INDEX_BATCH_SIZE,
) -> _H3ChunkExportResult:
    """Finalize retained H3 result chunks into a GeoPackage without full concatenation.

    This function is intended for retained Parquet/GeoParquet workspaces created by
    `estimate_h3_census_indexes(..., keep_intermediates=True)`. It streams the
    `result_chunks/` files to the target GeoPackage, rebuilding the same validation
    and integer additive totals that the in-memory finalization path produces.

    Args:
        intermediate_workspace: Directory containing `metadata.json`,
            `prepared_source.parquet`, and `result_chunks/result_chunk_*.parquet`.
        output_path: GeoPackage file to create or append to.
        output_layer: GeoPackage layer name. Defaults to
            `h3_census<year>_r<h3_resolution>` from the retained metadata.
        conservation_tolerance: Relative tolerance used for continuous total
            validation.
        index_batch_size: Number of additive indexes to inspect together while
            planning integer apportionment. Lower values use less memory.

    Returns:
        Summary with output path, layer, row count, chunk count, and validation tables.

    Raises:
        FileNotFoundError: If the retained workspace is incomplete.
        ValueError: If metadata is invalid, no result chunk exists, or the output layer
            already exists.
    """
    workspace = Path(intermediate_workspace)
    metadata = _read_h3_intermediate_metadata(workspace=workspace)
    index_columns = [str(index_column) for index_column in metadata["index_columns"]]
    year = int(metadata["year"])
    h3_resolution = int(metadata["h3_resolution"])
    area_crs = metadata.get("area_crs", DEFAULT_AREA_CRS)
    output_crs = metadata.get("output_crs", WGS84_CRS)
    clip_output = bool(metadata.get("clip_output", False))
    include_density = bool(metadata.get("include_density", True))
    layer_name = output_layer or f"h3_census{year}_r{h3_resolution}"

    result_chunk_paths = _retained_result_chunk_paths(
        workspace=workspace,
        expected_chunk_count=metadata.get("grid_chunk_count"),
    )
    source_path = workspace / "prepared_source.parquet"
    if not source_path.exists():
        raise FileNotFoundError(f"Retained H3 source parquet not found: {source_path}")
    source_area = gpd.read_parquet(source_path)

    logger.info(
        "Starting retained H3 chunk finalization: workspace=%s, output=%s, layer=%s, "
        "chunks=%s, indexes=%s.",
        workspace,
        output_path,
        layer_name,
        len(result_chunk_paths),
        len(index_columns),
    )
    h3_totals, row_count = _sum_h3_result_chunk_indexes(
        result_chunk_paths=result_chunk_paths,
        index_columns=index_columns,
    )
    continuous_total_validation = _build_total_validation_from_sums(
        source_area=source_area,
        h3_totals=h3_totals,
        index_columns=index_columns,
        tolerance=conservation_tolerance,
    )
    source_totals = {
        row["index"]: row["source_total"] for row in continuous_total_validation.to_dict("records")
    }
    integerization_plan = _build_chunk_integerization_plan(
        result_chunk_paths=result_chunk_paths,
        index_columns=index_columns,
        source_totals=source_totals,
        index_batch_size=index_batch_size,
    )
    integer_h3_totals = _write_finalized_h3_result_chunks(
        result_chunk_paths=result_chunk_paths,
        output_path=Path(output_path),
        output_layer=layer_name,
        index_columns=index_columns,
        integerization_plan=integerization_plan,
        area_crs=area_crs,
        output_crs=output_crs,
        clip_output=clip_output,
        include_density=include_density,
    )
    _ensure_h3_geopackage_indexes(output_path=Path(output_path), output_layer=layer_name)
    integer_total_validation = _build_integer_total_validation_from_sums(
        continuous_total_validation=continuous_total_validation,
        integer_h3_totals=integer_h3_totals,
        index_columns=index_columns,
    )
    logger.info(
        "Completed retained H3 chunk finalization: output=%s, layer=%s, rows=%s, chunks=%s.",
        output_path,
        layer_name,
        row_count,
        len(result_chunk_paths),
    )
    return _H3ChunkExportResult(
        output_path=Path(output_path),
        output_layer=layer_name,
        row_count=row_count,
        chunk_count=len(result_chunk_paths),
        total_validation=continuous_total_validation,
        integer_total_validation=integer_total_validation,
    )


def _select_h3_grid(
    aoi: gpd.GeoDataFrame,
    h3_resolution: int,
    area_crs: str | int,
    boundary_ring_size: int,
    h3_grid: gpd.GeoDataFrame | None,
) -> tuple[gpd.GeoDataFrame, dict[str, Any], str, bool]:
    expected_metadata = _build_h3_grid_metadata(
        aoi=aoi,
        h3_resolution=h3_resolution,
        area_crs=area_crs,
        boundary_ring_size=boundary_ring_size,
        grid_crs=WGS84_CRS,
    )
    expected_fingerprint = _metadata_fingerprint(expected_metadata)
    if h3_grid is None:
        grid = generate_h3_grid(
            aoi=aoi,
            h3_resolution=h3_resolution,
            area_crs=area_crs,
            boundary_ring_size=boundary_ring_size,
            output_crs=WGS84_CRS,
        )
        logger.info(
            "Generated H3 grid: cells=%s, fingerprint=%s.",
            len(grid),
            expected_fingerprint,
        )
        return grid, expected_metadata, expected_fingerprint, False

    reusable_grid = _validate_reusable_h3_grid(
        h3_grid=h3_grid,
        expected_metadata=expected_metadata,
        expected_fingerprint=expected_fingerprint,
    )
    logger.info(
        "Reusing precomputed H3 grid: cells=%s, fingerprint=%s.",
        len(reusable_grid),
        expected_fingerprint,
    )
    return reusable_grid, expected_metadata, expected_fingerprint, True


def _validate_reusable_h3_grid(
    h3_grid: gpd.GeoDataFrame,
    expected_metadata: dict[str, Any],
    expected_fingerprint: str,
) -> gpd.GeoDataFrame:
    if not isinstance(h3_grid, gpd.GeoDataFrame):
        raise TypeError("h3_grid must be a GeoDataFrame returned by generate_h3_grid().")

    missing_columns = {
        "h3_index",
        "h3_resolution",
        "h3_cell_area_sqm",
        h3_grid.geometry.name,
    }.difference(h3_grid.columns)
    if missing_columns:
        formatted_columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"h3_grid is missing required column(s): {formatted_columns}.")
    if h3_grid.crs is None:
        raise ValueError("h3_grid must define a CRS.")
    if _crs_to_string(h3_grid.crs) != expected_metadata["grid_crs"]:
        raise ValueError("h3_grid CRS does not match the required internal grid CRS.")
    if h3_grid.empty:
        raise ValueError("h3_grid must contain at least one H3 cell.")
    if not h3_grid["h3_index"].is_unique:
        raise ValueError("h3_grid must contain unique h3_index values.")
    if set(h3_grid["h3_resolution"].astype(int).unique()) != {
        int(expected_metadata["h3_resolution"])
    }:
        raise ValueError("h3_grid resolution does not match the requested H3 resolution.")

    actual_metadata = h3_grid.attrs.get("h3_grid_metadata")
    actual_fingerprint = h3_grid.attrs.get("h3_grid_fingerprint")
    if not isinstance(actual_metadata, dict) or not isinstance(actual_fingerprint, str):
        raise ValueError(
            "h3_grid must include h3_grid_metadata and h3_grid_fingerprint attrs. "
            "Build it with generate_h3_grid()."
        )
    if actual_fingerprint != _metadata_fingerprint(actual_metadata):
        raise ValueError("h3_grid fingerprint does not match its stored metadata.")
    if actual_metadata.get("aoi_bounds") != expected_metadata["aoi_bounds"]:
        raise ValueError("h3_grid does not match the requested AOI bounds.")
    if actual_fingerprint != expected_fingerprint:
        raise ValueError("h3_grid does not match the requested AOI and grid parameters.")

    reusable_grid = h3_grid.copy()
    reusable_grid.attrs.update(h3_grid.attrs)
    return reusable_grid


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
    logger.info("Computing H3 seed cells from AOI geometry: resolution=%s.", h3_resolution)
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
    logger.info("Computed H3 seed cells: cells=%s.", len(seed_cells))

    if boundary_ring_size == 0:
        return seed_cells

    candidate_cells = set(seed_cells)
    logger.info(
        "Expanding H3 seed cells with boundary ring: seed_cells=%s, boundary_ring_size=%s.",
        len(seed_cells),
        boundary_ring_size,
    )
    for position, h3_index in enumerate(seed_cells, start=1):
        candidate_cells.update(h3.grid_disk(h3_index, boundary_ring_size))
        if position % H3_GRID_PROGRESS_LOG_INTERVAL == 0:
            logger.info(
                "Expanded H3 boundary ring: processed_seed_cells=%s/%s, candidates=%s.",
                position,
                len(seed_cells),
                len(candidate_cells),
            )
    logger.info(
        "Expanded H3 boundary ring: candidates=%s.",
        len(candidate_cells),
    )

    return candidate_cells


def _h3_cell_to_polygon(h3_index: str) -> Polygon:
    boundary = h3.cell_to_boundary(h3_index)
    return Polygon((lng, lat) for lat, lng in boundary)


def _filter_h3_candidate_cells(
    candidate_cells: set[str],
    aoi_geometry: BaseGeometry,
) -> tuple[list[str], list[Polygon]]:
    sorted_candidate_cells = sorted(candidate_cells)
    candidate_count = len(sorted_candidate_cells)
    retained_h3_indexes: list[str] = []
    retained_geometries: list[Polygon] = []

    prepare(aoi_geometry)
    for chunk_start in range(0, candidate_count, H3_GRID_FILTER_CHUNK_SIZE):
        chunk_stop = min(chunk_start + H3_GRID_FILTER_CHUNK_SIZE, candidate_count)
        chunk_h3_indexes = sorted_candidate_cells[chunk_start:chunk_stop]
        chunk_geometries = np.array(
            [_h3_cell_to_polygon(h3_index) for h3_index in chunk_h3_indexes],
            dtype=object,
        )
        chunk_intersects_aoi = intersects(aoi_geometry, chunk_geometries)

        for h3_index, cell_geometry, keep_cell in zip(
            chunk_h3_indexes,
            chunk_geometries,
            chunk_intersects_aoi,
            strict=True,
        ):
            if keep_cell:
                retained_h3_indexes.append(h3_index)
                retained_geometries.append(cell_geometry)

        if chunk_stop % H3_GRID_PROGRESS_LOG_INTERVAL == 0:
            logger.info(
                "Filtered H3 candidate cells: processed=%s/%s, retained=%s.",
                chunk_stop,
                candidate_count,
                len(retained_h3_indexes),
            )

    return retained_h3_indexes, retained_geometries


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

    logger.info(
        "Preparing source census cells: year=%s, rows=%s, indexes=%s, "
        "area_crs=%s, special_section_policy=%s.",
        year,
        len(source),
        len(index_columns),
        area_crs,
        special_section_policy,
    )
    aoi_area = aoi.to_crs(area_crs)
    aoi_geometry = _union_geometry(aoi_area.geometry)
    logger.info("Projecting source census cells to area CRS: area_crs=%s.", area_crs)
    source_area = source.to_crs(area_crs).copy()
    source_area["geometry"] = source_area.geometry.map(_valid_geometry)
    source_area = source_area[source_area.geometry.notna() & ~source_area.geometry.is_empty].copy()
    logger.info(
        "Validated source census geometries: retained_rows=%s.",
        len(source_area),
    )
    if source_area.empty:
        raise ValueError("Source census layer does not contain usable geometries.")

    source_area["source_cell_area_sqm"] = source_area.geometry.area
    source_area = source_area[source_area["source_cell_area_sqm"] > 0].copy()
    logger.info(
        "Calculated source census cell areas: positive_area_rows=%s.",
        len(source_area),
    )
    if source_area.empty:
        raise ValueError("Source census layer contains only zero-area geometries.")

    source_area["is_special_section"] = _find_special_sections(source=source_area, year=year)
    source_area = source_area[source_area.geometry.intersects(aoi_geometry)].copy()
    logger.info(
        "Filtered source census cells by AOI intersection: intersecting_rows=%s, "
        "special_rows=%s.",
        len(source_area),
        int(source_area["is_special_section"].sum()),
    )
    if source_area.empty:
        raise ValueError("No census cells intersect the AOI.")

    if special_section_policy == "raise" and source_area["is_special_section"].any():
        raise ValueError("Special/fictitious census sections intersect the AOI.")
    if special_section_policy == "exclude":
        source_area = source_area[~source_area["is_special_section"]].copy()
        logger.info(
            "Excluded special/fictitious source census cells: retained_rows=%s.",
            len(source_area),
        )
        if source_area.empty:
            raise ValueError("Only special/fictitious census sections intersect the AOI.")

    logger.info("Clipping source census cells to AOI geometry.")
    source_area["geometry"] = source_area.geometry.intersection(aoi_geometry)
    source_area["source_aoi_area_sqm"] = source_area.geometry.area
    source_area = source_area[source_area["source_aoi_area_sqm"] > 0].copy()
    logger.info(
        "Prepared source census cells: rows=%s.",
        len(source_area),
    )
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
    chunk_size: int | None = None,
) -> gpd.GeoDataFrame:
    logger.info(
        "Preparing H3 overlay grid: cells=%s, area_crs=%s.",
        len(grid_wgs84),
        area_crs,
    )
    aoi_geometry = _union_geometry(aoi.to_crs(area_crs).geometry)
    selected_chunk_size = len(grid_wgs84) if chunk_size is None else chunk_size
    chunk_count = _count_chunks(row_count=len(grid_wgs84), chunk_size=selected_chunk_size)
    logger.info(
        "Clipping H3 overlay grid to AOI geometry: cells=%s, chunks=%s, chunk_size=%s.",
        len(grid_wgs84),
        chunk_count,
        selected_chunk_size,
    )
    prepared_chunks = []
    retained_cells = 0
    started_at = perf_counter()
    for chunk_index, chunk_start in enumerate(
        range(0, len(grid_wgs84), selected_chunk_size),
        start=1,
    ):
        chunk_stop = min(chunk_start + selected_chunk_size, len(grid_wgs84))
        chunk_started_at = perf_counter()
        prepared_chunk = _prepare_h3_overlay_grid_chunk(
            grid_chunk_wgs84=grid_wgs84.iloc[chunk_start:chunk_stop].copy(),
            aoi_geometry=aoi_geometry,
            area_crs=area_crs,
        )
        retained_cells += len(prepared_chunk)
        if not prepared_chunk.empty:
            prepared_chunks.append(prepared_chunk)
        logger.info(
            "Prepared H3 overlay grid chunk %s/%s: input_cells=%s, "
            "retained_cells=%s, total_retained=%s, seconds=%.3f.",
            chunk_index,
            chunk_count,
            chunk_stop - chunk_start,
            len(prepared_chunk),
            retained_cells,
            perf_counter() - chunk_started_at,
        )

    if prepared_chunks:
        merged = pd.concat(prepared_chunks, ignore_index=True)
        grid_area = gpd.GeoDataFrame(merged, geometry="geometry", crs=prepared_chunks[0].crs)
    else:
        grid_area = gpd.GeoDataFrame(columns=grid_wgs84.columns, geometry="geometry", crs=area_crs)
    logger.info(
        "Prepared H3 overlay grid: positive_area_cells=%s, seconds=%.3f.",
        len(grid_area),
        perf_counter() - started_at,
    )
    if grid_area.empty:
        raise ValueError("No positive-area H3 cell intersection remains inside the AOI.")

    return grid_area


def _prepare_h3_overlay_grid_chunk(
    grid_chunk_wgs84: gpd.GeoDataFrame,
    aoi_geometry: BaseGeometry,
    area_crs: str | int,
) -> gpd.GeoDataFrame:
    logger.info("Projecting H3 overlay grid chunk to area CRS: area_crs=%s.", area_crs)
    grid_chunk_area = grid_chunk_wgs84.to_crs(area_crs).copy()
    grid_chunk_area["h3_geometry"] = grid_chunk_area.geometry
    grid_chunk_area["geometry"] = grid_chunk_area.geometry.intersection(aoi_geometry)
    grid_chunk_area["aoi_intersection_area_sqm"] = grid_chunk_area.geometry.area
    grid_chunk_area = grid_chunk_area[grid_chunk_area["aoi_intersection_area_sqm"] > 0].copy()
    return grid_chunk_area.reset_index(drop=True)


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
    max_in_flight_chunks: int | None,
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
            max_in_flight_chunks=max_in_flight_chunks,
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
        max_in_flight_chunks=max_in_flight_chunks,
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


def _estimate_intersections_parquet_prepared_grid(
    source_area: gpd.GeoDataFrame,
    grid_wgs84: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
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
    max_in_flight_chunks: int | None,
    intermediate_metadata: dict[str, Any],
) -> gpd.GeoDataFrame:
    with _h3_parquet_prepared_grid_chunk_run(
        source_area=source_area,
        grid_wgs84=grid_wgs84,
        aoi=aoi,
        area_crs=area_crs,
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
        max_in_flight_chunks=max_in_flight_chunks,
        intermediate_metadata=intermediate_metadata,
    ) as chunk_run:
        merged = _merge_result_chunk_parquets(
            result_chunk_paths=chunk_run.result_chunk_paths,
            crs=area_crs,
            clip_output=clip_output,
        )
        result = _sort_result(gpd.GeoDataFrame(merged, geometry="geometry", crs=area_crs))
        result.attrs["h3_intermediate_dir"] = str(chunk_run.workspace)
        result.attrs["h3_intermediate_fingerprint"] = chunk_run.metadata_fingerprint
        result.attrs["h3_intermediates_retained"] = chunk_run.intermediates_retained
        return result


def _estimate_intersections_parquet_prepared_grid_stream_output(
    source_area: gpd.GeoDataFrame,
    grid_wgs84: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
    index_columns: list[str],
    year: int,
    h3_resolution: int,
    special_section_policy: str,
    include_density: bool,
    clip_output: bool,
    output_crs: str | int,
    output_path: Path,
    output_layer: str,
    conservation_tolerance: float,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
    intermediate_dir: str | Path | None,
    keep_intermediates: bool,
    reuse_intermediates: bool,
    max_in_flight_chunks: int | None,
    intermediate_metadata: dict[str, Any],
    boundary_ring_size: int,
    selected_storage: str,
    h3_grid_reused: bool,
    h3_grid_fingerprint: str,
    h3_grid_metadata: dict[str, Any],
) -> gpd.GeoDataFrame:
    with _h3_parquet_prepared_grid_chunk_run(
        source_area=source_area,
        grid_wgs84=grid_wgs84,
        aoi=aoi,
        area_crs=area_crs,
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
        max_in_flight_chunks=max_in_flight_chunks,
        intermediate_metadata=intermediate_metadata,
    ) as chunk_run:
        export_result = finalize_h3_result_chunks_to_geopackage(
            intermediate_workspace=chunk_run.workspace,
            output_path=output_path,
            output_layer=output_layer,
            conservation_tolerance=conservation_tolerance,
        )
        result = gpd.GeoDataFrame(geometry=[], crs=output_crs)
        result.attrs["source_totals"] = {
            row["index"]: row["source_total"]
            for row in export_result.total_validation.to_dict("records")
        }
        result.attrs["h3_totals"] = {
            row["index"]: row["h3_total"]
            for row in export_result.total_validation.to_dict("records")
        }
        result.attrs["integer_source_totals"] = {
            row["index"]: row["source_total"]
            for row in export_result.integer_total_validation.to_dict("records")
        }
        result.attrs["integer_h3_totals"] = {
            row["index"]: row["h3_total"]
            for row in export_result.integer_total_validation.to_dict("records")
        }
        result.attrs["total_validation"] = export_result.total_validation
        result.attrs["integer_total_validation"] = export_result.integer_total_validation
        result.attrs["estimation_method"] = "area_weighted_uniform_density"
        result.attrs["area_crs"] = str(area_crs)
        result.attrs["boundary_ring_size"] = boundary_ring_size
        result.attrs["workers"] = workers
        result.attrs["chunk_size"] = chunk_size
        result.attrs["parallel_backend"] = parallel_backend
        result.attrs["intermediate_storage"] = selected_storage
        result.attrs["max_in_flight_chunks"] = max_in_flight_chunks
        result.attrs["h3_grid_reused"] = h3_grid_reused
        result.attrs["h3_grid_fingerprint"] = h3_grid_fingerprint
        result.attrs["h3_grid_metadata"] = h3_grid_metadata
        result.attrs["h3_intermediate_dir"] = str(chunk_run.workspace)
        result.attrs["h3_intermediate_fingerprint"] = chunk_run.metadata_fingerprint
        result.attrs["h3_intermediates_retained"] = chunk_run.intermediates_retained
        result.attrs["stream_output"] = True
        result.attrs["row_count"] = export_result.row_count
        result.attrs["chunk_count"] = export_result.chunk_count
        result.attrs["output_path"] = str(export_result.output_path)
        result.attrs["output_layer"] = export_result.output_layer
        return result


@contextmanager
def _h3_parquet_prepared_grid_chunk_run(
    source_area: gpd.GeoDataFrame,
    grid_wgs84: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
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
    max_in_flight_chunks: int | None,
    intermediate_metadata: dict[str, Any],
) -> Iterator[_H3ParquetChunkRun]:
    metadata_fingerprint = _metadata_fingerprint(intermediate_metadata)
    with _h3_intermediate_workspace(
        intermediate_dir=intermediate_dir,
        keep_intermediates=keep_intermediates,
        reuse_intermediates=reuse_intermediates,
        metadata_fingerprint=metadata_fingerprint,
    ) as workspace:
        if parallel_backend == "dask" and workers > 1 and len(grid_wgs84) > chunk_size:
            _import_dask_module()
        _write_intermediate_metadata(
            workspace=workspace,
            metadata=intermediate_metadata,
            metadata_fingerprint=metadata_fingerprint,
        )
        source_path = workspace / "prepared_source.parquet"
        source_area.to_parquet(source_path, index=False)

        grid_chunk_paths, prepared_grid_rows = _write_prepared_grid_chunk_parquets(
            grid_wgs84=grid_wgs84,
            aoi=aoi,
            area_crs=area_crs,
            workspace=workspace,
            chunk_size=chunk_size,
            reuse_intermediates=reuse_intermediates,
        )
        if prepared_grid_rows is not None:
            logger.info(
                "Prepared H3 overlay inputs for year %s: source_features=%s, h3_cells=%s.",
                year,
                len(source_area),
                prepared_grid_rows,
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
            max_in_flight_chunks=max_in_flight_chunks,
        )
        yield _H3ParquetChunkRun(
            workspace=workspace,
            metadata_fingerprint=metadata_fingerprint,
            result_chunk_paths=result_chunk_paths,
            intermediates_retained=keep_intermediates or reuse_intermediates,
        )


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
    max_in_flight_chunks: int | None,
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
            max_in_flight_chunks=max_in_flight_chunks,
        )
        merged = _merge_result_chunk_parquets(
            result_chunk_paths=result_chunk_paths,
            crs=grid_area.crs,
            clip_output=clip_output,
        )
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
    max_in_flight_chunks: int | None,
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
    active_chunk_limit = _resolve_max_in_flight_chunks(
        max_in_flight_chunks=max_in_flight_chunks,
        active_workers=active_workers,
        chunk_count=len(chunks),
    )
    logger.info(
        "Estimating H3 intersections with %s %s worker(s), chunk_size=%s, "
        "chunks=%s, max_in_flight_chunks=%s.",
        active_workers,
        parallel_backend,
        chunk_size,
        len(chunks),
        active_chunk_limit,
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
            max_in_flight_chunks=active_chunk_limit,
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
            max_in_flight_chunks=active_chunk_limit,
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
    max_in_flight_chunks: int,
) -> list[gpd.GeoDataFrame | None]:
    executor_class = ThreadPoolExecutor if parallel_backend == "thread" else ProcessPoolExecutor
    completed_results: list[gpd.GeoDataFrame | None] = [None] * len(chunks)
    with executor_class(max_workers=workers) as executor:
        pending_futures = {}
        next_chunk_index = 0

        def submit_next_chunk() -> None:
            nonlocal next_chunk_index
            chunk_index = next_chunk_index
            pending_futures[
                executor.submit(
                    _estimate_intersections_serial,
                    source_area=source_area,
                    grid_area=chunks[chunk_index],
                    index_columns=index_columns,
                    year=year,
                    h3_resolution=h3_resolution,
                    special_section_policy=special_section_policy,
                    include_density=include_density,
                    clip_output=clip_output,
                )
            ] = chunk_index
            next_chunk_index += 1

        for _ in range(min(max_in_flight_chunks, len(chunks))):
            submit_next_chunk()

        completed_count = 0
        while pending_futures:
            completed_futures, _ = wait(
                pending_futures,
                return_when=FIRST_COMPLETED,
            )
            for future in completed_futures:
                chunk_index = pending_futures.pop(future)
                completed_results[chunk_index] = future.result()
                completed_count += 1
                logger.info(
                    "Completed H3 estimation chunk %s/%s.",
                    completed_count,
                    len(chunks),
                )
                if next_chunk_index < len(chunks):
                    submit_next_chunk()

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
    max_in_flight_chunks: int,
) -> list[gpd.GeoDataFrame]:
    dask_module = _import_dask_module()
    delayed = dask_module.delayed
    compute = dask_module.compute
    completed_results: list[gpd.GeoDataFrame | None] = [None] * len(chunks)
    completed_count = 0
    for batch_number, batch_start in enumerate(
        range(0, len(chunks), max_in_flight_chunks),
        start=1,
    ):
        batch_stop = min(batch_start + max_in_flight_chunks, len(chunks))
        batch_indexes = list(range(batch_start, batch_stop))
        logger.info(
            "Computing H3 Dask batch %s: chunks %s-%s of %s.",
            batch_number,
            batch_start + 1,
            batch_stop,
            len(chunks),
        )
        tasks = [
            delayed(_estimate_intersections_serial)(
                source_area=source_area,
                grid_area=chunks[chunk_index],
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
            )
            for chunk_index in batch_indexes
        ]
        batch_results = compute(*tasks, scheduler="threads", num_workers=workers)
        for chunk_index, result in zip(batch_indexes, batch_results, strict=False):
            completed_results[chunk_index] = result
            completed_count += 1
            logger.info(
                "Completed H3 estimation chunk %s/%s.",
                completed_count,
                len(chunks),
            )

    return [result for result in completed_results if result is not None]


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
    max_in_flight_chunks: int | None,
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
    active_chunk_limit = _resolve_max_in_flight_chunks(
        max_in_flight_chunks=max_in_flight_chunks,
        active_workers=active_workers,
        chunk_count=len(grid_chunk_paths),
    )
    logger.info(
        "Estimating H3 intersections with %s %s worker(s), chunk_size persisted, "
        "chunks=%s, max_in_flight_chunks=%s.",
        active_workers,
        parallel_backend,
        len(grid_chunk_paths),
        active_chunk_limit,
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
            max_in_flight_chunks=active_chunk_limit,
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
        max_in_flight_chunks=active_chunk_limit,
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
    max_in_flight_chunks: int,
) -> list[Path]:
    executor_class = ThreadPoolExecutor if parallel_backend == "thread" else ProcessPoolExecutor
    completed_paths: list[Path | None] = [None] * len(grid_chunk_paths)
    with executor_class(max_workers=workers) as executor:
        pending_futures = {}
        next_chunk_index = 0

        def submit_next_chunk() -> None:
            nonlocal next_chunk_index
            chunk_index = next_chunk_index
            pending_futures[
                executor.submit(
                    _estimate_intersections_chunk_to_parquet,
                    source_path=source_path,
                    grid_chunk_path=grid_chunk_paths[chunk_index],
                    result_path=result_chunk_paths[chunk_index],
                    index_columns=index_columns,
                    year=year,
                    h3_resolution=h3_resolution,
                    special_section_policy=special_section_policy,
                    include_density=include_density,
                    clip_output=clip_output,
                    reuse_intermediates=reuse_intermediates,
                )
            ] = chunk_index
            next_chunk_index += 1

        for _ in range(min(max_in_flight_chunks, len(grid_chunk_paths))):
            submit_next_chunk()

        completed_count = 0
        while pending_futures:
            completed_futures, _ = wait(
                pending_futures,
                return_when=FIRST_COMPLETED,
            )
            for future in completed_futures:
                chunk_index = pending_futures.pop(future)
                completed_paths[chunk_index] = future.result()
                completed_count += 1
                logger.info(
                    "Completed H3 estimation chunk %s/%s.",
                    completed_count,
                    len(grid_chunk_paths),
                )
                if next_chunk_index < len(grid_chunk_paths):
                    submit_next_chunk()

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
    max_in_flight_chunks: int,
) -> list[Path]:
    dask_module = _import_dask_module()
    delayed = dask_module.delayed
    compute = dask_module.compute
    completed_paths: list[Path | None] = [None] * len(grid_chunk_paths)
    completed_count = 0
    for batch_number, batch_start in enumerate(
        range(0, len(grid_chunk_paths), max_in_flight_chunks),
        start=1,
    ):
        batch_stop = min(batch_start + max_in_flight_chunks, len(grid_chunk_paths))
        batch_indexes = list(range(batch_start, batch_stop))
        logger.info(
            "Computing H3 Dask batch %s: chunks %s-%s of %s.",
            batch_number,
            batch_start + 1,
            batch_stop,
            len(grid_chunk_paths),
        )
        tasks = [
            delayed(_estimate_intersections_chunk_to_parquet)(
                source_path=source_path,
                grid_chunk_path=grid_chunk_paths[chunk_index],
                result_path=result_chunk_paths[chunk_index],
                index_columns=index_columns,
                year=year,
                h3_resolution=h3_resolution,
                special_section_policy=special_section_policy,
                include_density=include_density,
                clip_output=clip_output,
                reuse_intermediates=reuse_intermediates,
            )
            for chunk_index in batch_indexes
        ]
        batch_paths = compute(*tasks, scheduler="threads", num_workers=workers)
        for chunk_index, result_path in zip(batch_indexes, batch_paths, strict=False):
            completed_paths[chunk_index] = result_path
            completed_count += 1
            logger.info(
                "Completed H3 estimation chunk %s/%s.",
                completed_count,
                len(grid_chunk_paths),
            )

    return [path for path in completed_paths if path is not None]


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


def _merge_result_chunk_parquets(
    result_chunk_paths: list[Path],
    crs: str | int | Any,
    clip_output: bool,
) -> pd.DataFrame:
    chunk_frames = [
        _read_h3_result_chunk(
            result_path=result_path,
            crs=crs,
            clip_output=clip_output,
        )
        for result_path in result_chunk_paths
    ]
    return pd.concat(chunk_frames, ignore_index=True)


def _read_h3_intermediate_metadata(workspace: Path) -> dict[str, Any]:
    metadata_path = workspace / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Retained H3 metadata not found: {metadata_path}")

    metadata_record = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata = metadata_record.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"Retained H3 metadata is invalid: {metadata_path}")

    required_fields = ("year", "h3_resolution", "index_columns")
    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Retained H3 metadata is missing required fields: {missing}")
    if not metadata["index_columns"]:
        raise ValueError("Retained H3 metadata contains no index columns.")

    return metadata


def _retained_result_chunk_paths(
    workspace: Path,
    expected_chunk_count: Any,
) -> list[Path]:
    result_dir = workspace / "result_chunks"
    if not result_dir.exists():
        raise FileNotFoundError(f"Retained H3 result chunk directory not found: {result_dir}")

    result_chunk_paths = sorted(result_dir.glob("result_chunk_*.parquet"))
    if not result_chunk_paths:
        raise ValueError(f"No retained H3 result chunks found in {result_dir}")

    if expected_chunk_count is None:
        return result_chunk_paths

    expected_count = int(expected_chunk_count)
    expected_paths = [
        result_dir / f"result_chunk_{chunk_index:05d}.parquet"
        for chunk_index in range(expected_count)
    ]
    missing_paths = [path for path in expected_paths if not path.exists()]
    if missing_paths:
        preview = ", ".join(str(path) for path in missing_paths[:5])
        raise FileNotFoundError(
            "Retained H3 result chunks are incomplete: "
            f"expected={expected_count}, found={len(result_chunk_paths)}, missing={preview}"
        )

    return expected_paths


def _sum_h3_result_chunk_indexes(
    result_chunk_paths: list[Path],
    index_columns: list[str],
) -> tuple[dict[str, float], int]:
    h3_totals = dict.fromkeys(index_columns, 0.0)
    row_count = 0
    for result_path in result_chunk_paths:
        chunk = pd.read_parquet(result_path, columns=index_columns)
        row_count += len(chunk)
        chunk_totals = chunk.astype(float).fillna(0.0).sum()
        for index_column in index_columns:
            h3_totals[index_column] += float(chunk_totals[index_column])

    return h3_totals, row_count


def _build_chunk_integerization_plan(
    result_chunk_paths: list[Path],
    index_columns: list[str],
    source_totals: dict[str, float],
    index_batch_size: int,
) -> dict[str, dict[str, Any]]:
    if index_batch_size < 1:
        raise ValueError("index_batch_size must be greater than or equal to 1.")

    integerization_plan: dict[str, dict[str, Any]] = {}
    for index_batch in _batch_items(index_columns, index_batch_size):
        batch_plan = _build_index_batch_integerization_plan(
            result_chunk_paths=result_chunk_paths,
            index_columns=index_batch,
            source_totals=source_totals,
        )
        integerization_plan.update(batch_plan)

    return integerization_plan


def _build_index_batch_integerization_plan(
    result_chunk_paths: list[Path],
    index_columns: list[str],
    source_totals: dict[str, float],
) -> dict[str, dict[str, Any]]:
    floor_sums = dict.fromkeys(index_columns, 0)
    has_negative_values = dict.fromkeys(index_columns, False)
    fractional_parts: dict[str, list[np.ndarray]] = {
        index_column: [] for index_column in index_columns
    }

    for result_path in result_chunk_paths:
        chunk = pd.read_parquet(result_path, columns=index_columns)
        numeric_chunk = chunk.astype(float).fillna(0.0)
        for index_column in index_columns:
            values = numeric_chunk[index_column].to_numpy(dtype="float64", copy=False)
            has_negative_values[index_column] = has_negative_values[index_column] or bool(
                np.any(values < 0)
            )
            floored = np.floor(values)
            floor_sums[index_column] += int(floored.sum())
            fractional_parts[index_column].append(values - floored)

    batch_plan = {}
    for index_column in index_columns:
        target_total = _round_half_up(source_totals[index_column])
        if has_negative_values[index_column]:
            batch_plan[index_column] = {"mode": "round", "target_total": target_total}
            continue

        fractions = np.concatenate(fractional_parts[index_column])
        remainder_count = target_total - floor_sums[index_column]
        if remainder_count <= 0 or fractions.size == 0:
            batch_plan[index_column] = {
                "mode": "floor",
                "target_total": target_total,
                "base_increment": 0,
                "selection_count": 0,
                "cutoff": 0.0,
                "ties_to_increment": 0,
            }
            continue

        base_increment, selection_count = divmod(remainder_count, int(fractions.size))
        if selection_count == 0:
            cutoff = 0.0
            ties_to_increment = 0
        else:
            cutoff_position = int(fractions.size) - selection_count
            cutoff = float(np.partition(fractions, cutoff_position)[cutoff_position])
            greater_count = int(np.sum(fractions > cutoff))
            ties_to_increment = selection_count - greater_count

        batch_plan[index_column] = {
            "mode": "apportion",
            "target_total": target_total,
            "base_increment": base_increment,
            "selection_count": selection_count,
            "cutoff": cutoff,
            "ties_to_increment": ties_to_increment,
        }

    return batch_plan


def _write_finalized_h3_result_chunks(
    result_chunk_paths: list[Path],
    output_path: Path,
    output_layer: str,
    index_columns: list[str],
    integerization_plan: dict[str, dict[str, Any]],
    area_crs: str | int | Any,
    output_crs: str | int,
    clip_output: bool,
    include_density: bool,
) -> dict[str, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if _geopackage_layer_exists(output_path=output_path, output_layer=output_layer):
        raise ValueError(
            f"GeoPackage layer already exists: path={output_path}, layer={output_layer}"
        )

    integer_h3_totals = dict.fromkeys(index_columns, 0)
    tie_remaining = {
        index_column: int(plan.get("ties_to_increment", 0))
        for index_column, plan in integerization_plan.items()
    }
    total_rows = 0
    for chunk_number, result_path in enumerate(result_chunk_paths, start=1):
        chunk = _read_h3_result_chunk(
            result_path=result_path,
            crs=area_crs,
            clip_output=clip_output,
        )
        _validate_h3_index_chunk(chunk=chunk, result_path=result_path)
        chunk = _sort_result(chunk)
        chunk = _integerize_h3_result_chunk(
            chunk=chunk,
            index_columns=index_columns,
            integerization_plan=integerization_plan,
            tie_remaining=tie_remaining,
        )
        for index_column in index_columns:
            integer_h3_totals[index_column] += int(chunk[index_column].sum())
        if include_density:
            chunk = _append_density_columns(result=chunk, index_columns=index_columns)

        output_chunk = chunk.to_crs(output_crs)
        write_mode = "a" if output_path.exists() else "w"
        output_chunk.to_file(
            filename=str(output_path),
            driver="GPKG",
            layer=output_layer,
            mode=write_mode,
            SPATIAL_INDEX="YES",
        )
        if chunk_number == 1:
            _ensure_unique_h3_index(output_path=output_path, output_layer=output_layer)
        total_rows += len(output_chunk)
        if chunk_number == 1 or chunk_number % 25 == 0 or chunk_number == len(result_chunk_paths):
            logger.info(
                "Wrote finalized H3 result chunk %s/%s: rows=%s, total_rows=%s, output=%s.",
                chunk_number,
                len(result_chunk_paths),
                len(output_chunk),
                total_rows,
                output_path,
            )

    remaining_ties = {
        index_column: remaining for index_column, remaining in tie_remaining.items() if remaining
    }
    if remaining_ties:
        raise RuntimeError(f"H3 integer apportionment did not consume all ties: {remaining_ties}")

    return integer_h3_totals


def _validate_h3_index_chunk(chunk: gpd.GeoDataFrame, result_path: Path) -> None:
    if H3_INDEX_COLUMN not in chunk.columns:
        raise ValueError(f"H3 result chunk has no {H3_INDEX_COLUMN} column: {result_path}")

    missing_count = int(chunk[H3_INDEX_COLUMN].isna().sum())
    if missing_count:
        raise ValueError(
            f"H3 result chunk contains null {H3_INDEX_COLUMN} values: "
            f"path={result_path}, nulls={missing_count}"
        )

    duplicate_mask = chunk[H3_INDEX_COLUMN].duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_values = chunk.loc[duplicate_mask, H3_INDEX_COLUMN].astype(str).unique()[:10]
        duplicate_preview = ", ".join(duplicate_values)
        raise ValueError(
            f"H3 result chunk contains duplicate {H3_INDEX_COLUMN} values: "
            f"path={result_path}, duplicates={duplicate_preview}"
        )


def _integerize_h3_result_chunk(
    chunk: gpd.GeoDataFrame,
    index_columns: list[str],
    integerization_plan: dict[str, dict[str, Any]],
    tie_remaining: dict[str, int],
) -> gpd.GeoDataFrame:
    integerized = chunk.copy()
    for index_column in index_columns:
        values = integerized[index_column].astype(float).fillna(0.0)
        plan = integerization_plan[index_column]
        if plan["mode"] == "round":
            integerized[index_column] = values.round().astype("int64")
            continue

        floored = np.floor(values.to_numpy(dtype="float64", copy=False)).astype("int64")
        apportioned = pd.Series(floored, index=integerized.index)
        base_increment = int(plan.get("base_increment", 0))
        if base_increment:
            apportioned = apportioned + base_increment

        selection_count = int(plan.get("selection_count", 0))
        if plan["mode"] == "apportion" and selection_count:
            fractional_values = values - apportioned + base_increment
            cutoff = float(plan["cutoff"])
            selected = fractional_values > cutoff
            equal_cutoff = fractional_values == cutoff
            selected_tie_count = min(tie_remaining[index_column], int(equal_cutoff.sum()))
            if selected_tie_count:
                tie_indexes = equal_cutoff[equal_cutoff].index[:selected_tie_count]
                selected.loc[tie_indexes] = True
                tie_remaining[index_column] -= selected_tie_count
            apportioned.loc[selected] = apportioned.loc[selected] + 1

        integerized[index_column] = apportioned.astype("int64")

    integerized = gpd.GeoDataFrame(integerized, geometry="geometry", crs=chunk.crs)
    integerized.attrs.update(chunk.attrs)
    return integerized


def _geopackage_layer_exists(output_path: Path, output_layer: str) -> bool:
    if not output_path.exists():
        return False

    layers = gpd.list_layers(output_path)
    return output_layer in set(layers["name"].astype(str))


def _ensure_h3_geopackage_indexes(output_path: Path, output_layer: str) -> None:
    _ensure_unique_h3_index(output_path=output_path, output_layer=output_layer)
    _ensure_spatial_index_exists(output_path=output_path, output_layer=output_layer)


def _ensure_unique_h3_index(output_path: Path, output_layer: str) -> None:
    with sqlite3.connect(output_path) as connection:
        _validate_h3_index_table_values(connection=connection, output_layer=output_layer)
        if _has_unique_h3_index(connection=connection, output_layer=output_layer):
            return

        index_name = _available_sqlite_object_name(
            connection=connection,
            base_name=_safe_sqlite_name(f"idx_{output_layer}_{H3_INDEX_COLUMN}_unique"),
        )
        connection.execute(
            f"CREATE UNIQUE INDEX {_quote_sql_identifier(index_name)} "
            f"ON {_quote_sql_identifier(output_layer)} "
            f"({_quote_sql_identifier(H3_INDEX_COLUMN)})"
        )


def _validate_h3_index_table_values(
    connection: sqlite3.Connection,
    output_layer: str,
) -> None:
    row_count, non_null_count, distinct_count = connection.execute(
        f"SELECT COUNT(*), COUNT({_quote_sql_identifier(H3_INDEX_COLUMN)}), "
        f"COUNT(DISTINCT {_quote_sql_identifier(H3_INDEX_COLUMN)}) "
        f"FROM {_quote_sql_identifier(output_layer)}"
    ).fetchone()
    null_count = int(row_count) - int(non_null_count)
    if null_count:
        raise ValueError(
            f"GeoPackage layer contains null {H3_INDEX_COLUMN} values: "
            f"layer={output_layer}, nulls={null_count}"
        )
    if int(row_count) != int(distinct_count):
        duplicate_count = int(row_count) - int(distinct_count)
        examples = connection.execute(
            f"SELECT {_quote_sql_identifier(H3_INDEX_COLUMN)} "
            f"FROM {_quote_sql_identifier(output_layer)} "
            f"GROUP BY {_quote_sql_identifier(H3_INDEX_COLUMN)} "
            "HAVING COUNT(*) > 1 "
            "LIMIT 10"
        ).fetchall()
        duplicate_preview = ", ".join(str(row[0]) for row in examples)
        raise ValueError(
            f"GeoPackage layer contains duplicate {H3_INDEX_COLUMN} values: "
            f"layer={output_layer}, duplicates={duplicate_count}, examples={duplicate_preview}"
        )


def _has_unique_h3_index(
    connection: sqlite3.Connection,
    output_layer: str,
) -> bool:
    for index_row in connection.execute(
        f"PRAGMA index_list({_quote_sql_identifier(output_layer)})"
    ):
        index_name = str(index_row[1])
        is_unique = bool(index_row[2])
        if not is_unique:
            continue
        indexed_columns = [
            str(column_row[2])
            for column_row in connection.execute(
                f"PRAGMA index_info({_quote_sql_identifier(index_name)})"
            )
        ]
        if indexed_columns == [H3_INDEX_COLUMN]:
            return True
    return False


def _ensure_spatial_index_exists(output_path: Path, output_layer: str) -> None:
    with sqlite3.connect(output_path) as connection:
        geometry_column_row = connection.execute(
            "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
            (output_layer,),
        ).fetchone()
        if geometry_column_row is None:
            raise ValueError(f"GeoPackage layer has no geometry metadata: layer={output_layer}")

        geometry_column = str(geometry_column_row[0])
        rtree_table = f"rtree_{output_layer}_{geometry_column}"
        rtree_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (rtree_table,),
        ).fetchone()
        if rtree_exists is None:
            raise ValueError(
                f"GeoPackage layer is missing its spatial index: "
                f"layer={output_layer}, expected_table={rtree_table}"
            )


def _available_sqlite_object_name(
    connection: sqlite3.Connection,
    base_name: str,
) -> str:
    candidate_name = base_name
    suffix = 2
    while _sqlite_object_exists(connection=connection, object_name=candidate_name):
        candidate_name = f"{base_name}_{suffix}"
        suffix += 1
    return candidate_name


def _sqlite_object_exists(connection: sqlite3.Connection, object_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ?",
            (object_name,),
        ).fetchone()
        is not None
    )


def _quote_sql_identifier(identifier: str) -> str:
    escaped_identifier = identifier.replace('"', '""')
    return f'"{escaped_identifier}"'


def _safe_sqlite_name(name: str) -> str:
    safe_name = "".join(character if character.isalnum() else "_" for character in name)
    safe_name = "_".join(part for part in safe_name.split("_") if part)
    return safe_name[:120] or "idx_h3_index_unique"


def _batch_items(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def _read_h3_result_chunk(
    result_path: Path,
    crs: str | int | Any,
    clip_output: bool,
) -> gpd.GeoDataFrame:
    try:
        chunk = gpd.read_parquet(result_path)
    except Exception as exc:
        return _read_h3_result_chunk_with_geometry_repair(
            result_path=result_path,
            crs=crs,
            clip_output=clip_output,
            original_error=exc,
        )

    return _repair_decoded_h3_result_chunk_geometries(
        chunk=chunk,
        result_path=result_path,
        crs=crs,
        clip_output=clip_output,
    )


def _read_h3_result_chunk_with_geometry_repair(
    result_path: Path,
    crs: str | int | Any,
    clip_output: bool,
    original_error: Exception,
) -> gpd.GeoDataFrame:
    table = pq.read_table(result_path)
    if "geometry" not in table.column_names:
        raise ValueError(
            f"H3 result chunk has no geometry column: {result_path}"
        ) from original_error

    frame = table.to_pandas()
    repaired_geometries = []
    repair_details: list[str] = []
    geometry_values = frame["geometry"].tolist()
    for row_number, wkb_geometry in enumerate(geometry_values):
        h3_index = frame.iloc[row_number].get("h3_index") if "h3_index" in frame.columns else None
        try:
            geometry = from_wkb(wkb_geometry) if wkb_geometry is not None else None
        except Exception as exc:
            geometry = _repair_h3_result_geometry(
                geometry=None,
                h3_index=h3_index,
                crs=crs,
                clip_output=clip_output,
                result_path=result_path,
                row_number=row_number,
                original_error=exc,
            )
            repair_details.append(_format_geometry_repair_detail(row_number, h3_index, exc))
        else:
            was_usable = _is_usable_geometry(geometry)
            geometry = _repair_h3_result_geometry(
                geometry=geometry,
                h3_index=h3_index,
                crs=crs,
                clip_output=clip_output,
                result_path=result_path,
                row_number=row_number,
                original_error=None,
            )
            if not was_usable:
                repair_details.append(_format_geometry_repair_detail(row_number, h3_index, None))
        repaired_geometries.append(geometry)

    frame["geometry"] = repaired_geometries
    chunk = gpd.GeoDataFrame(frame, geometry="geometry", crs=crs)
    if repair_details:
        logger.warning(
            "Repaired %s invalid H3 result geometries while reading chunk %s: %s.",
            len(repair_details),
            result_path,
            _format_geometry_repair_details(repair_details),
        )
    return chunk


def _repair_decoded_h3_result_chunk_geometries(
    chunk: gpd.GeoDataFrame,
    result_path: Path,
    crs: str | int | Any,
    clip_output: bool,
) -> gpd.GeoDataFrame:
    repaired = chunk.copy()
    repair_details: list[str] = []
    for row_number, geometry in enumerate(repaired.geometry):
        if _is_usable_geometry(geometry):
            continue
        h3_index = repaired.iloc[row_number].get("h3_index")
        fixed_geometry = _repair_h3_result_geometry(
            geometry=geometry,
            h3_index=h3_index,
            crs=crs,
            clip_output=clip_output,
            result_path=result_path,
            row_number=row_number,
            original_error=None,
        )
        repaired.iat[row_number, repaired.columns.get_loc(repaired.geometry.name)] = fixed_geometry
        repair_details.append(_format_geometry_repair_detail(row_number, h3_index, None))

    if repair_details:
        logger.warning(
            "Repaired %s invalid H3 result geometries while reading chunk %s: %s.",
            len(repair_details),
            result_path,
            _format_geometry_repair_details(repair_details),
        )
    return repaired


def _repair_h3_result_geometry(
    geometry: BaseGeometry | None,
    h3_index: object,
    crs: str | int | Any,
    clip_output: bool,
    result_path: Path,
    row_number: int,
    original_error: Exception | None,
) -> BaseGeometry:
    if _is_usable_geometry(geometry):
        return geometry

    if not clip_output:
        try:
            return _h3_index_geometry_in_crs(h3_index=h3_index, crs=crs)
        except Exception as repair_error:
            error_detail = str(original_error) if original_error is not None else "invalid geometry"
            raise ValueError(
                "Unable to rebuild H3 result chunk geometry: "
                f"path={result_path}, row={row_number}, h3_index={h3_index}, "
                f"error={error_detail}, repair_error={repair_error}"
            ) from original_error or repair_error

    if geometry is not None:
        fixed_geometry = _valid_geometry(geometry)
        if _is_usable_geometry(fixed_geometry):
            return fixed_geometry

    error_detail = str(original_error) if original_error is not None else "invalid geometry"
    raise ValueError(
        "Unable to read H3 result chunk geometry: "
        f"path={result_path}, row={row_number}, h3_index={h3_index}, error={error_detail}"
    ) from original_error


def _h3_index_geometry_in_crs(h3_index: object, crs: str | int | Any) -> BaseGeometry:
    if h3_index is None or pd.isna(h3_index):
        raise ValueError("Cannot rebuild H3 geometry because h3_index is missing.")

    h3_geometry = _h3_cell_to_polygon(str(h3_index))
    projected = gpd.GeoSeries([h3_geometry], crs=WGS84_CRS).to_crs(crs)
    return projected.iloc[0]


def _is_usable_geometry(geometry: BaseGeometry | None) -> bool:
    return geometry is not None and not geometry.is_empty and geometry.is_valid


def _format_geometry_repair_detail(
    row_number: int,
    h3_index: object,
    error: Exception | None,
) -> str:
    detail = f"row={row_number}, h3_index={h3_index}"
    if error is not None:
        detail = f"{detail}, error={error}"
    return detail


def _format_geometry_repair_details(details: list[str]) -> str:
    if len(details) <= 10:
        return "; ".join(details)
    first_details = "; ".join(details[:10])
    return f"{first_details}; ... {len(details) - 10} more"


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


def _write_prepared_grid_chunk_parquets(
    grid_wgs84: gpd.GeoDataFrame,
    aoi: gpd.GeoDataFrame,
    area_crs: str | int,
    workspace: Path,
    chunk_size: int,
    reuse_intermediates: bool,
) -> tuple[list[Path], int | None]:
    chunk_count = _count_chunks(row_count=len(grid_wgs84), chunk_size=chunk_size)
    chunk_dir = workspace / "grid_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_paths = [
        chunk_dir / f"grid_chunk_{chunk_index:05d}.parquet" for chunk_index in range(chunk_count)
    ]
    if reuse_intermediates and _all_paths_exist(_result_chunk_paths(workspace, chunk_count)):
        logger.info(
            "Reusing retained H3 result chunks; skipping H3 overlay grid preparation: chunks=%s.",
            chunk_count,
        )
        return chunk_paths, None
    if reuse_intermediates and _all_paths_exist(chunk_paths):
        logger.info("Reusing prepared H3 overlay grid chunks: chunks=%s.", chunk_count)
        return chunk_paths, None

    aoi_geometry = _union_geometry(aoi.to_crs(area_crs).geometry)
    logger.info(
        "Preparing H3 overlay grid chunks: cells=%s, chunks=%s, chunk_size=%s, area_crs=%s.",
        len(grid_wgs84),
        chunk_count,
        chunk_size,
        area_crs,
    )
    retained_cells = 0
    started_at = perf_counter()
    for chunk_index, chunk_start in enumerate(range(0, len(grid_wgs84), chunk_size)):
        chunk_stop = min(chunk_start + chunk_size, len(grid_wgs84))
        chunk_started_at = perf_counter()
        chunk_path = chunk_paths[chunk_index]
        prepared_chunk = _prepare_h3_overlay_grid_chunk(
            grid_chunk_wgs84=grid_wgs84.iloc[chunk_start:chunk_stop].copy(),
            aoi_geometry=aoi_geometry,
            area_crs=area_crs,
        )
        prepared_chunk.to_parquet(chunk_path, index=False)
        retained_cells += len(prepared_chunk)
        logger.info(
            "Prepared H3 overlay grid chunk %s/%s: input_cells=%s, retained_cells=%s, "
            "total_retained=%s, seconds=%.3f, path=%s.",
            chunk_index + 1,
            chunk_count,
            chunk_stop - chunk_start,
            len(prepared_chunk),
            retained_cells,
            perf_counter() - chunk_started_at,
            chunk_path,
        )

    logger.info(
        "Prepared H3 overlay grid chunks: chunks=%s, positive_area_cells=%s, seconds=%.3f.",
        chunk_count,
        retained_cells,
        perf_counter() - started_at,
    )
    if retained_cells == 0:
        raise ValueError("No positive-area H3 cell intersection remains inside the AOI.")

    return chunk_paths, retained_cells


def _result_chunk_paths(workspace: Path, chunk_count: int) -> list[Path]:
    result_dir = workspace / "result_chunks"
    return [
        result_dir / f"result_chunk_{chunk_index:05d}.parquet" for chunk_index in range(chunk_count)
    ]


def _all_paths_exist(paths: list[Path]) -> bool:
    return bool(paths) and all(path.exists() for path in paths)


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


def _count_chunks(row_count: int, chunk_size: int) -> int:
    if row_count < 1:
        return 0
    return math.ceil(row_count / chunk_size)


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
    h3_totals = {index_column: float(result[index_column].sum()) for index_column in index_columns}
    return _build_total_validation_from_sums(
        source_area=source_area,
        h3_totals=h3_totals,
        index_columns=index_columns,
        tolerance=tolerance,
    )


def _build_total_validation_from_sums(
    source_area: gpd.GeoDataFrame,
    h3_totals: dict[str, float],
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
        h3_total = h3_totals[index_column]
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
    integer_h3_totals = {
        index_column: int(result[index_column].sum()) for index_column in index_columns
    }
    return _build_integer_total_validation_from_sums(
        continuous_total_validation=continuous_total_validation,
        integer_h3_totals=integer_h3_totals,
        index_columns=index_columns,
    )


def _build_integer_total_validation_from_sums(
    continuous_total_validation: pd.DataFrame,
    integer_h3_totals: dict[str, int],
    index_columns: list[str],
) -> pd.DataFrame:
    source_totals = {
        str(row["index"]): _round_half_up(float(row["source_total"]))
        for row in continuous_total_validation.to_dict("records")
    }
    records = []
    for index_column in index_columns:
        source_total = source_totals[index_column]
        h3_total = integer_h3_totals[index_column]
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


def _build_h3_grid_metadata(
    aoi: gpd.GeoDataFrame,
    h3_resolution: int,
    area_crs: str | int,
    boundary_ring_size: int,
    grid_crs: str | int,
) -> dict[str, Any]:
    aoi_geometry = _union_geometry(aoi.geometry)
    aoi_area_geometry = _union_geometry(aoi.to_crs(area_crs).geometry)
    aoi_wgs84_geometry = _union_geometry(aoi.to_crs(WGS84_CRS).geometry)
    return {
        "schema_version": H3_GRID_METADATA_SCHEMA_VERSION,
        "aoi_crs": _crs_to_string(aoi.crs),
        "h3_resolution": h3_resolution,
        "boundary_ring_size": boundary_ring_size,
        "area_crs": _crs_to_string(area_crs),
        "grid_crs": _crs_to_string(grid_crs),
        "aoi_bounds": _h3_grid_metadata_bounds(aoi),
        "aoi_area_sqm": _metadata_float(aoi_area_geometry.area),
        "aoi_geometry_hash": _geometry_hash(aoi_geometry),
        "aoi_geometry_wgs84_hash": _geometry_hash(aoi_wgs84_geometry),
    }


def _crs_to_string(crs: Any) -> str | None:
    if crs is None:
        return None
    crs_object = gpd.GeoDataFrame(geometry=[], crs=crs).crs
    if crs_object is None:
        return None
    return str(crs_object.to_string())


def _h3_grid_metadata_bounds(frame: gpd.GeoDataFrame) -> list[float]:
    return [_metadata_float(value, precision=12) for value in frame.total_bounds.tolist()]


def _metadata_float(value: float, precision: int = 6) -> float:
    return round(float(value), precision)


def _geometry_hash(geometry: BaseGeometry) -> str:
    normalized_geometry = geometry.normalize() if hasattr(geometry, "normalize") else geometry
    return hashlib.sha256(normalized_geometry.wkb).hexdigest()


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
    h3_grid_fingerprint: str,
    source_area: gpd.GeoDataFrame,
    grid_area: gpd.GeoDataFrame,
    grid_chunk_size: int,
) -> dict[str, Any]:
    metadata = _build_common_intermediate_metadata(
        census_data_path=census_data_path,
        layer_name=layer_name,
        year=year,
        h3_resolution=h3_resolution,
        index_columns=index_columns,
        municipality_codes=municipality_codes,
        special_section_policy=special_section_policy,
        boundary_ring_size=boundary_ring_size,
        include_density=include_density,
        clip_output=clip_output,
        area_crs=area_crs,
        output_crs=output_crs,
        h3_grid_fingerprint=h3_grid_fingerprint,
        source_area=source_area,
    )
    metadata.update(
        {
            "grid_preparation_mode": "materialized",
            "grid_chunk_size": grid_chunk_size,
            "grid_crs": str(grid_area.crs),
            "grid_rows": len(grid_area),
            "grid_total_bounds": _metadata_bounds(grid_area),
        }
    )
    return metadata


def _build_chunked_intermediate_metadata(
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
    h3_grid_fingerprint: str,
    source_area: gpd.GeoDataFrame,
    grid_wgs84: gpd.GeoDataFrame,
    grid_chunk_size: int,
) -> dict[str, Any]:
    metadata = _build_common_intermediate_metadata(
        census_data_path=census_data_path,
        layer_name=layer_name,
        year=year,
        h3_resolution=h3_resolution,
        index_columns=index_columns,
        municipality_codes=municipality_codes,
        special_section_policy=special_section_policy,
        boundary_ring_size=boundary_ring_size,
        include_density=include_density,
        clip_output=clip_output,
        area_crs=area_crs,
        output_crs=output_crs,
        h3_grid_fingerprint=h3_grid_fingerprint,
        source_area=source_area,
    )
    metadata.update(
        {
            "grid_preparation_mode": "chunked_parquet",
            "grid_chunk_size": grid_chunk_size,
            "grid_chunk_count": _count_chunks(
                row_count=len(grid_wgs84),
                chunk_size=grid_chunk_size,
            ),
            "grid_crs": _crs_to_string(area_crs),
            "grid_input_crs": str(grid_wgs84.crs),
            "grid_input_rows": len(grid_wgs84),
            "grid_input_total_bounds": _metadata_bounds(grid_wgs84),
        }
    )
    return metadata


def _build_common_intermediate_metadata(
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
    h3_grid_fingerprint: str,
    source_area: gpd.GeoDataFrame,
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
        "h3_grid_fingerprint": h3_grid_fingerprint,
        "source_crs": str(source_area.crs),
        "source_rows": len(source_area),
        "source_total_bounds": _metadata_bounds(source_area),
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
    max_in_flight_chunks: int | None,
) -> tuple[int, int, str, int | None]:
    if not isinstance(workers, int) or isinstance(workers, bool) or workers < 1:
        raise ValueError("workers must be an integer greater than or equal to 1.")
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size < 1:
        raise ValueError("chunk_size must be an integer greater than or equal to 1.")
    if parallel_backend not in PARALLEL_BACKENDS:
        backends = ", ".join(PARALLEL_BACKENDS)
        raise ValueError(f"parallel_backend must be one of: {backends}.")
    if max_in_flight_chunks is not None and (
        not isinstance(max_in_flight_chunks, int)
        or isinstance(max_in_flight_chunks, bool)
        or max_in_flight_chunks < 1
    ):
        raise ValueError(
            "max_in_flight_chunks must be None or an integer greater than or equal to 1."
        )
    return workers, chunk_size, parallel_backend, max_in_flight_chunks


def _resolve_max_in_flight_chunks(
    max_in_flight_chunks: int | None,
    active_workers: int,
    chunk_count: int,
) -> int:
    if chunk_count < 1:
        return 1
    selected_limit = active_workers if max_in_flight_chunks is None else max_in_flight_chunks
    return min(selected_limit, chunk_count)
