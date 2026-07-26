import json
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
):
    captured_calls: list[dict[str, object]] = []
    aoi_path = _write_aoi(tmp_path=tmp_path)
    output_path = tmp_path / "benchmark.json"

    def fake_estimate_h3_census_indexes(**kwargs: object) -> gpd.GeoDataFrame:
        if captured_calls:
            assert output_path.exists()
            written_records = json.loads(output_path.read_text(encoding="utf-8"))
            assert len(written_records) == len(captured_calls)
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

    records = benchmark_h3_estimation.run_benchmark(
        census_data_path=tmp_path / "census_data.gpkg",
        year=2021,
        aoi_path=aoi_path,
        indexes=[],
        aoi_layer="aoi",
        aoi_crs=None,
        municipality_codes=None,
        special_section_policy="exclude",
        area_crs="EPSG:3035",
        workers=[1, 2],
        chunk_sizes=[2],
        parallel_backend="dask",
        runs=1,
        output_path=output_path,
    )

    assert len(records) == 2
    written_records = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(written_records) == 2
    assert all(record["boundary_ring_size"] == 3 for record in written_records)
    assert [call["workers"] for call in captured_calls] == [1, 2]
    assert [call["chunk_size"] for call in captured_calls] == [2, 2]
    assert all(call["parallel_backend"] == "dask" for call in captured_calls)
    assert all(call["boundary_ring_size"] == 3 for call in captured_calls)
    assert all(call["indexes"] == [] for call in captured_calls)
    assert all(call["intermediate_storage"] == "parquet" for call in captured_calls)


def test_benchmark_h3_estimation_script_rejects_invalid_runs(tmp_path: Path):
    aoi_path = _write_aoi(tmp_path=tmp_path)

    with pytest.raises(ValueError, match="runs must be greater than or equal to 1"):
        benchmark_h3_estimation.run_benchmark(
            census_data_path=tmp_path / "census_data.gpkg",
            year=2021,
            aoi_path=aoi_path,
            indexes=[],
            aoi_layer="aoi",
            aoi_crs=None,
            municipality_codes=None,
            special_section_policy="exclude",
            area_crs="EPSG:3035",
            workers=[1],
            chunk_sizes=[5000],
            parallel_backend="thread",
            runs=0,
        )


def _write_aoi(tmp_path: Path) -> Path:
    aoi_path = tmp_path / "aoi.gpkg"
    gpd.GeoDataFrame(geometry=[box(12.0, 41.0, 12.02, 41.01)], crs=WGS84_CRS).to_file(
        aoi_path,
        layer="aoi",
        driver="GPKG",
    )
    return aoi_path
