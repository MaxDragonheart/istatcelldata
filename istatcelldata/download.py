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
    """Scarica un file da URL, mostra una barra di avanzamento ed estrae lo ZIP risultante.

    La funzione gestisce l’intero flusso di download di un archivio (tipicamente ZIP)
    a partire da un URL HTTP/HTTPS, salvandolo in un percorso locale, mostrando una
    barra di avanzamento tramite `tqdm`, estraendo il contenuto nella cartella
    di destinazione e infine rimuovendo il file compresso.

    Args:
        data_link (str):
            URL da cui scaricare il file (es. archivio ZIP dei dati censuari).
        data_file_path_destination (Path):
            Percorso completo del file da creare in locale (file compresso scaricato).
        data_folder (Path):
            Cartella in cui verrà estratto il contenuto del file compresso.
        destination_folder (Path):
            Cartella logica di destinazione associata al dataset scaricato; viene
            restituita al termine del processo per coerenza con il workflow chiamante.

    Returns:
        Path:
            Percorso di `destination_folder`, utilizzabile come riferimento
            alla radice dei dati scaricati ed estratti.

    Raises:
        Exception:
            Se il server restituisce un codice di stato HTTP diverso da 200
            oppure se si verifica un qualsiasi errore durante il download,
            il salvataggio o l’estrazione del file.
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
