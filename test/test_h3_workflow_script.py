from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

from istat_census_data.h3_workflow import H3CensusWorkflowResult
from scripts import run_h3_census_analysis

WGS84_CRS = "EPSG:4326"


def test_run_h3_census_analysis_script_passes_selected_years_to_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    captured_kwargs: dict[str, object] = {}
    aoi_path = _write_aoi(tmp_path=tmp_path)
    data_dir = tmp_path / "data"
    output_path = tmp_path / "h3_output.gpkg"

    def fake_run_h3_census_workflow(**kwargs: object) -> H3CensusWorkflowResult:
        captured_kwargs.update(kwargs)
        years = tuple(int(year) for year in kwargs["years"])
        results = {year: _result_frame(year=year) for year in years}
        return H3CensusWorkflowResult(
            data_folder=Path(kwargs["data_folder"]),
            census_data_path=Path(kwargs["data_folder"]) / "census_data.gpkg",
            output_path=Path(kwargs["output_path"]),
            years=years,
            layers={year: f"h3_census{year}_r11" for year in years},
            results=results,
        )

    monkeypatch.setattr(
        run_h3_census_analysis,
        "run_h3_census_workflow",
        fake_run_h3_census_workflow,
    )

    exit_code = run_h3_census_analysis.main(
        [
            "--years",
            "2011",
            "2021",
            "--data-dir",
            str(data_dir),
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--indexes",
            "P1",
            "P2",
            "--region-code",
            "1",
            "2",
            "--municipality-code",
            "58091",
            "--skip-download",
            "--workers",
            "2",
            "--chunk-size",
            "3",
            "--parallel-backend",
            "dask",
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "H3 census workflow completed" in captured.out
    assert "2011" in captured.out
    assert "2021" in captured.out
    assert captured_kwargs["years"] == [2011, 2021]
    assert captured_kwargs["data_folder"] == data_dir
    assert captured_kwargs["indexes"] == ["P1", "P2"]
    assert captured_kwargs["region_list"] == [1, 2]
    assert captured_kwargs["municipality_codes"] == ["58091"]
    assert captured_kwargs["special_section_policy"] == "exclude"
    assert captured_kwargs["run_download"] is False
    assert captured_kwargs["run_preprocess"] is True
    assert captured_kwargs["run_finalize"] is True
    assert captured_kwargs["workers"] == 2
    assert captured_kwargs["chunk_size"] == 3
    assert captured_kwargs["parallel_backend"] == "dask"
    assert captured_kwargs["output_path"] == output_path


def test_run_h3_census_analysis_script_defaults_to_all_additive_indexes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    captured_kwargs: dict[str, object] = {}
    aoi_path = _write_aoi(tmp_path=tmp_path)

    def fake_run_h3_census_workflow(**kwargs: object) -> H3CensusWorkflowResult:
        captured_kwargs.update(kwargs)
        data_folder = Path(kwargs["data_folder"])
        return H3CensusWorkflowResult(
            data_folder=data_folder,
            census_data_path=data_folder / "census_data.gpkg",
            output_path=data_folder / "h3_census_data.gpkg",
            years=(2021,),
            layers={2021: "h3_census2021_r11"},
            results={2021: _result_frame(year=2021)},
        )

    monkeypatch.setattr(
        run_h3_census_analysis,
        "run_h3_census_workflow",
        fake_run_h3_census_workflow,
    )

    exit_code = run_h3_census_analysis.main(
        [
            "--years",
            "2021",
            "--data-dir",
            str(tmp_path / "data"),
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["indexes"] == "all_additive"
    assert captured_kwargs["output_path"] is None


def test_run_h3_census_analysis_script_reports_missing_aoi_crs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    aoi_path = tmp_path / "aoi_without_crs.gpkg"
    gpd.GeoDataFrame(
        geometry=[box(12.0, 41.0, 12.02, 41.01)],
    ).to_file(aoi_path, layer="aoi", driver="GPKG")

    exit_code = run_h3_census_analysis.main(
        [
            "--years",
            "2021",
            "--data-dir",
            str(tmp_path / "data"),
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--skip-download",
            "--skip-preprocess",
            "--skip-finalize",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "AOI file has no CRS" in captured.err


def _write_aoi(tmp_path: Path) -> Path:
    aoi_path = tmp_path / "aoi.gpkg"
    gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.02, 41.01)], crs=WGS84_CRS).to_file(
        aoi_path,
        layer="aoi",
        driver="GPKG",
    )
    return aoi_path


def _result_frame(year: int) -> gpd.GeoDataFrame:
    frame = gpd.GeoDataFrame(
        {"year": [year], "h3_resolution": [11], "P1": [10.0]},
        geometry=[box(12.0, 41.0, 12.01, 41.01)],
        crs=WGS84_CRS,
    )
    return frame
