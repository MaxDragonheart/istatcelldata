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
        data_column_remapping: dict = None,
        add_administrative_informations: bool = None,
        regions_data_path: Path = None,
        regions_target_columns: list = None,
        provinces_data_path: Path = None,
        provinces_target_columns: list = None,
        municipalities_data_path: Path = None,
        municipalities_target_columns: list = None,
        output_folder: Path = None,
) -> Union[dict, Path]:
    """Preprocessa i file CSV del censimento e restituisce i dati aggregati e il tracciato.

    La funzione esegue le seguenti operazioni:

    1. Cerca tutti i file CSV nella cartella indicata.
    2. Utilizza l’ultimo CSV (in ordine alfabetico) come file di tracciato (trace).
    3. Carica e concatena tutti gli altri CSV in un unico DataFrame.
    4. Applica, se fornita, una mappatura dei nomi di colonna (`data_column_remapping`).
    5. Aggiunge, se richiesto, le informazioni amministrative (regioni, province, comuni).
    6. Sostituisce eventuali valori NaN con 0.
    7. Carica il file di tracciato in un DataFrame dedicato.
    8. Restituisce:
       - o un dizionario con i DataFrame `census_data` e `trace`,
       - oppure salva i CSV risultanti in `output_folder` e restituisce il percorso.

    Args:
        data_folder (Path):
            Cartella contenente i file CSV da processare.
        data_column_remapping (dict, optional):
            Dizionario di mappatura per rinominare le colonne del dataset
            di censimento (es. `{"pro_com": "PRO_COM"}`).
        add_administrative_informations (bool, optional):
            Se True, arricchisce i dati con informazioni amministrative
            (regioni, province, comuni) tramite `add_administrative_info()`.
        regions_data_path (Path, optional):
            Percorso del file contenente i dati delle regioni.
        regions_target_columns (list, optional):
            Lista delle colonne da estrarre/tenere per i dati delle regioni.
        provinces_data_path (Path, optional):
            Percorso del file contenente i dati delle province.
        provinces_target_columns (list, optional):
            Lista delle colonne da estrarre/tenere per i dati delle province.
        municipalities_data_path (Path, optional):
            Percorso del file contenente i dati dei comuni.
        municipalities_target_columns (list, optional):
            Lista delle colonne da estrarre/tenere per i dati dei comuni.
        output_folder (Path, optional):
            Cartella di destinazione in cui salvare i file:
            - `census_data.csv` per i dati concatenati;
            - `census_trace.csv` per il tracciato.
            Se None, i dati vengono restituiti come dizionario di DataFrame.

    Returns:
        Union[dict, Path]:
            - dict: con le chiavi:
                - `"census_data"` → DataFrame con i dati del censimento concatenati;
                - `"trace"` → DataFrame con il tracciato dei campi.
              Restituito se `output_folder` è None.
            - Path: percorso di `output_folder`, se specificato, in cui sono stati
              salvati i file `census_data.csv` e `census_trace.csv`.

    Raises:
        ValueError:
            Se non viene trovato alcun file CSV nella cartella indicata.

    Notes:
        - Il file di tracciato (trace) è considerato l’ultimo CSV in ordine
          alfabetico all’interno di `data_folder`.
        - La funzione `check_encoding()` viene utilizzata per determinare
          l’encoding corretto dei file CSV.
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
    if data_column_remapping is not None:
        df.rename(columns=data_column_remapping, inplace=True)

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
