import logging
from pathlib import Path

from istatcelldata.census2011.download import download_data as dwn
from istatcelldata.config import DATA_FOLDER, CENSUS_DATA_FOLDER
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

YEAR = 2021

def download_data(
        output_data_folder: Path,
        census_year: int
) -> Path:
    data_folder = dwn(
        output_data_folder=output_data_folder,
        census_year=census_year
    )

    final_folder = data_folder.joinpath(DATA_FOLDER, CENSUS_DATA_FOLDER)
    Path(final_folder).mkdir(parents=True, exist_ok=True)

    # Esegui il tracciamento dei dati dal primo file XLS trovato
    files_list = list(data_folder.rglob("*.xlsx"))
    print(files_list)
    if not files_list:
        logging.error("Nessun file XLSX trovato nella cartella dei dati.")
        raise Exception("Nessun file XLSX trovato per il tracciamento.")

    first_element = files_list[0]
    logging.info(f"Estrazione del tracciamento dei dati dal file {first_element}")
    # census_trace(
    #     file_path=first_element,
    #     year=census_year,
    #     output_path=final_folder
    # )
    #
    # # Rimuovi i file XLS non necessari
    # logging.info(f"Rimozione dei file XLS dalla cartella {data_folder}")
    # remove_xls(
    #     folder_path=data_folder,
    #     census_code=f"sez{census_year}",
    #     output_path=final_folder
    # )

    logging.info(f"Download dei dati censuari completato e salvato in {data_folder}")
    return data_folder

