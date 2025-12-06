import datetime
import logging
from pathlib import Path

from istatcelldata.census1991.download import download_all_census_data_1991
from istatcelldata.census2001.download import download_all_census_data_2001
from istatcelldata.census2011.download import download_all_census_data_2011
from istatcelldata.census2021.download import download_all_census_data_2021
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_census(years: list[int], output_data_folder: Path, region_list: list = []):
    """Download census data for one or more requested years including geodata and boundaries.

    This function provides centralized download of census data for years 1991, 2001,
    2011, and 2021. For each year, it automatically executes the following procedures:

    - Download of tabular census data
    - Download of geodata (for all regions or specified ones)
    - Download of administrative boundaries

    If `years` is empty, data for all available years is downloaded automatically.

    Args:
        years: List of census years to download. If the list is empty, data for
            all census years (1991, 2001, 2011, 2021) will be downloaded.
        output_data_folder: Path to the folder where all downloaded data will
            be saved.
        region_list: Optional list of region codes or names for which to download
            geodata. If empty, geodata for all available regions is downloaded.

    Raises:
        ValueError: If one of the specified years is not supported or does not
            exist in the mapping.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Starting analysis at {time_start}")

    # Map census years to their respective download functions
    function_map = {
        1991: lambda: download_all_census_data_1991(
            output_data_folder=output_data_folder, region_list=region_list
        ),
        2001: lambda: download_all_census_data_2001(
            output_data_folder=output_data_folder, region_list=region_list
        ),
        2011: lambda: download_all_census_data_2011(
            output_data_folder=output_data_folder, region_list=region_list
        ),
        2021: lambda: download_all_census_data_2021(
            output_data_folder=output_data_folder, region_list=region_list
        ),
    }

    # If the year list is empty, download data for all available years
    if not years:
        logging.info("No year specified, downloading all available data (1991, 2001, 2011, 2021).")
        years = [1991, 2001, 2011, 2021]

    # Download data for each specified year
    for year in years:
        if year in function_map:
            logging.info(f"Downloading data for {year} census")
            function_map[year]()  # Call the corresponding function for the year
        else:
            logging.error(f"Year {year} not supported. Operation canceled.")
            raise ValueError(f"Year {year} is not supported.")

    # Calculate total execution time
    time_end = datetime.datetime.now() - time_start
    logging.info(f"Analysis completed in {time_end}")
