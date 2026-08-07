from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from istat_census_data.config import PREPROCESSING_FOLDER
from istat_census_data.h3_estimation import (
    DEFAULT_BOUNDARY_RING_SIZE,
    DEFAULT_SPECIAL_SECTION_POLICY,
)
from istat_census_data.h3_workflow import (
    H3CensusWorkflowResult,
    run_h3_census_workflow,
)

WGS84_CRS = "EPSG:4326"


def test_run_h3_census_workflow_orchestrates_selected_years(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    calls: list[tuple[str, dict[str, object]]] = []

    def fake_download_census(**kwargs: object) -> None:
        calls.append(("download", kwargs))

    def fake_preprocess_census(**kwargs: object) -> Path:
        calls.append(("preprocess", kwargs))
        return tmp_path / "data"

    def fake_finalize_census_data(**kwargs: object) -> None:
        calls.append(("finalize", kwargs))
        Path(kwargs["census_data_path"]).joinpath("census_data.gpkg").touch()

    def fake_estimate_h3_census_indexes(**kwargs: object) -> gpd.GeoDataFrame:
        calls.append(("estimate", kwargs))
        return _result_frame(year=int(kwargs["year"]))

    grid_calls: list[dict[str, object]] = []
    shared_grid = _grid_frame()

    def fake_generate_h3_grid(**kwargs: object) -> gpd.GeoDataFrame:
        grid_calls.append(kwargs)
        return shared_grid

    monkeypatch.setattr("istat_census_data.h3_workflow.download_census", fake_download_census)
    monkeypatch.setattr("istat_census_data.h3_workflow.preprocess_census", fake_preprocess_census)
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.finalize_census_data",
        fake_finalize_census_data,
    )
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.estimate_h3_census_indexes",
        fake_estimate_h3_census_indexes,
    )
    monkeypatch.setattr("istat_census_data.h3_workflow.generate_h3_grid", fake_generate_h3_grid)

    data_folder = tmp_path / "data"
    output_path = tmp_path / "h3.gpkg"
    result = run_h3_census_workflow(
        years=[2011, 2021],
        data_folder=data_folder,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        indexes=["P1", "P2"],
        output_path=output_path,
        region_list=[1, 2],
        municipality_codes=["58091"],
        clip_output=True,
        workers=2,
        chunk_size=3,
        parallel_backend="dask",
    )

    assert isinstance(result, H3CensusWorkflowResult)
    assert result.years == (2011, 2021)
    assert result.output_path == output_path
    assert result.layers == {
        2011: "h3_census2011_r11",
        2021: "h3_census2021_r11",
    }
    assert [call[0] for call in calls] == [
        "download",
        "preprocess",
        "finalize",
        "estimate",
        "estimate",
    ]
    assert calls[0][1] == {
        "years": [2011, 2021],
        "output_data_folder": data_folder,
        "region_list": [1, 2],
    }
    assert calls[1][1] == {
        "processed_data_folder": data_folder / PREPROCESSING_FOLDER,
        "years": [2011, 2021],
        "output_data_folder": data_folder,
        "delete_download_folder": False,
        "municipalities_code": [58091],
    }
    assert calls[2][1] == {
        "census_data_path": data_folder,
        "years": [2011, 2021],
        "output_data_folder": data_folder,
        "delete_preprocessed_data": False,
    }
    estimate_calls = [kwargs for name, kwargs in calls if name == "estimate"]
    assert [call["year"] for call in estimate_calls] == [2011, 2021]
    assert all(
        call["census_data_path"] == data_folder / "census_data.gpkg" for call in estimate_calls
    )
    assert all(call["h3_resolution"] == 11 for call in estimate_calls)
    assert all(
        call["special_section_policy"] == DEFAULT_SPECIAL_SECTION_POLICY for call in estimate_calls
    )
    assert all(call["municipality_codes"] == [58091] for call in estimate_calls)
    assert all(call["clip_output"] is True for call in estimate_calls)
    assert all(call["boundary_ring_size"] == DEFAULT_BOUNDARY_RING_SIZE for call in estimate_calls)
    assert all(call["workers"] == 2 for call in estimate_calls)
    assert all(call["chunk_size"] == 3 for call in estimate_calls)
    assert all(call["parallel_backend"] == "dask" for call in estimate_calls)
    assert all(call["max_in_flight_chunks"] is None for call in estimate_calls)
    assert all(call["stream_output"] is False for call in estimate_calls)
    assert len(grid_calls) == 1
    assert all(call["h3_grid"] is shared_grid for call in estimate_calls)
    assert [call["output_layer"] for call in estimate_calls] == [
        "h3_census2011_r11",
        "h3_census2021_r11",
    ]


def test_run_h3_census_workflow_rejects_empty_and_unsupported_years(tmp_path: Path):
    with pytest.raises(ValueError, match="At least one census year"):
        run_h3_census_workflow(years=[], data_folder=tmp_path, aoi=box(12.0, 41.0, 12.01, 41.01))

    with pytest.raises(ValueError, match="Unsupported census year"):
        run_h3_census_workflow(
            years=[2023],
            data_folder=tmp_path,
            aoi=box(12.0, 41.0, 12.01, 41.01),
        )


def test_run_h3_census_workflow_can_reuse_existing_finalized_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    (data_folder / "census_data.gpkg").touch()

    def fail_stage(**kwargs: object) -> None:
        raise AssertionError(f"stage should have been skipped: {kwargs}")

    def fake_estimate_h3_census_indexes(**kwargs: object) -> gpd.GeoDataFrame:
        return _result_frame(year=int(kwargs["year"]))

    monkeypatch.setattr("istat_census_data.h3_workflow.download_census", fail_stage)
    monkeypatch.setattr("istat_census_data.h3_workflow.preprocess_census", fail_stage)
    monkeypatch.setattr("istat_census_data.h3_workflow.finalize_census_data", fail_stage)
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.estimate_h3_census_indexes",
        fake_estimate_h3_census_indexes,
    )
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.generate_h3_grid",
        lambda **kwargs: _grid_frame(),
    )

    result = run_h3_census_workflow(
        years=[2021],
        data_folder=data_folder,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        run_download=False,
        run_preprocess=False,
        run_finalize=False,
    )

    assert result.census_data_path == data_folder / "census_data.gpkg"
    assert result.layers == {2021: "h3_census2021_r11"}
    assert result.results[2021]["h3_resolution"].unique().tolist() == [11]
    assert result.row_counts == {2021: 1}


def test_run_h3_census_workflow_can_discard_yearly_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    data_folder = tmp_path / "data"
    data_folder.mkdir()
    (data_folder / "census_data.gpkg").touch()
    estimate_calls: list[dict[str, object]] = []

    def fail_stage(**kwargs: object) -> None:
        raise AssertionError(f"stage should have been skipped: {kwargs}")

    def fake_estimate_h3_census_indexes(**kwargs: object) -> gpd.GeoDataFrame:
        estimate_calls.append(kwargs)
        result = _result_frame(year=int(kwargs["year"]))
        if kwargs.get("stream_output"):
            streamed = gpd.GeoDataFrame(geometry=[], crs=WGS84_CRS)
            streamed.attrs.update(result.attrs)
            streamed.attrs["row_count"] = int(kwargs["year"]) - 2000
            return streamed
        return result

    monkeypatch.setattr("istat_census_data.h3_workflow.download_census", fail_stage)
    monkeypatch.setattr("istat_census_data.h3_workflow.preprocess_census", fail_stage)
    monkeypatch.setattr("istat_census_data.h3_workflow.finalize_census_data", fail_stage)
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.estimate_h3_census_indexes",
        fake_estimate_h3_census_indexes,
    )
    monkeypatch.setattr(
        "istat_census_data.h3_workflow.generate_h3_grid",
        lambda **kwargs: _grid_frame(),
    )

    result = run_h3_census_workflow(
        years=[2011, 2021],
        data_folder=data_folder,
        aoi=box(12.0, 41.0, 12.02, 41.01),
        run_download=False,
        run_preprocess=False,
        run_finalize=False,
        max_in_flight_chunks=2,
        retain_results=False,
    )

    assert result.results == {}
    assert result.row_counts == {2011: 11, 2021: 21}
    assert sorted(result.total_validations) == [2011, 2021]
    assert sorted(result.integer_total_validations) == [2011, 2021]
    assert [call["max_in_flight_chunks"] for call in estimate_calls] == [2, 2]
    assert [call["stream_output"] for call in estimate_calls] == [True, True]


def test_run_h3_census_workflow_requires_finalized_data_after_skipped_finalize(
    tmp_path: Path,
):
    with pytest.raises(FileNotFoundError, match="census_data.gpkg"):
        run_h3_census_workflow(
            years=[2021],
            data_folder=tmp_path / "data",
            aoi=box(12.0, 41.0, 12.01, 41.01),
            run_download=False,
            run_preprocess=False,
            run_finalize=False,
        )


def _result_frame(year: int) -> gpd.GeoDataFrame:
    frame = gpd.GeoDataFrame(
        {"year": [year], "h3_resolution": [11], "P1": [10.0]},
        geometry=[box(12.0, 41.0, 12.01, 41.01)],
        crs=WGS84_CRS,
    )
    frame.attrs["total_validation"] = pd.DataFrame(
        [{"index": "P1", "source_total": 10.0, "h3_total": 10.0, "within_tolerance": True}]
    )
    frame.attrs["integer_total_validation"] = pd.DataFrame(
        [{"index": "P1", "source_total": 10, "h3_total": 10, "within_tolerance": True}]
    )
    return frame


def _grid_frame() -> gpd.GeoDataFrame:
    frame = gpd.GeoDataFrame(
        {
            "h3_index": ["8b1e2"],
            "h3_resolution": [11],
            "h3_cell_area_sqm": [1.0],
        },
        geometry=[box(12.0, 41.0, 12.01, 41.01)],
        crs=WGS84_CRS,
    )
    frame.attrs["h3_grid_fingerprint"] = "test-grid"
    frame.attrs["h3_grid_metadata"] = {"fingerprint": "test-grid"}
    return frame
