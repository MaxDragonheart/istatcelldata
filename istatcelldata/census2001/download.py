import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.download import download_data
from istatcelldata.census2011.download import download_geodata, download_administrative_boundaries
from istatcelldata.config import PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_all_census_data_2001(
        output_data_folder: Path,
        region_list: List = []
) -> Path:
    """Download di tutti i dati censuari per l'anno selezionato. E' possibile
    effettuare il download per singola Regione ma anche per specifiche Regioni.
    Quando il campo `region_list` resta vuoto vengono scaricati i dati di tutte le Regioni.

    Args:
        output_data_folder: Path
        region_list: List

    Returns:
        Path di destinazione.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2001)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, census_year=2001
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2001)

    return output_data_folder
