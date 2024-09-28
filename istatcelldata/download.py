import logging
import os
import time
from pathlib import Path

import requests
from tqdm import tqdm

from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import unzip_data

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_base(
        data_link: str,
        data_file_path_destination: Path,
        data_folder: Path,
        destination_folder: Path,
) -> Path:
    """Funzione di download base per scaricare dati da un link.

    La funzione si occupa di scaricare i dati dal link fornito e salvarli nel percorso
    specificato. Se il download ha successo, il file ZIP scaricato viene estratto e
    il file ZIP originale viene eliminato.

    Args:
        data_link (str): L'URL da cui scaricare i dati.
        data_file_path_destination (Path): Il percorso dove salvare il file scaricato.
        data_folder (Path): La cartella dove estrarre i dati.
        destination_folder (Path): La cartella di destinazione.

    Returns:
        Path: Il percorso della cartella di destinazione.

    Raises:
        Exception: Se il download fallisce, restituisce il codice di stato HTTP.
    """
    start_time = time.time()
    try:
        logging.info(f"Inizio download dei dati dal link: {data_link}")
        data = requests.get(data_link, stream=True)

        # Controlla lo stato del download
        if data.status_code == 200:
            data_size = int(data.headers.get('Content-Length', 0))

            # Barra di avanzamento tramite tqdm
            with open(data_file_path_destination, 'wb') as output_file:
                # Usa tqdm per la barra di avanzamento
                with tqdm(total=data_size, desc="In download...", unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                    for chunk in data.iter_content(chunk_size=1024):  # Scarica il file in chunk
                        if chunk:  # Evita chunk vuoti
                            output_file.write(chunk)
                            pbar.update(len(chunk))  # Aggiorna la barra di avanzamento

            end_time = time.time()  # Tempo di fine
            elapsed_time = end_time - start_time  # Calcola il tempo trascorso
            logging.info(f"Download completato con successo in {elapsed_time:.2f} secondi.")
        else:
            logging.error(f"Download fallito. Codice di stato: {data.status_code}")
            raise Exception(f"Link {data_link} restituisce codice di stato {data.status_code}.")

        logging.info("Inizio estrazione del file ZIP.")
        unzip_data(data_file_path_destination, data_folder)

        logging.info(f"Eliminazione del file ZIP | {data_file_path_destination}")
        os.remove(data_file_path_destination)
        logging.info("File ZIP eliminato con successo.")

    except Exception as e:
        logging.error(f"Errore durante il download: {str(e)}")
        raise e

    return destination_folder
