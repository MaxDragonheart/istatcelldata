import logging
from pathlib import Path

from istatcelldata.census1991.utils import census_trace
from istatcelldata.census2011.download import download_data as dwn
from istatcelldata.census2021.utils import read_xlsx
from istatcelldata.config import DATA_FOLDER, CENSUS_DATA_FOLDER
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import get_census_dictionary, remove_files

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

YEAR = 2021

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
    files_list = list(data_folder.rglob("*.xlsx"))

    if not files_list:
        logging.error("Nessun file XLSX trovato nella cartella dei dati.")
        raise Exception("Nessun file XLSX trovato per il tracciamento.")

    logging.info(f"Estrazione dei dati censuari in formato xlsx e conversione in csv.")
    # Convert xls to csv
    for file_path in files_list:
        read_xlsx(
            file_path=file_path,
            output_path=final_folder
        )

    # Rimuovi i file XLS non necessari
    logging.info(f"Rimozione dei file XLS dalla cartella {data_folder}")
    remove_files(files_path=files_list)

    logging.info(f"Download dei dati censuari completato e salvato in {data_folder}")
    return data_folder
