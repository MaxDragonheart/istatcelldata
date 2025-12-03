import logging
from pathlib import Path

from istatcelldata.config import (
    BOUNDARIES_DATA_FOLDER,
    DATA_FOLDER,
    GEODATA_FOLDER,
    PREPROCESSING_FOLDER,
)
from istatcelldata.download import download_base
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import census_folder, get_census_dictionary

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_data(output_data_folder: Path, census_year: int) -> Path:
    """Download census data for a specific year and organize the working folder.

    This function retrieves from the census dictionary the link to data for the
    specified year, prepares the destination folder structure, and delegates
    the actual download to the `download_base()` function. Upon completion,
    it returns the path to the downloaded file (or folder, depending on how
    `download_base()` is implemented).

    Args:
        output_data_folder: Path to the output folder where the census data
            structure will be created (e.g., preprocessing folder or project).
        census_year: Reference year for the census data to download
            (e.g., 1991, 2001, 2011).

    Returns:
        Path returned by `download_base()`, representing the location of the
        downloaded census data (file or folder).

    Raises:
        Exception: If an error occurs during link retrieval, folder creation,
            or data download.
    """
    link_dict = get_census_dictionary(census_year=census_year)
    data_url = link_dict[f"census{census_year}"]["data_url"]

    try:
        # Creazione della cartella di destinazione per i dati
        logging.info(f"Creating destination data folder at {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)
        Path(destination_folder).mkdir(parents=True, exist_ok=True)

        data_folder = destination_folder.joinpath(DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = Path(data_url).stem + Path(data_url).suffix
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Downloading data from {data_url}")
        download_data_path = download_base(
            data_link=data_url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder,
        )

        logging.info(f"Census data download completed and saved in {destination_folder}")
        return download_data_path

    except Exception as e:
        logging.error(f"Error downloading data: {str(e)}")
        raise e


def download_geodata(
    output_data_folder: Path, census_year: int, region_list: list[int] = []
) -> Path:
    """Download census geodata for one or more regions for a census year.

    This function retrieves URLs for census geodata packages (ZIP) via
    `get_census_dictionary()`, creates the destination folder structure for the
    census year, and proceeds to download the ZIP files for the requested regions.
    If `region_list` is empty, data for all available regions in the dictionary
    is downloaded (typically 20).

    Args:
        output_data_folder: Root folder where the entire census data structure
            will be saved.
        census_year: Reference year for the census (e.g., 1991, 2001, 2011).
        region_list: List of ISTAT region codes for which to download geodata.
            If empty, geodata for all predefined regions is downloaded.

    Returns:
        Path to the folder containing the downloaded census geodata ZIP files.

    Note:
        The function does not extract the ZIP files: it only downloads them.
        Geodata URLs are obtained from the census dictionary via the
        `geodata_urls` key.
        The final data path is organized via the global `GEODATA_FOLDER` constant.
    """
    link_dict = get_census_dictionary(census_year=census_year, region_list=region_list)
    geodata_urls = link_dict[f"census{census_year}"]["geodata_urls"]

    # Creazione della cartella di destinazione per i dati
    destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    data_folder = destination_folder.joinpath(GEODATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    for url in geodata_urls:
        data_file_name = url.split("/")[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)
        logging.info(f"Destination file path: {data_file_path_dest}")

        # Scarica i dati
        download_base(
            data_link=url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder,
        )

    return data_folder


def download_administrative_boundaries(output_data_folder: Path, census_year: int) -> Path:
    """Download administrative boundaries for a census year and save to data structure.

    This function retrieves from the census dictionary the URL for administrative
    boundaries (regions, provinces, municipalities), prepares the folder structure
    dedicated to the census year, and downloads the associated ZIP file. The
    content is not extracted: the function only performs the download.

    Args:
        output_data_folder: Main path where the census data structure will be created.
        census_year: Reference census year (e.g., 1991, 2001, 2011).

    Returns:
        Path to the folder containing the downloaded administrative boundaries.

    Raises:
        Exception: If an error occurs during folder creation or download.

    Note:
        Administrative boundaries include municipalities, provinces, and regions.
        The file is saved to the folder defined by the `BOUNDARIES_DATA_FOLDER`
        constant.
        The returned path is the census year folder, not the individual downloaded file.
    """
    link_dict = get_census_dictionary(census_year=census_year)
    data_url = link_dict[f"census{census_year}"]["admin_boundaries_url"]

    try:
        # Creazione della cartella per i dati del censimento annuale
        logging.info(f"Creating census data folder at {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)

        # Creazione della cartella per i confini amministrativi
        data_folder = destination_folder.joinpath(BOUNDARIES_DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = data_url.split("/")[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Downloading administrative boundaries from {data_url}")
        download_base(
            data_link=data_url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder,
        )

        logging.info(
            f"Administrative boundaries download completed and saved in {destination_folder}"
        )
        return destination_folder

    except Exception as e:
        logging.error(f"Error downloading administrative boundaries: {str(e)}")
        raise e


def download_all_census_data_2011(output_data_folder: Path, region_list: list = []) -> Path:
    """Download complete census and geographic dataset for the 2011 Census.

    This function coordinates the three fundamental operations necessary to
    obtain all data for the 2011 Population Census:

    1. Download of tabular census data.
    2. Download of geodata for one or more regions (or all, if `region_list` is empty).
    3. Download of official administrative boundaries.

    In addition to downloading files, the function automatically creates the
    necessary folder structure within the output directory.

    Args:
        output_data_folder: Main path where all census data will be saved.
        region_list: List containing region codes or names for which to download
            geodata. If not provided or empty, the function downloads data for all regions.

    Returns:
        Path to the root folder containing the 2011 Census data structure.

    Note:
        This is a function specific to the 2011 census (the `census_year` parameter
        is fixed internally).
        It uses support functions: `download_data()`, `download_geodata()`,
        and `download_administrative_boundaries()`.
        The internal folder used for preprocessing is determined by the
        `PREPROCESSING_FOLDER` constant.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2011)

    # Download geodata
    download_geodata(output_data_folder=data_folder, region_list=region_list, census_year=2011)

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2011)

    return output_data_folder
