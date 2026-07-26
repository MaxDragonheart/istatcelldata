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
)
from istat_census_data.h3_workflow import H3CensusWorkflowResult, run_h3_census_workflow
from istat_census_data.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census_test")
aoi_path = main_path / "aoi.gpkg"
h3_output_path = main_path / "h3_census_analysis.gpkg"
list_year = [2021]
list_region: list[int] = []
selected_indexes: list[str] = []
municipalities_code: list[str] | None = None
aoi_layer: str | None = None
aoi_crs: str | None = None
output_layer_prefix = "h3_census"
clip_output = False
workers = DEFAULT_H3_WORKERS
chunk_size = DEFAULT_H3_CHUNK_SIZE
parallel_backend = DEFAULT_PARALLEL_BACKEND
run_download = True
run_preprocess = True
run_finalize = True
delete_download_folder = False
delete_preprocessed_data = False


# Configure logging at the start of the script.
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="run_h3_census_analysis",
    )


# Define the logger as a global variable.
logger = logging.getLogger(__name__)


def run(
    years: list[int],
    regions: list[int],
    data_dir: Path,
    aoi_path: Path,
    indexes: list[str],
    output_path: Path,
    output_layer_prefix: str,
    aoi_layer: str | None,
    aoi_crs: str | None,
    municipality_codes: list[str] | None,
    special_section_policy: str,
    area_crs: str,
    clip_output: bool,
    workers: int,
    chunk_size: int,
    parallel_backend: str,
    run_download: bool,
    run_preprocess: bool,
    run_finalize: bool,
    delete_download_folder: bool,
    delete_preprocessed_data: bool,
) -> H3CensusWorkflowResult:
    """Run the selected-year H3 workflow from script-level settings."""
    aoi = _read_aoi(path=aoi_path, layer=aoi_layer, fallback_crs=aoi_crs)
    result = run_h3_census_workflow(
        years=years,
        data_folder=data_dir,
        aoi=aoi,
        indexes=indexes,
        output_path=output_path,
        output_layer_prefix=output_layer_prefix,
        region_list=regions,
        municipality_codes=municipality_codes,
        special_section_policy=special_section_policy,
        area_crs=area_crs,
        aoi_crs=aoi_crs,
        clip_output=clip_output,
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
        run_download=run_download,
        run_preprocess=run_preprocess,
        run_finalize=run_finalize,
        delete_download_folder=delete_download_folder,
        delete_preprocessed_data=delete_preprocessed_data,
    )
    _log_summary(result=result)
    return result


def _read_aoi(path: Path, layer: str | None, fallback_crs: str | None) -> gpd.GeoDataFrame:
    aoi = gpd.read_file(filename=str(path), layer=layer)
    if aoi.crs is None:
        if fallback_crs is None:
            raise ValueError("AOI file has no CRS. Provide aoi_crs to assign one.")
        aoi = aoi.set_crs(fallback_crs)
    return aoi


def _log_summary(result: H3CensusWorkflowResult) -> None:
    years = ", ".join(str(year) for year in result.years)
    logger.info("H3 census workflow completed.")
    logger.info("Years: %s", years)
    logger.info("Finalized census data: %s", result.census_data_path)
    logger.info("H3 output: %s", result.output_path)
    for year in result.years:
        frame = result.results[year]
        output_layer = result.layers[year]
        logger.info(
            "%s: wrote %s H3 level-%s cells to layer %s.",
            year,
            len(frame),
            REQUIRED_H3_RESOLUTION,
            output_layer,
        )


if __name__ == "__main__":
    setup_logging(log_dir=main_path)
    run(
        years=list_year,
        regions=list_region,
        data_dir=main_path,
        aoi_path=aoi_path,
        indexes=selected_indexes,
        output_path=h3_output_path,
        output_layer_prefix=output_layer_prefix,
        aoi_layer=aoi_layer,
        aoi_crs=aoi_crs,
        municipality_codes=municipalities_code,
        special_section_policy=DEFAULT_SPECIAL_SECTION_POLICY,
        area_crs=DEFAULT_AREA_CRS,
        clip_output=clip_output,
        workers=workers,
        chunk_size=chunk_size,
        parallel_backend=parallel_backend,
        run_download=run_download,
        run_preprocess=run_preprocess,
        run_finalize=run_finalize,
        delete_download_folder=delete_download_folder,
        delete_preprocessed_data=delete_preprocessed_data,
    )
