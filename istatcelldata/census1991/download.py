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


def download_data(
        output_data_folder: Path,
        census_year: int
) -> Path:
    """Scarica, organizza ed elabora i dati censuari per un determinato anno.

    La funzione gestisce l'intero flusso di acquisizione dei dati censuari
    dall’origine fino alla produzione dei file CSV finali. Vengono effettuate
    le seguenti operazioni:

    1. Recupero del dizionario dei link relativi all'anno censuario.
    2. Download dei dati grezzi tramite la funzione `dwn()`.
    3. Creazione della struttura di cartelle di output.
    4. Individuazione e lettura dei file `.xls`.
    5. Conversione dei file Excel in CSV.
    6. Estrazione del tracciamento (metadati/codifiche) dal primo file disponibile.
    7. Rimozione dei file Excel originali.

    Args:
        output_data_folder (Path):
            Percorso della cartella radice in cui salvare i dati scaricati.
        census_year (int):
            Anno di riferimento dei dati censuari da trattare.

    Returns:
        Path: Percorso della cartella contenente i dati censuari scaricati
        ed elaborati.

    Raises:
        Exception: Se non viene trovato alcun file `.xls` nella cartella dei dati.

    Notes:
        - La conversione da XLS a CSV viene eseguita tramite la funzione `read_xls()`.
        - Il tracciamento del dataset viene effettuato solo sul primo file XLS trovato.
        - I file XLS vengono rimossi a fine processo per ridurre lo spazio occupato.
    """
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
    """Scarica l'intero set di dati censuari e geografici relativi al Censimento 1991.

    Questa funzione coordina tutte le operazioni necessarie per ottenere i dati
    censuari e le informazioni geografiche associate al Censimento 1991.
    Consente di scaricare:

    - dati censuari tabellari,
    - geodati specifici per una o più Regioni,
    - confini amministrativi ufficiali.

    Se non viene fornito alcun valore per `region_list`, vengono scaricati i
    geodati relativi a tutte le Regioni.

    Args:
        output_data_folder (Path):
            Percorso principale in cui salvare tutti i dati scaricati e processati.
        region_list (List, optional):
            Lista contenente i codici o nomi delle Regioni di cui scaricare i geodati.
            Se vuota, vengono considerate tutte le Regioni disponibili.

    Returns:
        Path: Percorso della cartella radice contenente i dati scaricati.

    Notes:
        - La funzione opera esclusivamente sul Censimento 1991.
        - Utilizza funzioni di supporto come `download_data()`,
          `download_geodata()` e `download_administrative_boundaries()`.
        - Crea automaticamente la struttura di cartelle necessaria.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=1991)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, census_year=1991
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=1991)

    return output_data_folder
