import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import geopandas as gpd

from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_H3_CHUNK_SIZE,
    DEFAULT_PARALLEL_BACKEND,
    DEFAULT_SPECIAL_SECTION_POLICY,
    REQUIRED_H3_RESOLUTION,
    estimate_h3_census_indexes,
)
from istat_census_data.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census_test")
census_data_path = main_path / "census_data.gpkg"
aoi_path = main_path / "aoi.gpkg"
benchmark_output_path = main_path / "h3_benchmark.json"
selected_year = 2021
selected_indexes: list[str] = []
municipalities_code: list[str] | None = None
aoi_layer: str | None = None
aoi_crs: str | None = None
worker_counts = [1, 2, 4]
chunk_sizes = [DEFAULT_H3_CHUNK_SIZE]
parallel_backend = DEFAULT_PARALLEL_BACKEND
runs = 1


# Configure logging at the start of the script.
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="benchmark_h3_estimation",
    )


# Define the logger as a global variable.
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkRecord:
    """One H3 benchmark measurement."""

    workers: int
    chunk_size: int
    parallel_backend: str
    run: int
    seconds: float
    h3_cells: int
    validation_passed: bool


def run_benchmark(
    census_data_path: Path,
    year: int,
    aoi_path: Path,
    indexes: list[str],
    aoi_layer: str | None,
    aoi_crs: str | None,
    municipality_codes: list[str] | None,
    special_section_policy: str,
    area_crs: str,
    workers: list[int],
    chunk_sizes: list[int],
    parallel_backend: str,
    runs: int,
) -> list[BenchmarkRecord]:
    """Run H3 estimation for each requested worker/chunk setting."""
    if runs < 1:
        raise ValueError("runs must be greater than or equal to 1.")

    aoi = _read_aoi(path=aoi_path, layer=aoi_layer, fallback_crs=aoi_crs)
    records: list[BenchmarkRecord] = []
    for worker_count in workers:
        for chunk_size in chunk_sizes:
            for run_number in range(1, runs + 1):
                started_at = perf_counter()
                result = estimate_h3_census_indexes(
                    census_data_path=census_data_path,
                    year=year,
                    aoi=aoi,
                    h3_resolution=REQUIRED_H3_RESOLUTION,
                    indexes=indexes,
                    aoi_crs=aoi_crs,
                    area_crs=area_crs,
                    municipality_codes=municipality_codes,
                    special_section_policy=special_section_policy,
                    workers=worker_count,
                    chunk_size=chunk_size,
                    parallel_backend=parallel_backend,
                )
                seconds = perf_counter() - started_at
                records.append(
                    BenchmarkRecord(
                        workers=worker_count,
                        chunk_size=chunk_size,
                        parallel_backend=parallel_backend,
                        run=run_number,
                        seconds=seconds,
                        h3_cells=len(result),
                        validation_passed=_validation_passed(result),
                    )
                )
    _log_records(records)
    return records


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide aoi_crs to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _validation_passed(result: gpd.GeoDataFrame) -> bool:
    validation = result.attrs.get("total_validation")
    if validation is None or validation.empty:
        return False
    return bool(validation["within_tolerance"].all())


def _write_records_json(records: list[BenchmarkRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(record) for record in records], indent=2),
        encoding="utf-8",
    )


def _log_records(records: list[BenchmarkRecord]) -> None:
    logger.info("workers chunk_size backend run seconds h3_cells validation")
    for record in records:
        logger.info(
            "%s %s %s %s %.6f %s %s",
            record.workers,
            record.chunk_size,
            record.parallel_backend,
            record.run,
            record.seconds,
            record.h3_cells,
            "ok" if record.validation_passed else "failed",
        )


if __name__ == "__main__":
    setup_logging(log_dir=main_path)
    benchmark_records = run_benchmark(
        census_data_path=census_data_path,
        year=selected_year,
        aoi_path=aoi_path,
        indexes=selected_indexes,
        aoi_layer=aoi_layer,
        aoi_crs=aoi_crs,
        municipality_codes=municipalities_code,
        special_section_policy=DEFAULT_SPECIAL_SECTION_POLICY,
        area_crs=DEFAULT_AREA_CRS,
        workers=worker_counts,
        chunk_sizes=chunk_sizes,
        parallel_backend=parallel_backend,
        runs=runs,
    )
    _write_records_json(records=benchmark_records, output_path=benchmark_output_path)
