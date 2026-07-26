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

    result = run_h3_census_analysis.run(
        years=[2011, 2021],
        regions=[1, 2],
        data_dir=data_dir,
        aoi_path=aoi_path,
        indexes=[],
        output_path=output_path,
        output_layer_prefix="h3_census",
        aoi_layer="aoi",
        aoi_crs=None,
        municipality_codes=["58091"],
        special_section_policy="exclude",
        area_crs="EPSG:3035",
        clip_output=False,
        workers=2,
        chunk_size=3,
        parallel_backend="dask",
        run_download=False,
        run_preprocess=True,
        run_finalize=True,
        delete_download_folder=False,
        delete_preprocessed_data=False,
    )

    assert result.years == (2011, 2021)
    assert captured_kwargs["years"] == [2011, 2021]
    assert captured_kwargs["data_folder"] == data_dir
    assert captured_kwargs["indexes"] == []
    assert captured_kwargs["region_list"] == [1, 2]
    assert captured_kwargs["municipality_codes"] == ["58091"]
    assert captured_kwargs["special_section_policy"] == "exclude"
    assert captured_kwargs["run_download"] is False
    assert captured_kwargs["run_preprocess"] is True
    assert captured_kwargs["run_finalize"] is True
    assert captured_kwargs["boundary_ring_size"] == 3
    assert captured_kwargs["workers"] == 2
    assert captured_kwargs["chunk_size"] == 3
    assert captured_kwargs["parallel_backend"] == "dask"
    assert captured_kwargs["output_path"] == output_path


def test_run_h3_census_analysis_script_reports_missing_aoi_crs(tmp_path: Path):
    aoi_path = tmp_path / "aoi_without_crs.gpkg"
    gpd.GeoDataFrame(
        geometry=[box(12.0, 41.0, 12.02, 41.01)],
    ).to_file(aoi_path, layer="aoi", driver="GPKG")

    with pytest.raises(ValueError, match="AOI file has no CRS"):
        run_h3_census_analysis.run(
            years=[2021],
            regions=[],
            data_dir=tmp_path / "data",
            aoi_path=aoi_path,
            indexes=[],
            output_path=tmp_path / "h3_output.gpkg",
            output_layer_prefix="h3_census",
            aoi_layer="aoi",
            aoi_crs=None,
            municipality_codes=None,
            special_section_policy="exclude",
            area_crs="EPSG:3035",
            clip_output=False,
            workers=1,
            chunk_size=5000,
            parallel_backend="thread",
            run_download=False,
            run_preprocess=False,
            run_finalize=False,
            delete_download_folder=False,
            delete_preprocessed_data=False,
        )


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
