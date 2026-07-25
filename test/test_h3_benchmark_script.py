from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from scripts import benchmark_h3_estimation

WGS84_CRS = "EPSG:4326"


def test_benchmark_h3_estimation_script_records_worker_and_chunk_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    captured_calls: list[dict[str, object]] = []
    aoi_path = _write_aoi(tmp_path=tmp_path)
    output_json = tmp_path / "benchmark.json"

    def fake_estimate_h3_census_indexes(**kwargs: object) -> gpd.GeoDataFrame:
        captured_calls.append(kwargs)
        result = gpd.GeoDataFrame(
            {"h3_index": ["abc"], "P1": [1.0]},
            geometry=[box(12.0, 41.0, 12.01, 41.01)],
            crs=WGS84_CRS,
        )
        result.attrs["total_validation"] = pd.DataFrame([{"index": "P1", "within_tolerance": True}])
        return result

    monkeypatch.setattr(
        benchmark_h3_estimation,
        "estimate_h3_census_indexes",
        fake_estimate_h3_census_indexes,
    )

    exit_code = benchmark_h3_estimation.main(
        [
            "--census-data",
            str(tmp_path / "census_data.gpkg"),
            "--year",
            "2021",
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--indexes",
            "P1",
            "--workers",
            "1",
            "2",
            "--chunk-size",
            "2",
            "--parallel-backend",
            "dask",
            "--runs",
            "1",
            "--output-json",
            str(output_json),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "workers chunk_size backend run seconds h3_cells validation" in captured.out
    assert output_json.exists()
    assert [call["workers"] for call in captured_calls] == [1, 2]
    assert [call["chunk_size"] for call in captured_calls] == [2, 2]
    assert all(call["parallel_backend"] == "dask" for call in captured_calls)


def test_benchmark_h3_estimation_script_rejects_invalid_runs(tmp_path: Path):
    aoi_path = _write_aoi(tmp_path=tmp_path)

    exit_code = benchmark_h3_estimation.main(
        [
            "--census-data",
            str(tmp_path / "census_data.gpkg"),
            "--year",
            "2021",
            "--aoi",
            str(aoi_path),
            "--aoi-layer",
            "aoi",
            "--runs",
            "0",
        ]
    )

    assert exit_code == 1


def _write_aoi(tmp_path: Path) -> Path:
    aoi_path = tmp_path / "aoi.gpkg"
    gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.02, 41.01)], crs=WGS84_CRS).to_file(
        aoi_path,
        layer="aoi",
        driver="GPKG",
    )
    return aoi_path
