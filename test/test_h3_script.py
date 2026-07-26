from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from scripts import estimate_h3_census

WGS84_CRS = "EPSG:4326"


def test_estimate_h3_census_script_run_writes_level_11_output(tmp_path: Path):
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=_source_cells())
    aoi_path = _write_aoi(tmp_path=tmp_path, geometry=box(12.0, 41.0, 12.02, 41.01))
    output_path = tmp_path / "h3_estimates.gpkg"

    result = estimate_h3_census.run(
        census_data_path=census_path,
        year=2021,
        aoi_path=aoi_path,
        output_path=output_path,
        indexes=["P1", "P2"],
        aoi_layer="aoi",
        aoi_crs=None,
        municipality_codes=None,
        special_section_policy="exclude",
        area_crs="EPSG:3035",
        clip_output=False,
        workers=2,
        chunk_size=2,
        parallel_backend="thread",
        output_layer="h3_test",
    )
    saved = gpd.read_file(output_path, layer="h3_test")

    assert output_path.exists()
    assert len(result) == len(saved)
    assert saved["h3_resolution"].unique().tolist() == [11]
    assert saved["year"].unique().tolist() == [2021]
    assert saved["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert saved["P2"].sum() == pytest.approx(120.0, rel=1e-4)


def test_estimate_h3_census_script_empty_indexes_use_all_additive(tmp_path: Path):
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=_source_cells())
    aoi_path = _write_aoi(tmp_path=tmp_path, geometry=box(12.0, 41.0, 12.02, 41.01))
    output_path = tmp_path / "h3_estimates.gpkg"

    result = estimate_h3_census.run(
        census_data_path=census_path,
        year=2021,
        aoi_path=aoi_path,
        output_path=output_path,
        indexes=[],
        aoi_layer="aoi",
        aoi_crs=None,
        municipality_codes=None,
        special_section_policy="exclude",
        area_crs="EPSG:3035",
        clip_output=False,
        workers=1,
        chunk_size=5000,
        parallel_backend="thread",
        output_layer="h3_test",
    )

    assert {"P1", "P2"}.issubset(result.columns)
    assert result["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert result["P2"].sum() == pytest.approx(120.0, rel=1e-4)


def test_estimate_h3_census_script_filters_municipality_codes(tmp_path: Path):
    source = _source_cells()
    source.loc[1, "PRO_COM"] = "58092"
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi_path = _write_aoi(tmp_path=tmp_path, geometry=box(12.0, 41.0, 12.02, 41.01))
    output_path = tmp_path / "h3_estimates.gpkg"

    estimate_h3_census.run(
        census_data_path=census_path,
        year=2021,
        aoi_path=aoi_path,
        output_path=output_path,
        indexes=["P1"],
        aoi_layer="aoi",
        aoi_crs=None,
        municipality_codes=["58091"],
        special_section_policy="exclude",
        area_crs="EPSG:3035",
        clip_output=False,
        workers=1,
        chunk_size=5000,
        parallel_backend="thread",
        output_layer=None,
    )
    saved = gpd.read_file(output_path, layer="h3_census2021_r11")

    assert saved["P1"].sum() == pytest.approx(100.0, rel=1e-4)


def test_estimate_h3_census_script_reports_missing_aoi_crs(tmp_path: Path):
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=_source_cells())
    aoi_path = tmp_path / "aoi_without_crs.gpkg"
    gpd.GeoDataFrame(
        geometry=[box(12.0, 41.0, 12.02, 41.01)],
    ).to_file(aoi_path, layer="aoi", driver="GPKG")

    with pytest.raises(ValueError, match="AOI file has no CRS"):
        estimate_h3_census.run(
            census_data_path=census_path,
            year=2021,
            aoi_path=aoi_path,
            output_path=tmp_path / "h3_estimates.gpkg",
            indexes=["P1"],
            aoi_layer="aoi",
            aoi_crs=None,
            municipality_codes=None,
            special_section_policy="exclude",
            area_crs="EPSG:3035",
            clip_output=False,
            workers=1,
            chunk_size=5000,
            parallel_backend="thread",
            output_layer=None,
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


def _write_aoi(tmp_path: Path, geometry: object) -> Path:
    aoi_path = tmp_path / "aoi.gpkg"
    gpd.GeoDataFrame(geometry=[geometry], crs=WGS84_CRS).to_file(
        aoi_path, layer="aoi", driver="GPKG"
    )
    return aoi_path
