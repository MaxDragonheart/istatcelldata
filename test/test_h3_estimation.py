import importlib
import json
import logging
import sqlite3
import struct
import threading
import warnings
from pathlib import Path
from time import sleep
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from shapely.geometry import Polygon, box

import istat_census_data
from istat_census_data import h3_estimation as h3_module
from istat_census_data.catalog import get_census_index_catalog
from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_BOUNDARY_RING_SIZE,
    DEFAULT_INTERMEDIATE_STORAGE,
    REQUIRED_H3_RESOLUTION,
    estimate_h3_census_indexes,
    generate_h3_grid,
)

WGS84_CRS = "EPSG:4326"


def test_root_package_exports_h3_estimation_api():
    assert "estimate_h3_census_indexes" in istat_census_data.__all__
    assert "generate_h3_grid" in istat_census_data.__all__
    assert "REQUIRED_H3_RESOLUTION" in istat_census_data.__all__
    assert "DEFAULT_BOUNDARY_RING_SIZE" in istat_census_data.__all__
    assert "DEFAULT_INTERMEDIATE_STORAGE" in istat_census_data.__all__
    assert callable(istat_census_data.estimate_h3_census_indexes)
    assert callable(istat_census_data.generate_h3_grid)
    assert istat_census_data.REQUIRED_H3_RESOLUTION == REQUIRED_H3_RESOLUTION
    assert istat_census_data.DEFAULT_BOUNDARY_RING_SIZE == DEFAULT_BOUNDARY_RING_SIZE
    assert istat_census_data.DEFAULT_INTERMEDIATE_STORAGE == DEFAULT_INTERMEDIATE_STORAGE


def test_generate_h3_grid_returns_intersecting_cells_with_area_metadata():
    aoi = box(12.0, 41.0, 12.02, 41.01)

    grid = generate_h3_grid(aoi=aoi)

    assert not grid.empty
    assert grid.crs.to_string() == WGS84_CRS
    assert {"h3_index", "h3_resolution", "h3_cell_area_sqm"}.issubset(grid.columns)
    assert grid["h3_resolution"].unique().tolist() == [REQUIRED_H3_RESOLUTION]
    assert grid["h3_index"].is_unique
    assert (grid["h3_cell_area_sqm"] > 0).all()
    assert grid.intersects(aoi).all()


def test_generate_h3_grid_uses_robust_boundary_ring_by_default():
    aoi = box(12.0, 41.0, 12.02, 41.01)

    default_grid = generate_h3_grid(aoi=aoi)
    explicit_grid = generate_h3_grid(
        aoi=aoi,
        boundary_ring_size=DEFAULT_BOUNDARY_RING_SIZE,
    )

    assert DEFAULT_BOUNDARY_RING_SIZE == 3
    assert default_grid["h3_index"].tolist() == explicit_grid["h3_index"].tolist()


def test_generate_h3_grid_records_reuse_metadata():
    aoi = box(12.0, 41.0, 12.02, 41.01)

    grid = generate_h3_grid(aoi=aoi)

    metadata = grid.attrs["h3_grid_metadata"]
    assert grid.attrs["h3_grid_fingerprint"]
    assert metadata["aoi_crs"] == WGS84_CRS
    assert metadata["h3_resolution"] == REQUIRED_H3_RESOLUTION
    assert metadata["boundary_ring_size"] == DEFAULT_BOUNDARY_RING_SIZE
    assert metadata["area_crs"] == DEFAULT_AREA_CRS
    assert metadata["grid_crs"] == WGS84_CRS
    assert metadata["aoi_bounds"] == [12.0, 41.0, 12.02, 41.01]
    assert metadata["aoi_area_sqm"] > 0
    assert metadata["aoi_geometry_hash"]


def test_generate_h3_grid_logs_progress(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="istat_census_data.h3_estimation")

    generate_h3_grid(aoi=box(12.0, 41.0, 12.002, 41.002))

    messages = [record.getMessage() for record in caplog.records]
    assert any("Starting H3 grid generation" in message for message in messages)
    assert any("Computing H3 seed cells" in message for message in messages)
    assert any("Filtering H3 candidate cells" in message for message in messages)
    assert any("Completed H3 grid generation" in message for message in messages)


def test_generate_h3_grid_filters_candidates_in_bounded_chunks(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    caplog.set_level(logging.INFO, logger="istat_census_data.h3_estimation")
    aoi = box(12.0, 41.0, 12.001, 41.001)
    cell_geometries = {
        "cell_a": box(12.0, 41.0, 12.0004, 41.0004),
        "cell_b": box(13.0, 42.0, 13.0004, 42.0004),
        "cell_c": box(12.0005, 41.0005, 12.0015, 41.0015),
    }

    def fake_candidate_h3_cells(**kwargs: object) -> set[str]:
        return set(cell_geometries)

    def fake_h3_cell_to_polygon(h3_index: str) -> Polygon:
        return cell_geometries[h3_index]

    monkeypatch.setattr(h3_module, "H3_GRID_FILTER_CHUNK_SIZE", 2)
    monkeypatch.setattr(h3_module, "H3_GRID_PROGRESS_LOG_INTERVAL", 2)
    monkeypatch.setattr(h3_module, "_candidate_h3_cells", fake_candidate_h3_cells)
    monkeypatch.setattr(h3_module, "_h3_cell_to_polygon", fake_h3_cell_to_polygon)

    grid = generate_h3_grid(aoi=aoi)

    messages = [record.getMessage() for record in caplog.records]
    assert grid["h3_index"].tolist() == ["cell_a", "cell_c"]
    assert grid["h3_index"].is_unique
    assert any(
        "Filtered H3 candidate cells: processed=2/3, retained=1." in message for message in messages
    )


def test_prepare_overlay_inputs_log_progress(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO, logger="istat_census_data.h3_estimation")
    aoi = gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.002, 41.002)], crs=WGS84_CRS)
    source = _source_cells()
    grid = generate_h3_grid(aoi=aoi)

    source_area = h3_module._prepare_source_cells(
        source=source,
        aoi=aoi,
        area_crs=DEFAULT_AREA_CRS,
        index_columns=["P1"],
        year=2021,
        special_section_policy="exclude",
    )
    grid_area = h3_module._prepare_h3_overlay_grid(
        grid_wgs84=grid,
        aoi=aoi,
        area_crs=DEFAULT_AREA_CRS,
    )

    messages = [record.getMessage() for record in caplog.records]
    assert not source_area.empty
    assert not grid_area.empty
    assert any("Preparing source census cells" in message for message in messages)
    assert any("Prepared source census cells" in message for message in messages)
    assert any("Preparing H3 overlay grid" in message for message in messages)
    assert any("Prepared H3 overlay grid" in message for message in messages)


def test_prepare_h3_overlay_grid_uses_requested_chunk_size(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.INFO, logger="istat_census_data.h3_estimation")
    aoi = gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.005, 41.001)], crs=WGS84_CRS)
    grid = gpd.GeoDataFrame(
        {
            "h3_index": [f"cell_{index}" for index in range(5)],
            "h3_resolution": [REQUIRED_H3_RESOLUTION] * 5,
            "h3_cell_area_sqm": [100.0] * 5,
        },
        geometry=[
            box(12.000 + index * 0.001, 41.0, 12.001 + index * 0.001, 41.001) for index in range(5)
        ],
        crs=WGS84_CRS,
    )
    chunk_sizes: list[int] = []
    real_prepare_chunk = h3_module._prepare_h3_overlay_grid_chunk

    def spy_prepare_chunk(**kwargs: object) -> gpd.GeoDataFrame:
        grid_chunk_wgs84 = kwargs["grid_chunk_wgs84"]
        assert isinstance(grid_chunk_wgs84, gpd.GeoDataFrame)
        chunk_sizes.append(len(grid_chunk_wgs84))
        return real_prepare_chunk(**kwargs)

    monkeypatch.setattr(h3_module, "_prepare_h3_overlay_grid_chunk", spy_prepare_chunk)

    grid_area = h3_module._prepare_h3_overlay_grid(
        grid_wgs84=grid,
        aoi=aoi,
        area_crs=DEFAULT_AREA_CRS,
        chunk_size=2,
    )

    messages = [record.getMessage() for record in caplog.records]
    assert not grid_area.empty
    assert chunk_sizes == [2, 2, 1]
    assert any("Prepared H3 overlay grid chunk 3/3" in message for message in messages)


def test_generate_h3_grid_rejects_non_level_11_resolution():
    with pytest.raises(ValueError, match="requires h3_resolution=11"):
        generate_h3_grid(aoi=box(12.0, 41.0, 12.02, 41.01), h3_resolution=10)


def test_estimate_h3_census_indexes_preserves_totals_for_complete_aoi(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        indexes=["P1", "P2"],
    )

    assert not result.empty
    assert {
        "h3_index",
        "year",
        "P1",
        "P2",
        "P1_density_per_sq_km",
        "aoi_coverage_ratio",
    }.issubset(result.columns)
    assert result["year"].unique().tolist() == [2021]
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert result["P2"].sum() == pytest.approx(120.0, rel=1e-4)
    assert pd.api.types.is_integer_dtype(result["P1"])
    assert pd.api.types.is_integer_dtype(result["P2"])
    assert result.attrs["source_totals"]["P1"] == pytest.approx(300.0, rel=1e-4)
    assert result.attrs["h3_totals"]["P2"] == pytest.approx(120.0, rel=1e-4)
    assert result.attrs["total_validation"]["within_tolerance"].all()
    assert result.attrs["integer_total_validation"]["within_tolerance"].all()
    assert result.attrs["boundary_ring_size"] == DEFAULT_BOUNDARY_RING_SIZE


def test_estimate_h3_census_indexes_uses_catalogue_additive_default(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
    )

    assert {"P1", "P2"}.issubset(result.columns)
    assert "SEZ2021" not in result.columns
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert pd.api.types.is_integer_dtype(result["P1"])


def test_estimate_h3_census_indexes_empty_index_list_uses_all_additive(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=[],
    )

    assert {"P1", "P2"}.issubset(result.columns)
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert result["P2"].sum() == pytest.approx(120.0, rel=1e-4)
    assert pd.api.types.is_integer_dtype(result["P1"])
    assert pd.api.types.is_integer_dtype(result["P2"])


def test_estimate_h3_census_indexes_handles_partial_aoi_overlap(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.005, 41.01)
    expected_total = _expected_partial_total(source=source.iloc[[0]], aoi=aoi, column="P1")

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
    )

    assert 0 < result["P1"].sum() < 100
    assert result["P1"].sum() == int(expected_total + 0.5)
    assert pd.api.types.is_integer_dtype(result["P1"])
    assert result.attrs["source_totals"]["P1"] == pytest.approx(expected_total)
    assert result.attrs["total_validation"]["within_tolerance"].all()
    assert result.attrs["integer_total_validation"]["within_tolerance"].all()


def test_estimate_h3_census_indexes_reprojects_source_and_aoi(tmp_path: Path):
    source = _source_cells().to_crs("EPSG:3857")
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.02, 41.01)], crs=WGS84_CRS)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
    )

    assert result.crs.to_string() == WGS84_CRS
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert result.attrs["total_validation"]["within_tolerance"].all()


def test_estimate_h3_census_indexes_repairs_invalid_and_skips_zero_area_cells(
    tmp_path: Path,
):
    invalid_polygon = Polygon(
        [
            (12.0, 41.0),
            (12.01, 41.01),
            (12.01, 41.0),
            (12.0, 41.01),
            (12.0, 41.0),
        ]
    )
    zero_area_polygon = Polygon([(12.02, 41.0), (12.03, 41.0), (12.04, 41.0), (12.02, 41.0)])
    source = gpd.GeoDataFrame(
        {
            "SEZ2021": ["5809100001", "5809100002"],
            "PRO_COM": ["58091", "58091"],
            "P1": [100, 999],
        },
        geometry=[invalid_polygon, zero_area_polygon],
        crs=WGS84_CRS,
    )
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        indexes=["P1"],
    )

    assert result["P1"].sum() == pytest.approx(100.0)
    assert result.attrs["total_validation"]["within_tolerance"].all()


def test_estimate_h3_census_indexes_supports_special_section_policies(tmp_path: Path):
    source = _source_cells()
    source.loc[0, "SEZ2021"] = "580918888881"
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    default_excluded = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
    )
    included = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
        special_section_policy="include",
    )
    excluded = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
        special_section_policy="exclude",
    )

    assert default_excluded["P1"].sum() == pytest.approx(200.0, rel=1e-4)
    assert default_excluded["special_section_policy"].unique().tolist() == ["exclude"]
    assert not default_excluded["intersects_special_section"].any()
    assert included["intersects_special_section"].any()
    assert included["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert excluded["P1"].sum() == pytest.approx(200.0, rel=1e-4)
    with pytest.raises(ValueError, match="Special/fictitious census sections"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            special_section_policy="raise",
        )


def test_estimate_h3_census_indexes_filters_municipality_codes_and_writes_output(
    tmp_path: Path,
):
    source = _source_cells()
    source.loc[1, "PRO_COM"] = "58092"
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    output_path = tmp_path / "h3_estimates.gpkg"

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        indexes=["P1"],
        municipality_codes=[58091],
        output_path=output_path,
        output_layer="test_h3",
    )
    saved = gpd.read_file(output_path, layer="test_h3")

    assert result["P1"].sum() == pytest.approx(100.0, rel=1e-4)
    assert output_path.exists()
    assert pd.api.types.is_integer_dtype(result["P1"])
    assert pd.api.types.is_integer_dtype(saved["P1"])
    assert saved["P1"].sum() == pytest.approx(100.0, rel=1e-4)


def test_estimate_h3_census_indexes_filters_float_municipality_codes(tmp_path: Path):
    source = _source_cells()
    source["PRO_COM"] = [58091.0, 58092.0]
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        indexes=["P1"],
        municipality_codes=[58091],
    )

    assert result["P1"].sum() == pytest.approx(100.0, rel=1e-4)
    assert pd.api.types.is_integer_dtype(result["P1"])
    assert result.attrs["integer_total_validation"]["within_tolerance"].all()


def test_estimate_h3_census_indexes_reuses_precomputed_h3_grid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)
    h3_grid = generate_h3_grid(aoi=aoi)

    def fail_grid_generation(**kwargs: object) -> gpd.GeoDataFrame:
        raise AssertionError(f"grid should have been reused: {kwargs}")

    monkeypatch.setattr(h3_module, "generate_h3_grid", fail_grid_generation)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        h3_grid=h3_grid,
    )

    assert result.attrs["h3_grid_reused"] is True
    assert result.attrs["h3_grid_fingerprint"] == h3_grid.attrs["h3_grid_fingerprint"]
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)


def test_estimate_h3_census_indexes_rejects_mismatched_h3_grid(
    tmp_path: Path,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)
    h3_grid = generate_h3_grid(aoi=aoi)
    same_bounds_different_geometry = Polygon(
        [
            (12.0, 41.0),
            (12.02, 41.0),
            (12.02, 41.01),
            (12.01, 41.01),
            (12.01, 41.005),
            (12.0, 41.005),
            (12.0, 41.0),
        ]
    )

    with pytest.raises(ValueError, match="AOI and grid parameters"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=same_bounds_different_geometry,
            indexes=["P1"],
            h3_grid=h3_grid,
        )
    with pytest.raises(ValueError, match="AOI and grid parameters"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            boundary_ring_size=1,
            h3_grid=h3_grid,
        )
    with pytest.raises(ValueError, match="AOI and grid parameters"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            area_crs="EPSG:3857",
            h3_grid=h3_grid,
        )


def test_estimate_h3_census_indexes_parallel_matches_serial(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    serial = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=1,
    )
    parallel = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=2,
        chunk_size=2,
    )

    serial = serial.sort_values("h3_index").reset_index(drop=True)
    parallel = parallel.sort_values("h3_index").reset_index(drop=True)
    assert parallel["h3_index"].tolist() == serial["h3_index"].tolist()
    assert parallel.geometry.to_wkb().tolist() == serial.geometry.to_wkb().tolist()
    assert parallel.attrs["workers"] == 2
    assert parallel.attrs["chunk_size"] == 2
    assert parallel.attrs["parallel_backend"] == "thread"
    for column in [
        "P1",
        "P2",
        "P1_density_per_sq_km",
        "P2_density_per_sq_km",
        "source_intersection_area_sqm",
        "aoi_coverage_ratio",
    ]:
        assert parallel[column].tolist() == pytest.approx(serial[column].tolist(), rel=1e-9)
    assert parallel.attrs["total_validation"]["within_tolerance"].all()


def test_estimate_h3_census_indexes_default_parquet_retains_intermediates(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        indexes=["P1", "P2"],
        workers=2,
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
    )

    retained_dir = Path(result.attrs["h3_intermediate_dir"])
    assert result.attrs["intermediate_storage"] == "parquet"
    assert result.attrs["h3_intermediates_retained"] is True
    assert result.attrs["boundary_ring_size"] == DEFAULT_BOUNDARY_RING_SIZE
    assert retained_dir.parent == intermediate_dir
    assert (retained_dir / "metadata.json").exists()
    assert (retained_dir / "prepared_source.parquet").exists()
    assert not (retained_dir / "h3_grid.parquet").exists()
    assert list((retained_dir / "grid_chunks").glob("grid_chunk_*.parquet"))
    assert list((retained_dir / "result_chunks").glob("result_chunk_*.parquet"))
    metadata = json.loads((retained_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["metadata"]["grid_preparation_mode"] == "chunked_parquet"
    assert metadata["metadata"]["grid_chunk_size"] == 2
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)


def test_estimate_h3_census_indexes_parquet_prepares_grid_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"
    aoi = box(12.0, 41.0, 12.002, 41.002)
    h3_grid = generate_h3_grid(aoi=aoi)
    chunk_sizes: list[int] = []
    real_prepare_chunk = h3_module._prepare_h3_overlay_grid_chunk

    def fail_materialized_grid_preparation(**kwargs: object) -> gpd.GeoDataFrame:
        raise AssertionError(f"materialized grid preparation should not run: {kwargs}")

    def spy_prepare_chunk(**kwargs: object) -> gpd.GeoDataFrame:
        grid_chunk_wgs84 = kwargs["grid_chunk_wgs84"]
        assert isinstance(grid_chunk_wgs84, gpd.GeoDataFrame)
        chunk_sizes.append(len(grid_chunk_wgs84))
        return real_prepare_chunk(**kwargs)

    monkeypatch.setattr(
        h3_module,
        "_prepare_h3_overlay_grid",
        fail_materialized_grid_preparation,
    )
    monkeypatch.setattr(h3_module, "_prepare_h3_overlay_grid_chunk", spy_prepare_chunk)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1"],
        h3_grid=h3_grid,
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
    )

    retained_dir = Path(result.attrs["h3_intermediate_dir"])
    metadata = json.loads((retained_dir / "metadata.json").read_text(encoding="utf-8"))
    grid_chunk_paths = sorted((retained_dir / "grid_chunks").glob("grid_chunk_*.parquet"))
    assert result.attrs["total_validation"]["within_tolerance"].all()
    assert chunk_sizes
    assert max(chunk_sizes) <= 2
    assert len(grid_chunk_paths) == metadata["metadata"]["grid_chunk_count"]
    assert not (retained_dir / "h3_grid.parquet").exists()


def test_estimate_h3_census_indexes_reuses_retained_parquet_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"
    aoi = box(12.0, 41.0, 12.02, 41.01)

    first = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=2,
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
    )

    def fail_recalculation(**kwargs: object) -> gpd.GeoDataFrame:
        raise AssertionError(f"chunk should have been reused: {kwargs}")

    monkeypatch.setattr(
        "istat_census_data.h3_estimation._estimate_intersections_serial",
        fail_recalculation,
    )
    second = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=2,
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
        reuse_intermediates=True,
    )

    assert second.attrs["h3_intermediate_dir"] == first.attrs["h3_intermediate_dir"]
    assert second["P1"].sum() == pytest.approx(first["P1"].sum(), rel=1e-9)


def test_finalize_h3_result_chunks_to_geopackage_streams_retained_chunks(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"
    output_path = tmp_path / "h3_streamed.gpkg"

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.002, 41.002),
        indexes=["P1", "P2"],
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
    )
    retained_dir = Path(result.attrs["h3_intermediate_dir"])

    streamed = h3_module.finalize_h3_result_chunks_to_geopackage(
        intermediate_workspace=retained_dir,
        output_path=output_path,
        output_layer="streamed_h3",
        index_batch_size=1,
    )
    saved = gpd.read_file(output_path, layer="streamed_h3")

    assert streamed.output_path == output_path
    assert streamed.output_layer == "streamed_h3"
    assert streamed.row_count == len(result)
    assert streamed.integer_total_validation["within_tolerance"].all()
    assert saved.crs.to_string() == WGS84_CRS
    assert len(saved) == len(result)
    assert saved["P1"].sum() == pytest.approx(result["P1"].sum(), rel=1e-9)
    assert saved["P2"].sum() == pytest.approx(result["P2"].sum(), rel=1e-9)
    assert pd.api.types.is_integer_dtype(saved["P1"])
    assert "P1_density_per_sq_km" in saved.columns
    assert _has_unique_h3_index(output_path=output_path, output_layer="streamed_h3")
    assert _has_spatial_index(output_path=output_path, output_layer="streamed_h3")

    with pytest.raises(ValueError, match="GeoPackage layer already exists"):
        h3_module.finalize_h3_result_chunks_to_geopackage(
            intermediate_workspace=retained_dir,
            output_path=output_path,
            output_layer="streamed_h3",
        )


def test_estimate_h3_census_indexes_streams_geopackage_output_without_global_merge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"
    output_path = tmp_path / "h3_streamed.gpkg"

    def fail_global_merge(**kwargs: object) -> pd.DataFrame:
        raise AssertionError(f"global result chunk merge should not run: {kwargs}")

    monkeypatch.setattr(h3_module, "_merge_result_chunk_parquets", fail_global_merge)

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.002, 41.002),
        indexes=["P1", "P2"],
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
        output_path=output_path,
        output_layer="streamed_h3",
        stream_output=True,
    )
    saved = gpd.read_file(output_path, layer="streamed_h3")

    assert result.empty
    assert result.attrs["stream_output"] is True
    assert result.attrs["row_count"] == len(saved)
    assert result.attrs["output_path"] == str(output_path)
    assert result.attrs["output_layer"] == "streamed_h3"
    assert result.attrs["integer_total_validation"]["within_tolerance"].all()
    assert saved.crs.to_string() == WGS84_CRS
    assert pd.api.types.is_integer_dtype(saved["P1"])
    assert "P1_density_per_sq_km" in saved.columns
    assert _has_unique_h3_index(output_path=output_path, output_layer="streamed_h3")
    assert _has_spatial_index(output_path=output_path, output_layer="streamed_h3")


def test_quote_sql_identifier_escapes_double_quotes():
    assert h3_module._quote_sql_identifier("plain_name") == '"plain_name"'
    assert h3_module._quote_sql_identifier('name"with"quotes') == '"name""with""quotes"'


def test_finalize_h3_result_chunks_rejects_duplicate_h3_index(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    intermediate_dir = tmp_path / "h3_intermediates"
    output_path = tmp_path / "h3_streamed.gpkg"

    result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=box(12.0, 41.0, 12.002, 41.002),
        indexes=["P1"],
        chunk_size=2,
        intermediate_dir=intermediate_dir,
        keep_intermediates=True,
    )
    retained_dir = Path(result.attrs["h3_intermediate_dir"])
    first_chunk_path = sorted((retained_dir / "result_chunks").glob("result_chunk_*.parquet"))[0]
    first_chunk = gpd.read_parquet(first_chunk_path)
    first_chunk.loc[first_chunk.index[1], "h3_index"] = first_chunk.loc[
        first_chunk.index[0], "h3_index"
    ]
    first_chunk.to_parquet(first_chunk_path, index=False)

    with pytest.raises(ValueError, match="duplicate h3_index values"):
        h3_module.finalize_h3_result_chunks_to_geopackage(
            intermediate_workspace=retained_dir,
            output_path=output_path,
            output_layer="streamed_h3",
        )


def test_estimate_h3_census_indexes_memory_path_avoids_fragmentation_warning(tmp_path: Path):
    source = _source_cells_with_many_indexes()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always", pd.errors.PerformanceWarning)
        result = estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=box(12.0, 41.0, 12.002, 41.002),
            indexes=[],
            intermediate_storage="memory",
        )

    performance_warnings = [
        warning
        for warning in captured_warnings
        if issubclass(warning.category, pd.errors.PerformanceWarning)
    ]
    assert performance_warnings == []
    assert "P1" in result.columns
    assert "P1_density_per_sq_km" in result.columns


def test_estimate_h3_census_indexes_dask_backend_matches_serial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    def fake_delayed(function):
        def delayed_call(**kwargs):
            return lambda: function(**kwargs)

        return delayed_call

    def fake_compute(*tasks, **kwargs):
        assert kwargs == {"scheduler": "threads", "num_workers": 2}
        return tuple(task() for task in tasks)

    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "dask":
            return SimpleNamespace(delayed=fake_delayed, compute=fake_compute)
        return real_import_module(name)

    monkeypatch.setattr(
        "istat_census_data.h3_estimation.importlib.import_module",
        fake_import_module,
    )

    serial = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=1,
    )
    dask_result = estimate_h3_census_indexes(
        census_data_path=census_path,
        year=2021,
        aoi=aoi,
        indexes=["P1", "P2"],
        workers=2,
        chunk_size=2,
        parallel_backend="dask",
    )

    serial = serial.sort_values("h3_index").reset_index(drop=True)
    dask_result = dask_result.sort_values("h3_index").reset_index(drop=True)
    assert dask_result["h3_index"].tolist() == serial["h3_index"].tolist()
    assert dask_result["P1"].tolist() == pytest.approx(serial["P1"].tolist(), rel=1e-9)
    assert dask_result["P2"].tolist() == pytest.approx(serial["P2"].tolist(), rel=1e-9)
    assert dask_result.attrs["parallel_backend"] == "dask"


def test_parquet_thread_backend_limits_in_flight_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    active_chunks = 0
    max_active_chunks = 0
    lock = threading.Lock()
    grid_chunk_paths = [tmp_path / f"grid_{chunk_index}.parquet" for chunk_index in range(5)]
    result_chunk_paths = [tmp_path / f"result_{chunk_index}.parquet" for chunk_index in range(5)]

    def fake_chunk_to_parquet(**kwargs: object) -> Path:
        nonlocal active_chunks, max_active_chunks
        with lock:
            active_chunks += 1
            max_active_chunks = max(max_active_chunks, active_chunks)
        try:
            sleep(0.01)
            return Path(kwargs["result_path"])
        finally:
            with lock:
                active_chunks -= 1

    monkeypatch.setattr(
        h3_module,
        "_estimate_intersections_chunk_to_parquet",
        fake_chunk_to_parquet,
    )

    completed_paths = h3_module._estimate_parquet_chunk_paths_with_executor(
        source_path=tmp_path / "source.parquet",
        grid_chunk_paths=grid_chunk_paths,
        result_chunk_paths=result_chunk_paths,
        index_columns=["P1"],
        year=2021,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        special_section_policy="exclude",
        include_density=True,
        clip_output=False,
        workers=4,
        parallel_backend="thread",
        reuse_intermediates=False,
        max_in_flight_chunks=2,
    )

    assert completed_paths == result_chunk_paths
    assert max_active_chunks <= 2


def test_parquet_dask_backend_computes_bounded_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    batch_sizes: list[int] = []
    grid_chunk_paths = [tmp_path / f"grid_{chunk_index}.parquet" for chunk_index in range(5)]
    result_chunk_paths = [tmp_path / f"result_{chunk_index}.parquet" for chunk_index in range(5)]

    def fake_chunk_to_parquet(**kwargs: object) -> Path:
        return Path(kwargs["result_path"])

    def fake_delayed(function):
        def delayed_call(**kwargs):
            return lambda: function(**kwargs)

        return delayed_call

    def fake_compute(*tasks, **kwargs):
        assert kwargs == {"scheduler": "threads", "num_workers": 4}
        batch_sizes.append(len(tasks))
        return tuple(task() for task in tasks)

    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "dask":
            return SimpleNamespace(delayed=fake_delayed, compute=fake_compute)
        return real_import_module(name)

    monkeypatch.setattr(
        h3_module,
        "_estimate_intersections_chunk_to_parquet",
        fake_chunk_to_parquet,
    )
    monkeypatch.setattr(
        "istat_census_data.h3_estimation.importlib.import_module",
        fake_import_module,
    )

    completed_paths = h3_module._estimate_parquet_chunk_paths_with_dask(
        source_path=tmp_path / "source.parquet",
        grid_chunk_paths=grid_chunk_paths,
        result_chunk_paths=result_chunk_paths,
        index_columns=["P1"],
        year=2021,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        special_section_policy="exclude",
        include_density=True,
        clip_output=False,
        workers=4,
        reuse_intermediates=False,
        max_in_flight_chunks=2,
    )

    assert completed_paths == result_chunk_paths
    assert batch_sizes == [2, 2, 1]


def test_result_chunk_merge_repairs_unreadable_h3_geometry(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.WARNING, logger="istat_census_data.h3_estimation")
    result_path = tmp_path / "result_chunk_00000.parquet"
    h3_index = h3_module.h3.latlng_to_cell(41.9, 12.5, REQUIRED_H3_RESOLUTION)
    _write_raw_result_chunk_with_invalid_wkb(result_path=result_path, h3_index=h3_index)

    merged = h3_module._merge_result_chunk_parquets(
        result_chunk_paths=[result_path],
        crs=DEFAULT_AREA_CRS,
        clip_output=False,
    )

    assert len(merged) == 1
    assert merged.loc[0, "h3_index"] == h3_index
    assert merged.loc[0, "geometry"].is_valid
    assert merged.loc[0, "geometry"].area > 0
    messages = [record.getMessage() for record in caplog.records]
    assert any("Repaired 1 invalid H3 result geometries" in message for message in messages)
    assert any("row=0" in message and h3_index in message for message in messages)


def test_result_chunk_merge_reports_unrepairable_clipped_geometry(tmp_path: Path):
    result_path = tmp_path / "result_chunk_00000.parquet"
    h3_index = h3_module.h3.latlng_to_cell(41.9, 12.5, REQUIRED_H3_RESOLUTION)
    _write_raw_result_chunk_with_invalid_wkb(result_path=result_path, h3_index=h3_index)

    with pytest.raises(ValueError) as exc_info:
        h3_module._merge_result_chunk_parquets(
            result_chunk_paths=[result_path],
            crs=DEFAULT_AREA_CRS,
            clip_output=True,
        )

    message = str(exc_info.value)
    assert str(result_path) in message
    assert "row=0" in message
    assert h3_index in message
    assert "Points of LinearRing do not form a closed linestring" in message


def test_memory_thread_backend_limits_in_flight_chunks(
    monkeypatch: pytest.MonkeyPatch,
):
    active_chunks = 0
    max_active_chunks = 0
    lock = threading.Lock()
    chunks = [_chunk_frame(chunk_index) for chunk_index in range(5)]

    def fake_serial(**kwargs: object) -> gpd.GeoDataFrame:
        nonlocal active_chunks, max_active_chunks
        with lock:
            active_chunks += 1
            max_active_chunks = max(max_active_chunks, active_chunks)
        try:
            sleep(0.01)
            grid_area = kwargs["grid_area"]
            assert isinstance(grid_area, gpd.GeoDataFrame)
            return grid_area.copy()
        finally:
            with lock:
                active_chunks -= 1

    monkeypatch.setattr(h3_module, "_estimate_intersections_serial", fake_serial)

    completed_results = h3_module._estimate_intersections_with_executor(
        source_area=_chunk_frame(99),
        chunks=chunks,
        index_columns=["P1"],
        year=2021,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        special_section_policy="exclude",
        include_density=True,
        clip_output=False,
        workers=4,
        parallel_backend="thread",
        max_in_flight_chunks=2,
    )

    assert [int(result["chunk_index"].iloc[0]) for result in completed_results] == list(range(5))
    assert max_active_chunks <= 2


def test_memory_dask_backend_computes_bounded_batches(monkeypatch: pytest.MonkeyPatch):
    batch_sizes: list[int] = []
    chunks = [_chunk_frame(chunk_index) for chunk_index in range(5)]

    def fake_serial(**kwargs: object) -> gpd.GeoDataFrame:
        grid_area = kwargs["grid_area"]
        assert isinstance(grid_area, gpd.GeoDataFrame)
        return grid_area.copy()

    def fake_delayed(function):
        def delayed_call(**kwargs):
            return lambda: function(**kwargs)

        return delayed_call

    def fake_compute(*tasks, **kwargs):
        assert kwargs == {"scheduler": "threads", "num_workers": 4}
        batch_sizes.append(len(tasks))
        return tuple(task() for task in tasks)

    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "dask":
            return SimpleNamespace(delayed=fake_delayed, compute=fake_compute)
        return real_import_module(name)

    monkeypatch.setattr(h3_module, "_estimate_intersections_serial", fake_serial)
    monkeypatch.setattr(
        "istat_census_data.h3_estimation.importlib.import_module",
        fake_import_module,
    )

    completed_results = h3_module._estimate_intersections_with_dask(
        source_area=_chunk_frame(99),
        chunks=chunks,
        index_columns=["P1"],
        year=2021,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        special_section_policy="exclude",
        include_density=True,
        clip_output=False,
        workers=4,
        max_in_flight_chunks=2,
    )

    assert [int(result["chunk_index"].iloc[0]) for result in completed_results] == list(range(5))
    assert batch_sizes == [2, 2, 1]


def test_estimate_h3_census_indexes_dask_backend_requires_optional_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)

    def fake_import_module(name: str):
        if name == "dask":
            raise ImportError("missing dask")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(
        "istat_census_data.h3_estimation.importlib.import_module",
        fake_import_module,
    )

    with pytest.raises(ImportError, match="istat-census-data\\[dask\\]"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=box(12.0, 41.0, 12.02, 41.01),
            indexes=["P1"],
            workers=2,
            chunk_size=2,
            parallel_backend="dask",
        )


def test_estimate_h3_census_indexes_rejects_invalid_parallel_options(tmp_path: Path):
    source = _source_cells()
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi = box(12.0, 41.0, 12.02, 41.01)

    with pytest.raises(ValueError, match="workers"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            workers=0,
        )
    with pytest.raises(ValueError, match="chunk_size"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            chunk_size=0,
        )
    with pytest.raises(ValueError, match="parallel_backend"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            parallel_backend="invalid",
        )
    with pytest.raises(ValueError, match="intermediate_storage"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            intermediate_storage="invalid",
        )
    with pytest.raises(ValueError, match="max_in_flight_chunks"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            max_in_flight_chunks=0,
        )
    with pytest.raises(ValueError, match="reuse_intermediates"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            reuse_intermediates=True,
        )
    with pytest.raises(ValueError, match="stream_output"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            stream_output=True,
        )
    with pytest.raises(ValueError, match="intermediate_storage"):
        estimate_h3_census_indexes(
            census_data_path=census_path,
            year=2021,
            aoi=aoi,
            indexes=["P1"],
            output_path=tmp_path / "streamed.gpkg",
            intermediate_storage="memory",
            stream_output=True,
        )


def _source_cells() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "SEZ2021": ["5809100001", "5809100002"],
            "PRO_COM": ["58091", "58091"],
            "P1": [100, 200],
            "P2": [40, 80],
        },
        geometry=[
            box(12.0, 41.0, 12.01, 41.01),
            box(12.01, 41.0, 12.02, 41.01),
        ],
        crs=WGS84_CRS,
    )


def _source_cells_with_many_indexes() -> gpd.GeoDataFrame:
    catalog = get_census_index_catalog(year=2021)
    index_columns = [
        str(source_code)
        for source_code in catalog[catalog["is_additive"].astype(bool)]["source_code"].tolist()
    ]
    data: dict[str, list[float] | list[str]] = {
        "SEZ2021": ["5809100001", "5809100002"],
        "PRO_COM": ["58091", "58091"],
    }
    for position, index_column in enumerate(index_columns, start=1):
        data[index_column] = [float(position), float(position * 2)]

    return gpd.GeoDataFrame(
        data,
        geometry=[
            box(12.0, 41.0, 12.001, 41.002),
            box(12.001, 41.0, 12.002, 41.002),
        ],
        crs=WGS84_CRS,
    )


def _write_census_geopackage(tmp_path: Path, source: gpd.GeoDataFrame) -> Path:
    census_path = tmp_path / "census_data.gpkg"
    source.to_file(census_path, layer="census2021", driver="GPKG")
    return census_path


def _has_unique_h3_index(output_path: Path, output_layer: str) -> bool:
    with sqlite3.connect(output_path) as connection:
        for index_row in connection.execute(f'PRAGMA index_list("{output_layer}")'):
            index_name = str(index_row[1])
            is_unique = bool(index_row[2])
            if not is_unique:
                continue
            indexed_columns = [
                str(column_row[2])
                for column_row in connection.execute(f'PRAGMA index_info("{index_name}")')
            ]
            if indexed_columns == ["h3_index"]:
                return True
    return False


def _has_spatial_index(output_path: Path, output_layer: str) -> bool:
    with sqlite3.connect(output_path) as connection:
        geometry_column_row = connection.execute(
            "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
            (output_layer,),
        ).fetchone()
        if geometry_column_row is None:
            return False
        rtree_table = f"rtree_{output_layer}_{geometry_column_row[0]}"
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (rtree_table,),
            ).fetchone()
            is not None
        )


def _write_raw_result_chunk_with_invalid_wkb(result_path: Path, h3_index: str) -> None:
    table = pa.table(
        {
            "h3_index": [h3_index],
            "h3_resolution": [REQUIRED_H3_RESOLUTION],
            "geometry": [_invalid_unclosed_polygon_wkb()],
            "year": [2021],
            "special_section_policy": ["exclude"],
            "P1": [1.0],
            "source_intersection_area_sqm": [1.0],
            "intersects_special_section": [False],
            "aoi_coverage_ratio": [1.0],
        }
    )
    pq.write_table(table, result_path)


def _invalid_unclosed_polygon_wkb() -> bytes:
    coordinates = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    parts = [
        struct.pack("<BI", 1, 3),
        struct.pack("<I", 1),
        struct.pack("<I", len(coordinates)),
    ]
    parts.extend(struct.pack("<dd", x, y) for x, y in coordinates)
    return b"".join(parts)


def _chunk_frame(chunk_index: int) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"chunk_index": [chunk_index]},
        geometry=[box(float(chunk_index), 0.0, float(chunk_index) + 0.5, 0.5)],
        crs=WGS84_CRS,
    )


def _expected_partial_total(source: gpd.GeoDataFrame, aoi: Polygon, column: str) -> float:
    source_area = source.to_crs(DEFAULT_AREA_CRS)
    aoi_area = gpd.GeoSeries([aoi], crs=WGS84_CRS).to_crs(DEFAULT_AREA_CRS).iloc[0]
    source_geometry = source_area.geometry.iloc[0]
    coverage_ratio = source_geometry.intersection(aoi_area).area / source_geometry.area
    return float(source_area[column].iloc[0] * coverage_ratio)
