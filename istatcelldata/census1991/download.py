import logging
from pathlib import Path

from istatcelldata.census1991.utils import census_trace, read_xls
from istatcelldata.census2011.download import download_administrative_boundaries, download_geodata
from istatcelldata.census2011.download import download_data as dwn
from istatcelldata.config import CENSUS_DATA_FOLDER, DATA_FOLDER, PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import get_census_dictionary, remove_files

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_data(output_data_folder: Path, census_year: int) -> Path:
    """Download, organize, and process census data for a specific year.

    This function manages the complete workflow for acquiring census data from
    source through to producing final CSV files. The following operations are
    performed:

    1. Retrieval of the dictionary of links for the census year.
    2. Download of raw data via the `dwn()` function.
    3. Creation of the output folder structure.
    4. Identification and reading of `.xls` files.
    5. Conversion of Excel files to CSV.
    6. Extraction of tracking metadata (codifications) from the first available file.
    7. Removal of original Excel files.

    Args:
        output_data_folder: Root folder path where downloaded data will be saved.
        census_year: Reference year for the census data to process.

    Returns:
        Path to the folder containing the downloaded and processed census data.

    Raises:
        Exception: If no `.xls` file is found in the data folder.

    Note:
        Conversion from XLS to CSV is performed via the `read_xls()` function.
        Dataset tracking is performed only on the first XLS file found.
        XLS files are removed at the end of the process to reduce disk space usage.
    """
    link_dict = get_census_dictionary(census_year=census_year)
    census_code = link_dict[f"census{census_year}"]["census_code"]

    data_folder = dwn(output_data_folder=output_data_folder, census_year=census_year)

    final_folder = data_folder.joinpath(DATA_FOLDER, CENSUS_DATA_FOLDER)
    Path(final_folder).mkdir(parents=True, exist_ok=True)

    # Esegui il tracciamento dei dati dal primo file XLS trovato
    files_list = list(data_folder.rglob("*.xls"))
    if not files_list:
        logging.error("Nessun file XLS trovato nella cartella dei dati.")
        raise Exception("Nessun file XLS trovato per il tracciamento.")

    logging.info("Estrazione dei dati censuari in formato xls e conversione in csv.")
    # Convert xls to csv
    for file_path in files_list:
        read_xls(file_path=file_path, census_code=census_code, output_path=final_folder)

    first_element = files_list[0]
    logging.info(f"Extracting data trace from file {first_element}")
    census_trace(file_path=first_element, year=census_year, output_path=final_folder)

    # Remove unnecessary XLS files
    logging.info(f"Removing XLS files from folder {data_folder}")
    remove_files(files_path=files_list)

    logging.info(f"Census data download completed and saved in {data_folder}")
    return data_folder


def download_all_census_data_1991(output_data_folder: Path, region_list: list = []) -> Path:
    """Download complete census and geographic dataset for the 1991 Census.

    This function coordinates all necessary operations to obtain census data
    and geographic information associated with the 1991 Census. It enables
    downloading of:

    - Tabular census data
    - Geodata specific to one or more regions
    - Official administrative boundaries

    If no value is provided for `region_list`, geodata for all regions is
    downloaded.

    Args:
        output_data_folder: Main path where all downloaded and processed data
            will be saved.
        region_list: List containing region codes or names for which to download
            geodata. If empty, all available regions are considered.

    Returns:
        Path to the root folder containing the downloaded data.

    Note:
        This function operates exclusively on the 1991 Census.
        It uses support functions such as `download_data()`,
        `download_geodata()`, and `download_administrative_boundaries()`.
        The necessary folder structure is created automatically.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=1991)

    # Download geodata
    download_geodata(output_data_folder=data_folder, region_list=region_list, census_year=1991)

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=1991)

    return output_data_folder
