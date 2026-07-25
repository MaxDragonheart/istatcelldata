"""Run selected-year census preparation and fixed level-11 H3 analysis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypeVar

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
)
from istat_census_data.h3_workflow import (
    H3CensusWorkflowResult,
    run_h3_census_workflow,
)

RepeatedValue = TypeVar("RepeatedValue")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Download, preprocess, finalize, and estimate selected ISTAT census "
            "years on the fixed H3 level-11 grid."
        )
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        choices=SUPPORTED_CENSUS_YEARS,
        required=True,
        help="One or more census years to download, process, finalize, and estimate.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Root folder used for downloaded, preprocessed, finalized, and H3 output data.",
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
            "Omit this option to use all additive indexes available in each layer."
        ),
    )
    index_group.add_argument(
        "--all-additive",
        action="store_true",
        help="Explicitly estimate all additive indexes available in each census layer.",
    )
    parser.add_argument(
        "--region-code",
        action="append",
        nargs="+",
        type=int,
        help=(
            "Optional ISTAT region code filter for the download stage. Repeat the "
            "option or pass multiple values after it."
        ),
    )
    parser.add_argument(
        "--municipality-code",
        action="append",
        nargs="+",
        help=(
            "Optional municipality code filter for preprocessing and H3 estimation. "
            "Repeat the option or pass multiple values after it."
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
        help=(
            "Backend for workers greater than 1. Use dask only after installing "
            "the optional istat-census-data[dask] extra."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output GeoPackage path. Defaults to <data-dir>/h3_census_data.gpkg.",
    )
    parser.add_argument(
        "--output-layer-prefix",
        default="h3_census",
        help="Prefix for per-year H3 output layers. Defaults to h3_census.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip the download stage and reuse files already present under --data-dir.",
    )
    parser.add_argument(
        "--skip-preprocess",
        action="store_true",
        help="Skip preprocessing and reuse an existing preprocessed census.gpkg.",
    )
    parser.add_argument(
        "--skip-finalize",
        action="store_true",
        help="Skip finalization and reuse an existing census_data.gpkg.",
    )
    parser.add_argument(
        "--delete-download-folder",
        action="store_true",
        help="Delete downloaded preprocessing files after preprocessing completes.",
    )
    parser.add_argument(
        "--delete-preprocessed-data",
        action="store_true",
        help="Delete the preprocessed census.gpkg after finalization completes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the end-to-end H3 census analysis command-line workflow."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        aoi = _read_aoi(path=args.aoi, layer=args.aoi_layer, fallback_crs=args.aoi_crs)
        result = run_h3_census_workflow(
            years=args.years,
            data_folder=args.data_dir,
            aoi=aoi,
            indexes="all_additive" if args.all_additive or args.indexes is None else args.indexes,
            output_path=args.output,
            output_layer_prefix=args.output_layer_prefix,
            region_list=_flatten_repeated_values(args.region_code),
            municipality_codes=_flatten_repeated_values(args.municipality_code),
            special_section_policy=args.special_section_policy,
            area_crs=args.area_crs,
            aoi_crs=args.aoi_crs,
            clip_output=args.clip_output,
            workers=args.workers,
            chunk_size=args.chunk_size,
            parallel_backend=args.parallel_backend,
            run_download=not args.skip_download,
            run_preprocess=not args.skip_preprocess,
            run_finalize=not args.skip_finalize,
            delete_download_folder=args.delete_download_folder,
            delete_preprocessed_data=args.delete_preprocessed_data,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(result=result)
    return 0


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide --aoi-crs to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _flatten_repeated_values(
    values: list[list[RepeatedValue]] | None,
) -> list[RepeatedValue] | None:
    if values is None:
        return None
    return [value for group in values for value in group]


def _print_summary(result: H3CensusWorkflowResult) -> None:
    years = ", ".join(str(year) for year in result.years)
    print("H3 census workflow completed.")
    print(f"Years: {years}")
    print(f"Finalized census data: {result.census_data_path}")
    print(f"H3 output: {result.output_path}")
    for year in result.years:
        frame = result.results[year]
        output_layer = result.layers[year]
        print(
            f"- {year}: wrote {len(frame)} H3 level-{REQUIRED_H3_RESOLUTION} "
            f"cells to layer {output_layer}."
        )
        validation = frame.attrs.get("total_validation")
        if validation is not None and not validation.empty:
            failed = validation[~validation["within_tolerance"]]
            if failed.empty:
                print(f"  {year} validation: all estimated indexes are within tolerance.")
            else:
                failed_indexes = ", ".join(failed["index"].astype(str).tolist())
                print(f"  {year} validation: outside tolerance for {failed_indexes}.")


if __name__ == "__main__":
    raise SystemExit(main())
