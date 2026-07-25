"""Estimate finalized ISTAT census data on the fixed level-11 H3 grid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd

from istat_census_data.catalog import SUPPORTED_CENSUS_YEARS
from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_H3_CHUNK_SIZE,
    DEFAULT_H3_WORKERS,
    DEFAULT_PARALLEL_BACKEND,
    DEFAULT_SPECIAL_SECTION_POLICY,
    PARALLEL_BACKENDS,
    REQUIRED_H3_RESOLUTION,
    SPECIAL_SECTION_POLICIES,
    estimate_h3_census_indexes,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=("Estimate finalized ISTAT census indicators on the fixed H3 level-11 grid.")
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
    index_group = parser.add_mutually_exclusive_group()
    index_group.add_argument(
        "--indexes",
        nargs="+",
        help=(
            "Source index codes or canonical catalogue IDs to estimate. "
            "Omit this option to use all additive indexes available in the layer."
        ),
    )
    index_group.add_argument(
        "--all-additive",
        action="store_true",
        help="Explicitly estimate all additive indexes available in the census layer.",
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
        "--clip-output",
        action="store_true",
        help="Clip output geometries to the AOI instead of writing full H3 hexagons.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_H3_WORKERS,
        help="Number of H3 chunk workers. Defaults to 1 for serial execution.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_H3_CHUNK_SIZE,
        help="Maximum number of H3 cells per parallel chunk.",
    )
    parser.add_argument(
        "--parallel-backend",
        choices=PARALLEL_BACKENDS,
        default=DEFAULT_PARALLEL_BACKEND,
        help="Executor backend for workers greater than 1.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output GeoPackage path.",
    )
    parser.add_argument(
        "--output-layer",
        help="Optional output layer name. Defaults to h3_census<year>_r11.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the H3 census estimation command-line workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        aoi = _read_aoi(path=args.aoi, layer=args.aoi_layer, fallback_crs=args.aoi_crs)
        result = estimate_h3_census_indexes(
            census_data_path=args.census_data,
            year=args.year,
            aoi=aoi,
            indexes=args.indexes or "all_additive",
            area_crs=args.area_crs,
            municipality_codes=_flatten_repeated_values(args.municipality_code),
            special_section_policy=args.special_section_policy,
            clip_output=args.clip_output,
            workers=args.workers,
            chunk_size=args.chunk_size,
            parallel_backend=args.parallel_backend,
            output_path=args.output,
            output_layer=args.output_layer,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(
        result=result,
        output_path=args.output,
        output_layer=args.output_layer or f"h3_census{args.year}_r{REQUIRED_H3_RESOLUTION}",
    )
    return 0


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


def _print_summary(result: gpd.GeoDataFrame, output_path: Path, output_layer: str) -> None:
    print(f"Wrote {len(result)} H3 level-11 cells to {output_path} layer {output_layer}.")
    validation = result.attrs.get("total_validation")
    if validation is not None and not validation.empty:
        failed = validation[~validation["within_tolerance"]]
        if failed.empty:
            print("Total validation: all estimated indexes are within tolerance.")
        else:
            failed_indexes = ", ".join(failed["index"].astype(str).tolist())
            print(f"Total validation: outside tolerance for {failed_indexes}.")


if __name__ == "__main__":
    raise SystemExit(main())
