import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.utils import census_trace, read_xls
from istatcelldata.census2011.download import download_data as dwn, download_geodata, download_administrative_boundaries
from istatcelldata.config import DATA_FOLDER, CENSUS_DATA_FOLDER, PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import get_census_dictionary, remove_files

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


YEAR = 1991


def download_data(
        output_data_folder: Path,
        census_year: int
) -> Path:
    link_dict = get_census_dictionary(census_year=census_year)
    census_code = link_dict[f"census{census_year}"]["census_code"]

    data_folder = dwn(
        output_data_folder=output_data_folder,
        census_year=census_year
    )

    final_folder = data_folder.joinpath(DATA_FOLDER, CENSUS_DATA_FOLDER)
    Path(final_folder).mkdir(parents=True, exist_ok=True)

    # Esegui il tracciamento dei dati dal primo file XLS trovato
    files_list = list(data_folder.rglob("*.xls"))
    if not files_list:
        logging.error("Nessun file XLS trovato nella cartella dei dati.")
        raise Exception("Nessun file XLS trovato per il tracciamento.")

    logging.info(f"Estrazione dei dati censuari in formato xls e conversione in csv.")
    # Convert xls to csv
    for file_path in files_list:
        read_xls(
            file_path=file_path,
            census_code=census_code,
            output_path=final_folder
        )

    first_element = files_list[0]
    logging.info(f"Estrazione del tracciamento dei dati dal file {first_element}")
    census_trace(
        file_path=first_element,
        year=census_year,
        output_path=final_folder
    )

    # Rimuovi i file XLS non necessari
    logging.info(f"Rimozione dei file XLS dalla cartella {data_folder}")
    remove_files(files_path=files_list)

    logging.info(f"Download dei dati censuari completato e salvato in {data_folder}")
    return data_folder


def download_all_census_data_1991(
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
    download_data(output_data_folder=data_folder, census_year=YEAR)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, census_year=YEAR
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=YEAR)

    return output_data_folder
