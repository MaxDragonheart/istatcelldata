import logging
from pathlib import Path

import geopandas as gpd

from istat_census_data.h3_estimation import (
    DEFAULT_AREA_CRS,
    DEFAULT_H3_CHUNK_SIZE,
    DEFAULT_H3_WORKERS,
    DEFAULT_PARALLEL_BACKEND,
    DEFAULT_SPECIAL_SECTION_POLICY,
    REQUIRED_H3_RESOLUTION,
    estimate_h3_census_indexes,
)
from istat_census_data.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census_test")
census_data_path = main_path / "census_data.gpkg"
aoi_path = main_path / "aoi.gpkg"
h3_output_path = main_path / "h3_census_2021.gpkg"
selected_year = 2021
selected_indexes: list[str] = []
municipalities_code: list[str] | None = None
aoi_layer: str | None = None
aoi_crs: str | None = None
output_layer: str | None = None
clip_output = False
workers = DEFAULT_H3_WORKERS
chunk_size = DEFAULT_H3_CHUNK_SIZE
parallel_backend = DEFAULT_PARALLEL_BACKEND


# Configure logging at the start of the script.
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="estimate_h3_census",
    )


# Define the logger as a global variable.
logger = logging.getLogger(__name__)


def run(
    census_data_path: Path,
    year: int,
    aoi_path: Path,
    output_path: Path,
    indexes: list[str],
    aoi_layer: str | None,
    aoi_crs: str | None,
    municipality_codes: list[str] | None,
    special_section_policy: str,
    area_crs: str,
    clip_output: bool,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
    output_layer: str | None,
) -> gpd.GeoDataFrame:
    """Run H3 estimation from finalized census data and an AOI file."""
    aoi = _read_aoi(path=aoi_path, layer=aoi_layer, fallback_crs=aoi_crs)
    result = estimate_h3_census_indexes(
        census_data_path=census_data_path,
        year=year,
        aoi=aoi,
        indexes=indexes,
        area_crs=area_crs,
        municipality_codes=municipality_codes,
        special_section_policy=special_section_policy,
        clip_output=clip_output,
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
        output_path=output_path,
        output_layer=output_layer,
    )
    _log_summary(
        result=result,
        output_path=output_path,
        output_layer=output_layer or f"h3_census{year}_r{REQUIRED_H3_RESOLUTION}",
    )
    return result


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide aoi_crs to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _log_summary(result: gpd.GeoDataFrame, output_path: Path, output_layer: str) -> None:
    logger.info(
        "Wrote %s H3 level-%s cells to %s layer %s.",
        len(result),
        REQUIRED_H3_RESOLUTION,
        output_path,
        output_layer,
    )
    validation = result.attrs.get("total_validation")
    if validation is not None and not validation.empty:
        failed = validation[~validation["within_tolerance"]]
        if failed.empty:
            logger.info("Total validation: all estimated indexes are within tolerance.")
        else:
            failed_indexes = ", ".join(failed["index"].astype(str).tolist())
            logger.warning("Total validation: outside tolerance for %s.", failed_indexes)


if __name__ == "__main__":
    setup_logging(log_dir=main_path)
    run(
        census_data_path=census_data_path,
        year=selected_year,
        aoi_path=aoi_path,
        output_path=h3_output_path,
        indexes=selected_indexes,
        aoi_layer=aoi_layer,
        aoi_crs=aoi_crs,
        municipality_codes=municipalities_code,
        special_section_policy=DEFAULT_SPECIAL_SECTION_POLICY,
        area_crs=DEFAULT_AREA_CRS,
        clip_output=clip_output,
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
        output_layer=output_layer,
    )
