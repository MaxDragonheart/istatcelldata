import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.utils import census_trace, remove_xls
from istatcelldata.config import GEODATA_FOLDER, DATA_FOLDER, CENSUS_DATA_FOLDER, BOUNDARIES_DATA_FOLDER, \
    PREPROCESSING_FOLDER
from istatcelldata.download import download_base
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import census_folder, get_region

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


YEAR = 1991

MAIN_LINK = "https://www.istat.it/storage/cartografia"
DATA_LINK = f"{MAIN_LINK}/variabili-censuarie/dati-cpa_{YEAR}.zip"
GEODATA_LINK = f"{MAIN_LINK}/basi_territoriali/WGS_84_UTM/{YEAR}/"

ADMIN_BOUNDARIES = f"{MAIN_LINK}/confini_amministrativi/non_generalizzati/Limiti{YEAR}.zip"

def download_data(
        output_data_folder: Path,
        url: str,
        year: int
) -> Path:
    """Scarica i dati censuari e li salva in una cartella di destinazione.

    Questa funzione crea una cartella di destinazione per i dati,
    scarica i file necessari, esegue il tracciamento dei dati dal file
    Excel e rimuove i file XLS non necessari.

    Args:
        output_data_folder (Path): Il percorso della cartella in cui
            salvare i dati scaricati.

    Returns:
        Path: Il percorso della cartella di destinazione contenente
            i dati scaricati.

    Raises:
        Exception: Se si verifica un errore durante il download o il
            salvataggio dei dati.
    """
    try:
        # Creazione della cartella di destinazione per i dati
        logging.info(f"Creazione della cartella di destinazione per i dati in {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=year)
        Path(destination_folder).mkdir(parents=True, exist_ok=True)

        data_folder = destination_folder.joinpath(DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = Path(url).stem + Path(url).suffix
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Download dei dati da {url}")
        download_base(
            data_link=url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

        final_folder = data_folder.joinpath(CENSUS_DATA_FOLDER)
        Path(final_folder).mkdir(parents=True, exist_ok=True)

        # Esegui il tracciamento dei dati dal primo file XLS trovato
        files_list = list(data_folder.rglob("*.xls"))
        if not files_list:
            logging.error("Nessun file XLS trovato nella cartella dei dati.")
            raise Exception("Nessun file XLS trovato per il tracciamento.")

        first_element = files_list[0]
        logging.info(f"Estrazione del tracciamento dei dati dal file {first_element}")
        census_trace(
            file_path=first_element,
            year=year,
            output_path=final_folder
        )

        # Rimuovi i file XLS non necessari
        logging.info(f"Rimozione dei file XLS dalla cartella {data_folder}")
        remove_xls(
            folder_path=data_folder,
            census_code=f"sez{year}",
            output_path=final_folder
        )

        logging.info(f"Download dei dati censuari completato e salvato in {destination_folder}")
        return destination_folder

    except Exception as e:
        logging.error(f"Errore durante il download dei dati: {str(e)}")
        raise e


def download_geodata(
        output_data_folder: Path,
        url: str,
        year: int,
        region_list: List[int] = []
) -> Path:
    """Scarica i dati geocensuari per le regioni specificate.

    Questa funzione crea una struttura di cartelle per i dati censuari e scarica i file
    ZIP contenenti i dati geocensuari per le regioni indicate. Se non vengono fornite
    regioni, vengono scaricati i dati per tutte le 20 regioni.

    Args:
        output_data_folder (Path): La cartella di output principale per i dati.
        region_list (List[int], optional): Lista di regioni da scaricare. Se vuota,
            scarica i dati per tutte le regioni (default: []).

    Returns:
        Path: La cartella contenente i dati geocensuari scaricati.
    """
    # Creazione della cartella di destinazione per i dati
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    data_folder = destination_folder.joinpath(GEODATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    year_folder = str(year)[2:]  # Ultime due cifre dell'anno

    # Imposta la lista delle regioni da scaricare
    regions = get_region(region_list=region_list)

    for region in regions:
        region_str = str(region).zfill(2)
        data_link = f"{url}/R{region_str}_{year_folder}_WGS84.zip"
        logging.info(f"Link dei dati: {data_link}")

        data_file_name = data_link.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)
        logging.info(f"Percorso del file di destinazione: {data_file_path_dest}")

        # Scarica i dati
        download_base(
            data_link=data_link,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

    return data_folder


def download_administrative_boundaries(
        output_data_folder: Path,
        url: str,
        year: int
) -> Path:
    """Scarica i confini amministrativi e li salva in una cartella di destinazione.

    Questa funzione crea una cartella di destinazione per i confini
    amministrativi e scarica il file necessario nella cartella creata.

    Args:
        output_data_folder (Path): Il percorso della cartella in cui
            salvare i confini amministrativi scaricati.

    Returns:
        Path: Il percorso della cartella di destinazione contenente
            i confini amministrativi scaricati.

    Raises:
        Exception: Se si verifica un errore durante il download dei
            confini amministrativi.
    """
    try:
        # Creazione della cartella per i dati del censimento annuale
        logging.info(f"Creazione della cartella per i dati del censimento in {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

        # Creazione della cartella per i confini amministrativi
        data_folder = destination_folder.joinpath(BOUNDARIES_DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = url.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Scaricamento dei confini amministrativi da {url}")
        download_base(
            data_link=url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

        logging.info(f"Download dei confini amministrativi completato e salvato in {destination_folder}")
        return destination_folder

    except Exception as e:
        logging.error(f"Errore durante il download dei confini amministrativi: {str(e)}")
        raise e


def download_all_census_data_1991(
        output_data_folder: Path,
        data_url: str,
        geodata_url: str,
        boudaries_url: str,
        year: int,
        region_list: List = []
) -> None:
    """Download di tutti i dati censuari per l'anno selezionato. E' possibile
    effettuare il download per singola Regione ma anche per specifiche Regioni.
    Quando il campo `region_list` resta vuoto vengono scaricati i dati di tutte le Regioni.

    Args:
        output_data_folder: Path
        region_list: List
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, url=data_url, year=year)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, url=geodata_url, year=year
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, url=boudaries_url, year=year)
