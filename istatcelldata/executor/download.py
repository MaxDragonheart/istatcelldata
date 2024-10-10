import datetime
import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.download import download_all_census_data_1991
from istatcelldata.census2001.download import download_all_census_data_2001
from istatcelldata.census2011.download import download_all_census_data_2011
from istatcelldata.census2021.download import download_all_census_data_2021
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_census(
        years: List[int],
        output_data_folder: Path,
        region_list: List = []
):
    """Scarica i dati censuari per gli anni specificati e salva i dati nella cartella di output.

    Args:
        years (List[int]): Lista degli anni censuari da scaricare. Se vuota, scarica i dati per tutti gli anni disponibili.
        output_data_folder (Path): Percorso della cartella di destinazione per i dati scaricati.
        region_list (List, opzionale): Lista delle regioni per cui scaricare i dati. Se vuota, scarica i dati per tutte le regioni.

    Raises:
        ValueError: Se un anno specificato non è supportato o non esiste nella mappa delle funzioni.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Inizio dell'analisi alle {time_start}")

    # Mappa degli anni censuari alle rispettive funzioni di download
    function_map = {
        1991: lambda: download_all_census_data_1991(output_data_folder=output_data_folder, region_list=region_list),
        2001: lambda: download_all_census_data_2001(output_data_folder=output_data_folder, region_list=region_list),
        2011: lambda: download_all_census_data_2011(output_data_folder=output_data_folder, region_list=region_list),
        2021: lambda: download_all_census_data_2021(output_data_folder=output_data_folder, region_list=region_list),
    }

    # Se la lista degli anni è vuota, scarica i dati per tutti gli anni disponibili
    if not years:
        logging.info("Nessun anno specificato, scarico tutti i dati disponibili (1991, 2001, 2011, 2021).")
        years = [1991, 2001, 2011, 2021]

    # Scarica i dati per ogni anno specificato
    for year in years:
        if year in function_map:
            logging.info(f"Scarico i dati per il censimento del {year}")
            function_map[year]()  # Chiamata alla funzione corrispondente per l'anno
        else:
            logging.error(f"Anno {year} non supportato. Operazione annullata.")
            raise ValueError(f"L'anno {year} non è supportato.")

    # Calcolo del tempo totale di esecuzione
    time_end = datetime.datetime.now() - time_start
    logging.info(f"Analisi completata in {time_end}")
