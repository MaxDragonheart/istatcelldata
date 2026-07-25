from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, box

import istat_census_data
from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    REQUIRED_H3_RESOLUTION,
    estimate_h3_census_indexes,
    generate_h3_grid,
)

WGS84_CRS = "EPSG:4326"


def test_root_package_exports_h3_estimation_api():
    assert "estimate_h3_census_indexes" in istat_census_data.__all__
    assert "generate_h3_grid" in istat_census_data.__all__
    assert "REQUIRED_H3_RESOLUTION" in istat_census_data.__all__
    assert callable(istat_census_data.estimate_h3_census_indexes)
    assert callable(istat_census_data.generate_h3_grid)
    assert istat_census_data.REQUIRED_H3_RESOLUTION == REQUIRED_H3_RESOLUTION


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
    assert result.attrs["source_totals"]["P1"] == pytest.approx(300.0, rel=1e-4)
    assert result.attrs["h3_totals"]["P2"] == pytest.approx(120.0, rel=1e-4)
    assert result.attrs["total_validation"]["within_tolerance"].all()


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
    assert result["P1"].sum() == pytest.approx(expected_total)
    assert result.attrs["source_totals"]["P1"] == pytest.approx(expected_total)
    assert result.attrs["total_validation"]["within_tolerance"].all()


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
    assert saved["P1"].sum() == pytest.approx(100.0, rel=1e-4)


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

    monkeypatch.setattr(
        "istat_census_data.h3_estimation.importlib.import_module",
        lambda name: SimpleNamespace(delayed=fake_delayed, compute=fake_compute)
        if name == "dask"
        else None,
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


def _write_census_geopackage(tmp_path: Path, source: gpd.GeoDataFrame) -> Path:
    census_path = tmp_path / "census_data.gpkg"
    source.to_file(census_path, layer="census2021", driver="GPKG")
    return census_path


def _expected_partial_total(source: gpd.GeoDataFrame, aoi: Polygon, column: str) -> float:
    source_area = source.to_crs(DEFAULT_AREA_CRS)
    aoi_area = gpd.GeoSeries([aoi], crs=WGS84_CRS).to_crs(DEFAULT_AREA_CRS).iloc[0]
    source_geometry = source_area.geometry.iloc[0]
    coverage_ratio = source_geometry.intersection(aoi_area).area / source_geometry.area
    return float(source_area[column].iloc[0] * coverage_ratio)
