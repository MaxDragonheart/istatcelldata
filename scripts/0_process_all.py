import datetime
import logging
from pathlib import Path

from istatcelldata.config import PREPROCESSING_FOLDER
from istatcelldata.executor.download import download_census
from istatcelldata.executor.preprocess import preprocess_census
from istatcelldata.executor.process import finalize_census_data
from istatcelldata.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census")
list_year = [1991, 2001, 2011, 2021]
list_region = []

# Configure logging at the start of the script
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="process_all",
    )

# Define the logger as a global variable
logger = logging.getLogger(__name__)

def run(
        years: list,
        regions: list,
        data_dir: Path,
        delete_download_folder: bool,
        delete_preprocessed_data: bool,
        municipalities_code: list[int]
):
    """Esegue l’intero workflow ETL dei dati di censimento per uno o più anni.

    La funzione coordina l’intero processo di gestione dei dati censuari,
    eseguendo in sequenza:

    1. **Download** dei dati censuari, geodati e confini amministrativi per
       gli anni specificati.
    2. **Preprocessing** dei dati (geografici e tabellari), con eventuale
       filtro sui comuni di interesse.
    3. **Finalizzazione** dei dati in un GeoPackage unico, pronto per analisi
       e utilizzo in ambiente GIS/DB.

    Args:
        years (list):
            Lista degli anni di censimento da processare
            (es. [1991, 2001, 2011, 2021]).
        regions (list):
            Lista dei codici delle regioni da considerare per il download dei
            geodati. Se la logica interna di `download_census()` prevede che una
            lista vuota significhi “tutte le regioni”, questo comportamento viene
            ereditato.
        data_dir (Path):
            Cartella radice in cui vengono salvati:
            - i dati scaricati,
            - i dati pre-processati,
            - i dati finali (GeoPackage).
        delete_download_folder (bool):
            Se True, elimina la cartella dei dati scaricati/pre-processati
            al termine della fase di preprocessing (parametro propagato a
            `preprocess_census()`).
        delete_preprocessed_data (bool):
            Se True, elimina i dati pre-processati (es. `census.gpkg`) al termine
            della fase di finalizzazione (parametro propagato a
            `finalize_census_data()`).
        municipalities_code (list[int]):
            Lista di codici ISTAT dei comuni (`PRO_COM`) da estrarre. Se la logica
            interna delle funzioni chiamate lo prevede, una lista vuota significa
            che vengono considerati tutti i comuni.

    Returns:
        None

    Notes:
        - La funzione funge da entrypoint alto-livello per l’intera pipeline
          ISTAT (download → preprocess → finalizza).
        - Si appoggia alle funzioni:
          `download_census()`, `preprocess_census()`, `finalize_census_data()`.
        - I tempi di esecuzione complessivi vengono loggati.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Inizio analisi alle {time_start} per gli anni: {years}.")

    # Fase di download dei dati del censimento
    logging.info(f"Download dei dati del censimento per gli anni {years}.")
    download_census(
        years=years,
        output_data_folder=data_dir,
        region_list=regions,
    )
    logging.info("Download completato con successo.")

    # Fase di preprocessing dei dati del censimento
    logging.info("Avvio del preprocessing dei dati del censimento.")
    preprocess_census(
        processed_data_folder=data_dir.joinpath(PREPROCESSING_FOLDER),
        years=years,
        delete_download_folder=delete_download_folder,
        municipalities_code=municipalities_code
    )
    logging.info("Preprocessing completato con successo.")

    # Fase di finalizzazione dei dati del censimento
    logging.info("Avvio della finalizzazione dei dati del censimento.")
    finalize_census_data(
        census_data_path=data_dir,
        years=years,
        delete_preprocessed_data=delete_preprocessed_data
    )

    # Tempo totale di esecuzione
    time_end = datetime.datetime.now()
    elapsed_time = time_end - time_start
    logging.info(f"Analisi completata in {elapsed_time}.")


if __name__ == '__main__':
    # Inizializza il logging
    setup_logging(log_dir=main_path)

    # Esecuzione della funzione principale
    run(
        years=list_year,
        regions=list_region,
        data_dir=main_path,
        delete_download_folder=True,
        delete_preprocessed_data=True,
        # municipalities_code=[1136, 2088, 85007]
    )
