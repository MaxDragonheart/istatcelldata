"""Reproduce BUG-006 H3 grid generation outside the full census workflow."""

from __future__ import annotations

import faulthandler
import importlib.metadata
import logging
import os
import platform
import resource
from pathlib import Path
from time import perf_counter

import geopandas as gpd

from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_BOUNDARY_RING_SIZE,
    REQUIRED_H3_RESOLUTION,
    WGS84_CRS,
    generate_h3_grid,
)

AOI_PATH = Path("/home/max/Desktop/census/aoi.gpkg")
AOI_LAYER: str | None = None
AOI_CRS: str | None = None
OUTPUT_CRS = WGS84_CRS

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the BUG-006 grid-only reproduction."""
    faulthandler.enable(all_threads=True)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    logger.info("Starting BUG-006 H3 grid-generation-only reproduction.")
    _log_environment()

    aoi = _read_aoi(path=AOI_PATH, layer=AOI_LAYER, fallback_crs=AOI_CRS)
    logger.info(
        "Loaded AOI: path=%s, layer=%s, rows=%s, crs=%s, bounds=%s.",
        AOI_PATH,
        AOI_LAYER,
        len(aoi),
        aoi.crs,
        list(aoi.total_bounds),
    )

    started_at = perf_counter()
    grid = generate_h3_grid(
        aoi=aoi,
        h3_resolution=REQUIRED_H3_RESOLUTION,
        area_crs=DEFAULT_AREA_CRS,
        boundary_ring_size=DEFAULT_BOUNDARY_RING_SIZE,
        output_crs=OUTPUT_CRS,
    )
    elapsed_seconds = perf_counter() - started_at

    logger.info(
        "Completed BUG-006 reproduction without crash: cells=%s, elapsed_seconds=%.2f, "
        "peak_rss_mb=%.1f.",
        len(grid),
        elapsed_seconds,
        _peak_rss_mb(),
    )


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    if not path.exists():
        raise FileNotFoundError(f"AOI file was not found: {path}")

    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide AOI_CRS to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _log_environment() -> None:
    logger.info("Process: pid=%s, python=%s.", os.getpid(), platform.python_version())
    logger.info(
        "Dependency versions: geopandas=%s, shapely=%s, h3=%s, pandas=%s, numpy=%s.",
        _package_version("geopandas"),
        _package_version("shapely"),
        _package_version("h3"),
        _package_version("pandas"),
        _package_version("numpy"),
    )


def _package_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _peak_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


if __name__ == "__main__":
    main()
