import logging
from pathlib import Path
from typing import Union

import pandas as pd
from tqdm import tqdm

from istatcelldata.census1991.process import add_administrative_info
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def preprocess_data(
        data_folder: Path,
        add_administrative_informations: bool = None,
        regions_data_path: Path = None,
        regions_target_columns: list = None,
        provinces_data_path: Path = None,
        provinces_target_columns: list = None,
        municipalities_data_path: Path = None,
        municipalities_target_columns: list = None,
        output_folder: Path = None,
) -> Union[dict, Path]:
    """Preprocessa i file CSV presenti in una cartella e restituisce i dati concatenati e il file di trace.

    Args:
        data_folder (Path): Cartella contenente i file CSV da processare.
        add_administrative_informations (bool, opzionale): Se True, aggiunge le informazioni amministrative ai dati.
        regions_data_path (Path, opzionale): Percorso del file contenente i dati delle regioni.
        regions_target_columns (list, opzionale): Lista delle colonne target per i dati delle regioni.
        provinces_data_path (Path, opzionale): Percorso del file contenente i dati delle province.
        provinces_target_columns (list, opzionale): Lista delle colonne target per i dati delle province.
        municipalities_data_path (Path, opzionale): Percorso del file contenente i dati dei comuni.
        municipalities_target_columns (list, opzionale): Lista delle colonne target per i dati dei comuni.


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
    for csv in tqdm(csv_list, desc="Lettura dei file CSV..."):
        if csv != trace:
            logging.info(f"Processamento file: {csv}")

            # Lettura del file CSV
            read_csv = pd.read_csv(filepath_or_buffer=csv, sep=';', encoding=check_encoding(data=csv))
            data_list.append(read_csv)

    # Concatena tutti i dati letti in un unico DataFrame
    df = pd.concat(data_list, ignore_index=True)

    if add_administrative_informations:
        df = add_administrative_info(
            census_data=df,
            regions_data_path=regions_data_path,
            regions_target_columns=regions_target_columns,
            provinces_data_path=provinces_data_path,
            provinces_target_columns=provinces_target_columns,
            municipalities_data_path=municipalities_data_path,
            municipalities_target_columns=municipalities_target_columns
        )
    df.fillna(value=0, inplace=True)
    logging.info("Dati concatenati con successo")

    # Lettura del file di trace
    trace_df = pd.read_csv(filepath_or_buffer=trace, sep=';', encoding=check_encoding(data=trace))
    logging.info(f"File di trace letto con successo: {trace}")

    logging.info(f"Preprocessing completato con successo.")
    if output_folder is not None:
        logging.info(f"Salvataggio dei file...")
        census_file_path = output_folder.joinpath("census_data.csv")
        df.to_csv(census_file_path, index=False, sep=';')

        trace_file_path = output_folder.joinpath("census_trace.csv")
        trace_df.to_csv(trace_file_path, index=False, sep=';')

        return output_folder

    else:
        # Restituisce il dizionario con i dati concatenati e il file di trace.
        result = {
            'census_data': df,
            'trace': trace_df,
        }
        return result
