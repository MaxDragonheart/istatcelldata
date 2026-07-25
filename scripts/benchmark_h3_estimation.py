"""Benchmark finalized ISTAT census H3 estimation worker settings."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import geopandas as gpd

from istat_census_data.catalog import SUPPORTED_CENSUS_YEARS
from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_H3_CHUNK_SIZE,
    DEFAULT_PARALLEL_BACKEND,
    DEFAULT_SPECIAL_SECTION_POLICY,
    PARALLEL_BACKENDS,
    REQUIRED_H3_RESOLUTION,
    SPECIAL_SECTION_POLICIES,
    estimate_h3_census_indexes,
)


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


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark finalized ISTAT census H3 estimation with different worker "
            "and chunk settings. This script does not download census data."
        )
    )
    parser.add_argument(
        "--census-data",
        type=Path,
        required=True,
        help="Path to the finalized census_data.gpkg file.",
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        choices=SUPPORTED_CENSUS_YEARS,
        help="Census year to read from layer census<year>.",
    )
    parser.add_argument(
        "--aoi",
        type=Path,
        required=True,
        help="Path to an AOI vector file readable by GeoPandas.",
    )
    parser.add_argument(
        "--aoi-layer",
        help="Optional AOI layer name when reading a multi-layer file.",
    )
    parser.add_argument(
        "--aoi-crs",
        help="CRS to assign when the AOI file has no CRS, for example EPSG:4326.",
    )
    parser.add_argument(
        "--indexes",
        nargs="+",
        help=(
            "Source index codes or canonical catalogue IDs to estimate. "
            "Omit this option to use all additive indexes available in the layer."
        ),
    )
    parser.add_argument(
        "--municipality-code",
        action="append",
        nargs="+",
        help=(
            "Optional municipality code filter. Repeat the option or pass multiple "
            "values after it."
        ),
    )
    parser.add_argument(
        "--special-section-policy",
        choices=SPECIAL_SECTION_POLICIES,
        default=DEFAULT_SPECIAL_SECTION_POLICY,
        help=(
            "How to handle special or fictitious census sections. Defaults to "
            f"{DEFAULT_SPECIAL_SECTION_POLICY!r}."
        ),
    )
    parser.add_argument(
        "--area-crs",
        default=DEFAULT_AREA_CRS,
        help="Projected CRS used for area calculations. Defaults to EPSG:3035.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        nargs="+",
        default=[1, 2, 4],
        help="Worker counts to benchmark. Defaults to 1 2 4.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        nargs="+",
        default=[DEFAULT_H3_CHUNK_SIZE],
        help="H3 cell chunk sizes to benchmark.",
    )
    parser.add_argument(
        "--parallel-backend",
        choices=PARALLEL_BACKENDS,
        default=DEFAULT_PARALLEL_BACKEND,
        help="Executor backend for workers greater than 1.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of repeated measurements per worker/chunk setting.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path where benchmark records are written as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run H3 estimation benchmarks."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        records = run_benchmark(
            census_data_path=args.census_data,
            year=args.year,
            aoi_path=args.aoi,
            aoi_layer=args.aoi_layer,
            aoi_crs=args.aoi_crs,
            indexes=args.indexes or "all_additive",
            municipality_codes=_flatten_repeated_values(args.municipality_code),
            special_section_policy=args.special_section_policy,
            area_crs=args.area_crs,
            workers=args.workers,
            chunk_sizes=args.chunk_size,
            parallel_backend=args.parallel_backend,
            runs=args.runs,
        )
        if args.output_json is not None:
            args.output_json.parent.mkdir(parents=True, exist_ok=True)
            args.output_json.write_text(
                json.dumps([asdict(record) for record in records], indent=2),
                encoding="utf-8",
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_records(records)
    return 0


def run_benchmark(
    census_data_path: Path,
    year: int,
    aoi_path: Path,
    aoi_layer: str | None,
    aoi_crs: str | None,
    indexes: str | list[str],
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
    return records


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide --aoi-crs to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _flatten_repeated_values(values: list[list[str]] | None) -> list[str] | None:
    if values is None:
        return None
    return [value for group in values for value in group]


def _validation_passed(result: gpd.GeoDataFrame) -> bool:
    validation = result.attrs.get("total_validation")
    if validation is None or validation.empty:
        return False
    return bool(validation["within_tolerance"].all())


def _print_records(records: list[BenchmarkRecord]) -> None:
    print("workers chunk_size backend run seconds h3_cells validation")
    for record in records:
        print(
            f"{record.workers} {record.chunk_size} {record.parallel_backend} "
            f"{record.run} {record.seconds:.6f} {record.h3_cells} "
            f"{'ok' if record.validation_passed else 'failed'}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
