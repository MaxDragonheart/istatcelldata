"""Finalize retained H3 result chunks into a GeoPackage."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from istat_census_data.h3_estimation import finalize_h3_result_chunks_to_geopackage
from istat_census_data.logger_config import configure_logging

DEFAULT_CENSUS_ROOT = Path("/home/max/Desktop/census")
DEFAULT_INTERMEDIATE_WORKSPACE = (
    DEFAULT_CENSUS_ROOT
    / "h3_intermediates"
    / "66dd6c4db99f37c02fa7ae4893c05245964bb7849c8ae2fb550a0fc7bd74ce1e"
)
DEFAULT_OUTPUT_PATH = DEFAULT_CENSUS_ROOT / "h3_census_analysis.gpkg"

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line options for retained H3 chunk finalization."""
    parser = argparse.ArgumentParser(
        description="Finalize retained H3 result_chunks into a GeoPackage layer."
    )
    parser.add_argument(
        "--intermediate-workspace",
        type=Path,
        default=DEFAULT_INTERMEDIATE_WORKSPACE,
        help="Retained H3 workspace containing metadata.json and result_chunks/.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="GeoPackage output path.",
    )
    parser.add_argument(
        "--output-layer",
        default=None,
        help="GeoPackage layer name. Defaults to h3_census<year>_r<h3_resolution>.",
    )
    parser.add_argument(
        "--index-batch-size",
        type=int,
        default=8,
        help="Number of additive indexes inspected together during integerization planning.",
    )
    parser.add_argument(
        "--conservation-tolerance",
        type=float,
        default=1e-6,
        help="Relative tolerance used for continuous total validation.",
    )
    return parser.parse_args()


def main() -> None:
    """Run retained H3 chunk finalization from command-line arguments."""
    args = parse_args()
    configure_logging(log_dir=args.output_path.parent, log_name="finalize_h3_result_chunks")
    result = finalize_h3_result_chunks_to_geopackage(
        intermediate_workspace=args.intermediate_workspace,
        output_path=args.output_path,
        output_layer=args.output_layer,
        conservation_tolerance=args.conservation_tolerance,
        index_batch_size=args.index_batch_size,
    )
    failed_continuous = result.total_validation[
        ~result.total_validation["within_tolerance"].astype(bool)
    ]
    failed_integer = result.integer_total_validation[
        ~result.integer_total_validation["within_tolerance"].astype(bool)
    ]
    logger.info("Finalized H3 chunks to %s layer %s.", result.output_path, result.output_layer)
    logger.info("Rows: %s; chunks: %s.", result.row_count, result.chunk_count)
    logger.info("Continuous validation failures: %s.", len(failed_continuous))
    logger.info("Integer validation failures: %s.", len(failed_integer))
    if not failed_integer.empty:
        raise RuntimeError("Integer total validation failed after retained chunk finalization.")


if __name__ == "__main__":
    main()
