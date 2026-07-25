from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from scripts.estimate_h3_census import main

WGS84_CRS = "EPSG:4326"


def test_estimate_h3_census_script_writes_level_11_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=_source_cells())
    aoi_path = _write_aoi(tmp_path=tmp_path, geometry=box(12.0, 41.0, 12.02, 41.01))
    output_path = tmp_path / "h3_estimates.gpkg"

    exit_code = main(
        [
            "--census-data",
            str(census_path),
            "--year",
            "2021",
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--indexes",
            "P1",
            "P2",
            "--workers",
            "2",
            "--chunk-size",
            "2",
            "--output",
            str(output_path),
            "--output-layer",
            "h3_test",
        ]
    )
    captured = capsys.readouterr()
    saved = gpd.read_file(output_path, layer="h3_test")

    assert exit_code == 0
    assert output_path.exists()
    assert "H3 level-11 cells" in captured.out
    assert "within tolerance" in captured.out
    assert saved["h3_resolution"].unique().tolist() == [11]
    assert saved["year"].unique().tolist() == [2021]
    assert saved["P1"].sum() == pytest.approx(300.0, rel=1e-4)
    assert saved["P2"].sum() == pytest.approx(120.0, rel=1e-4)


def test_estimate_h3_census_script_filters_municipality_codes(
    tmp_path: Path,
):
    source = _source_cells()
    source.loc[1, "PRO_COM"] = "58092"
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=source)
    aoi_path = _write_aoi(tmp_path=tmp_path, geometry=box(12.0, 41.0, 12.02, 41.01))
    output_path = tmp_path / "h3_estimates.gpkg"

    exit_code = main(
        [
            "--census-data",
            str(census_path),
            "--year",
            "2021",
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--indexes",
            "P1",
            "--municipality-code",
            "58091",
            "--output",
            str(output_path),
        ]
    )
    saved = gpd.read_file(output_path, layer="h3_census2021_r11")

    assert exit_code == 0
    assert saved["P1"].sum() == pytest.approx(100.0, rel=1e-4)


def test_estimate_h3_census_script_reports_missing_aoi_crs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    census_path = _write_census_geopackage(tmp_path=tmp_path, source=_source_cells())
    aoi_path = tmp_path / "aoi_without_crs.gpkg"
    gpd.GeoDataFrame(
        geometry=[box(12.0, 41.0, 12.02, 41.01)],
    ).to_file(aoi_path, layer="aoi", driver="GPKG")

    exit_code = main(
        [
            "--census-data",
            str(census_path),
            "--year",
            "2021",
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--indexes",
            "P1",
            "--output",
            str(tmp_path / "h3_estimates.gpkg"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "AOI file has no CRS" in captured.err


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
