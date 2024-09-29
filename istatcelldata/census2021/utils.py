import logging
from pathlib import Path
from typing import Union

import pandas as pd

from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def read_xlsx(
        file_path: Path,
        output_path: Path = None,
) -> Union[pd.DataFrame, Path]:
    """Legge un file Excel (formato .xlsx) e lo converte in un DataFrame Pandas.
    Se specificato, salva i dati in formato CSV.

    Args:
        file_path (Path): Il percorso del file Excel da leggere.
        output_path (Path, opzionale): Il percorso in cui salvare il file CSV generato.
            Se non viene specificato, restituisce il DataFrame.

    Returns:
        Union[pd.DataFrame, Path]: Restituisce un DataFrame se `output_path` è None,
        altrimenti restituisce il percorso del file CSV salvato.

    Raises:
        FileNotFoundError: Se il file Excel specificato non viene trovato.
        ValueError: Se il file Excel non può essere letto correttamente.
    """
    try:
        print(file_path.stem[:1])
        logging.info(f"Lettura del file Excel da {file_path}")
        # Lettura del file Excel utilizzando il motore 'openpyxl'
        df = pd.read_excel(file_path, engine='openpyxl')


        # Se non viene fornito un percorso di output, restituisce il DataFrame
        if output_path is None:
            logging.info(f"Restituzione del DataFrame senza salvare su disco.")
            return df
        else:
            if file_path.stem[:1] == "R":
                file_name = file_path.stem
                census_data_path = output_path.joinpath(f'{file_name}.csv')
                logging.info(f"Salvataggio dei dati in formato CSV in {census_data_path}")
                # Salva i dati nel percorso specificato
                df.to_csv(path_or_buf=census_data_path, sep=';', index=False)
                logging.info(f"Dati salvati correttamente in {census_data_path}")
                return census_data_path
            else:
                trace_data_path = output_path.joinpath('tracciato_2021_sezioni.csv')
                logging.info(f"Salvataggio dei dati del tracciato in {trace_data_path}")
                # Salva i dati nel percorso specificato
                df.to_csv(path_or_buf=trace_data_path, sep=';', index=False)
                logging.info(f"Dati salvati correttamente in {trace_data_path}")
                return trace_data_path

    except FileNotFoundError as e:
        logging.error(f"File non trovato: {file_path}")
        raise e
    except ValueError as e:
        logging.error(f"Errore nella lettura del file Excel: {file_path}. Dettagli: {str(e)}")
        raise e
