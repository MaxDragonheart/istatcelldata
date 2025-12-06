import logging
from pathlib import Path

from istatcelldata.census2011.download import download_administrative_boundaries, download_geodata
from istatcelldata.census2011.download import download_data as dwn
from istatcelldata.census2021.utils import read_xlsx
from istatcelldata.config import CENSUS_DATA_FOLDER, DATA_FOLDER, PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import remove_files

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_data(output_data_folder: Path, census_year: int) -> Path:
    """Download, organize, and convert census data to processable format.

    This function manages the complete workflow of downloading and preparing
    census data for a specific year. It identifies XLSX files present,
    performs conversion to CSV, and removes the original files that are no
    longer needed.

    Args:
        output_data_folder: Path to the main folder where downloaded and
            processed data will be saved.
        census_year: Reference year for the census data to download.

    Returns:
        Path to the folder containing the downloaded and processed data.

    Raises:
        Exception: If no XLSX file is found in the downloaded data folder.

    Note:
        XLSX files are converted to CSV to facilitate subsequent ETL and
        analysis phases.
        Original XLSX files are deleted to reduce disk space usage.
        The final data structure depends on the global constants
        `DATA_FOLDER` and `CENSUS_DATA_FOLDER`.
    """
    data_folder = dwn(output_data_folder=output_data_folder, census_year=census_year)

    final_folder = data_folder.joinpath(DATA_FOLDER, CENSUS_DATA_FOLDER)
    Path(final_folder).mkdir(parents=True, exist_ok=True)

    # Perform data tracing from first XLS file found
    files_list = list(data_folder.rglob("*.xlsx"))

    if not files_list:
        logging.error("No XLSX files found in data folder.")
        raise Exception("No XLSX files found for tracing.")

    logging.info("Extracting census data in xlsx format and converting to csv.")
    # Convert xls to csv
    for file_path in files_list:
        read_xlsx(file_path=file_path, output_path=final_folder)

    # Remove unnecessary XLS files
    logging.info(f"Removing XLS files from folder {data_folder}")
    remove_files(files_path=files_list)

    logging.info(f"Census data download completed and saved to {data_folder}")
    return data_folder


def download_all_census_data_2021(output_data_folder: Path, region_list: list = []) -> Path:
    """Download complete census and geographic dataset for the 2021 Census.

    This function performs all necessary operations to obtain 2021 census data,
    automatically coordinating:

    1. Download of tabular census data.
    2. Download of geodata for requested regions (or all, if `region_list` is empty).
    3. Download of official administrative boundaries.

    The function automatically creates the necessary folder structure to organize
    the data, defined by the `PREPROCESSING_FOLDER` constant.

    Args:
        output_data_folder: Main path where 2021 Census data will be saved.
        region_list: Region codes or names for which to download geodata.
            If the list is empty, geodata for all regions is downloaded.

    Returns:
        Path to the root folder containing the complete downloaded data structure
        for the 2021 Census.

    Note:
        The `census_year` parameter is fixed at 2021.
        It uses support functions: `download_data()`, `download_geodata()`,
        and `download_administrative_boundaries()`.
    """  # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2021)

    # Download geodata
    download_geodata(output_data_folder=data_folder, region_list=region_list, census_year=2021)

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2021)

    return output_data_folder
