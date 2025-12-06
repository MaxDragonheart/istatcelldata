import logging
from pathlib import Path

from istatcelldata.census1991.download import download_data
from istatcelldata.census2011.download import download_administrative_boundaries, download_geodata
from istatcelldata.config import PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_all_census_data_2001(output_data_folder: Path, region_list: list = []) -> Path:
    """Download complete census and geographic dataset for the 2001 Census.

    This function coordinates all necessary operations to obtain census data
    and geographic information associated with the 2001 Census. Specifically,
    it handles:

    - Downloading tabular census data
    - Downloading geodata (for all regions or a specified subset)
    - Downloading official administrative boundaries

    If `region_list` is empty, geodata for all available regions is downloaded.

    Args:
        output_data_folder: Main path where all downloaded and processed data
            will be saved.
        region_list: List of region codes or names for which to download geodata.
            If left empty, the function considers all regions.

    Returns:
        Path to the root folder `output_data_folder` containing the 2001 Census
        data structure.

    Note:
        This function is specific to the 2001 Census (the `census_year` parameter
        is fixed internally to 2001).
        It uses support functions: `download_data()`, `download_geodata()`, and
        `download_administrative_boundaries()`.
        A preprocessing subfolder is created automatically, defined by the
        `PREPROCESSING_FOLDER` constant.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2001)

    # Download geodata
    download_geodata(output_data_folder=data_folder, region_list=region_list, census_year=2001)

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2001)

    return output_data_folder
