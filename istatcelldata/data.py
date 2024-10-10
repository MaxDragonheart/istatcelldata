import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def preprocess_data(data_folder: Path) -> dict:
    """Preprocessa i file CSV presenti in una cartella e restituisce i dati concatenati e il file di trace.

    Args:
        data_folder (Path): Cartella contenente i file CSV da processare.

    Returns:
        dict: Dizionario con i dati del censimento concatenati, il file di trace e l'anno di riferimento.

    Raises:
        ValueError: Se non vengono trovati file CSV nella cartella specificata.
    """
    logging.info(f"Inizio preprocessing dei dati nella cartella {data_folder}")

    # Trova e ordina tutti i file CSV nella cartella specificata
    csv_list = sorted(list(data_folder.glob('*.csv')))

    if not csv_list:
        raise ValueError(f"Nessun file CSV trovato nella cartella {data_folder}")

    logging.info(f"Trovati {len(csv_list)} file CSV")

    # Ultimo file CSV considerato come "trace"
    trace = csv_list[-1]
    logging.info(f"File di trace selezionato: {trace}")

    data_list = []

    # Itera attraverso i file CSV e carica i dati
    for csv in tqdm(csv_list, desc="Lettura dei file CSV"):
        if csv != trace:
            logging.info(f"Processamento file: {csv}")

            # Lettura del file CSV
            read_csv = pd.read_csv(filepath_or_buffer=csv, sep=';', encoding=check_encoding(data=csv))
            data_list.append(read_csv)
            break

    # Concatena tutti i dati letti in un unico DataFrame
    df = pd.concat(data_list, ignore_index=True)
    df.fillna(value=0, inplace=True)
    logging.info("Dati concatenati con successo")

    # Lettura del file di trace
    trace_df = pd.read_csv(filepath_or_buffer=trace, sep=';', encoding=check_encoding(data=trace))
    logging.info(f"File di trace letto con successo: {trace}")

    # Restituisce il dizionario con i dati concatenati, il file di trace e l'anno di riferimento
    result = {
        'census_data': df,
        'trace': trace_df,
    }

    logging.info(f"Preprocessing completato con successo.")
    return result