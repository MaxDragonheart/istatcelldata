import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.download import MAIN_LINK, download_data, download_geodata, \
    download_administrative_boundaries
from istatcelldata.config import PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

YEAR = 2011

GEODATA_LINK = f"{MAIN_LINK}/basi_territoriali/WGS_84_UTM/{YEAR}/"
DATA_LINK = f"{MAIN_LINK}/variabili-censuarie/dati-cpa_{YEAR}.zip"
ADMIN_BOUNDARIES = f"{MAIN_LINK}/confini_amministrativi/non_generalizzati/Limiti{YEAR}.zip"


def download_all_census_data_2011(
        output_data_folder: Path,
        data_url: str,
        geodata_url: str,
        boudaries_url: str,
        census_year: int,
        region_list: List = []
) -> None:
    """Download di tutti i dati censuari per l'anno selezionato. E' possibile
    effettuare il download per singola Regione ma anche per specifiche Regioni.
    Quando il campo `region_list` resta vuoto vengono scaricati i dati di tutte le Regioni.

    Args:
        output_data_folder: Path
        region_list: List
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, url=data_url, census_year=census_year)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, url=geodata_url, census_year=census_year
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, url=boudaries_url, census_year=census_year)
