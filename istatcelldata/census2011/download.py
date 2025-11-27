import logging
from pathlib import Path
from typing import List

from istatcelldata.config import DATA_FOLDER, GEODATA_FOLDER, BOUNDARIES_DATA_FOLDER, PREPROCESSING_FOLDER
from istatcelldata.download import download_base
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import census_folder, get_census_dictionary

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_data(
        output_data_folder: Path,
        census_year: int
) -> Path:
    """Scarica i dati censuari per un anno specifico e organizza la cartella di lavoro.

    La funzione recupera dal dizionario dei censimenti il link ai dati relativi
    all'anno indicato, prepara la struttura di cartelle di destinazione e
    delega il download effettivo alla funzione `download_base()`. Al termine
    restituisce il percorso del file scaricato (o della cartella, a seconda
    di come `download_base()` è implementata).

    Args:
        output_data_folder (Path):
            Percorso della cartella di output in cui creare la struttura dati
            del censimento (es. cartella di preprocessing o progetto).
        census_year (int):
            Anno di riferimento del censimento di cui scaricare i dati
            (es. 1991, 2001, 2011).

    Returns:
        Path:
            Percorso restituito da `download_base()`, che rappresenta la
            posizione dei dati censuari scaricati (file o cartella).

    Raises:
        Exception:
            Se si verifica un errore durante il recupero del link, la creazione
            delle cartelle o il download dei dati.
    """
    link_dict = get_census_dictionary(census_year=census_year)
    data_url = link_dict[f"census{census_year}"]["data_url"]

    try:
        # Creazione della cartella di destinazione per i dati
        logging.info(f"Creazione della cartella di destinazione per i dati in {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)
        Path(destination_folder).mkdir(parents=True, exist_ok=True)

        data_folder = destination_folder.joinpath(DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = Path(data_url).stem + Path(data_url).suffix
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Download dei dati da {data_url}")
        download_data_path = download_base(
            data_link=data_url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

        logging.info(f"Download dei dati censuari completato e salvato in {destination_folder}")
        return download_data_path

    except Exception as e:
        logging.error(f"Errore durante il download dei dati: {str(e)}")
        raise e


def download_geodata(
        output_data_folder: Path,
        census_year: int,
        region_list: List[int] = []
) -> Path:
    """Scarica i dati geocensuari per una o più Regioni relative a un anno di censimento.

    La funzione recupera gli URL dei pacchetti geocensuari (ZIP) tramite
    `get_census_dictionary()`, crea la struttura delle cartelle di destinazione
    per l'anno censuario e procede a scaricare i file ZIP relativi alle regioni
    richieste. Se `region_list` è vuota, vengono scaricati i dati per tutte le
    Regioni disponibili nel dizionario (tipicamente 20).

    Args:
        output_data_folder (Path):
            Cartella radice in cui salvare l'intera struttura dei dati censuari.
        census_year (int):
            Anno di riferimento del censimento (es. 1991, 2001, 2011).
        region_list (List[int], optional):
            Lista dei codici ISTAT delle Regioni di cui scaricare i geodati.
            Se vuota, vengono scaricati i geodati per tutte le Regioni predefinite.

    Returns:
        Path:
            Percorso della cartella contenente i file ZIP geocensuari scaricati.

    Notes:
        - La funzione non esegue l'estrazione degli ZIP: scarica solamente i file.
        - Gli URL dei geodati sono ottenuti dal dizionario del censimento tramite
          la chiave `geodata_urls`.
        - Il percorso finale dei dati è organizzato tramite la costante globale
          `GEODATA_FOLDER`.
    """
    link_dict = get_census_dictionary(census_year=census_year, region_list=region_list)
    geodata_urls = link_dict[f"census{census_year}"]["geodata_urls"]

    # Creazione della cartella di destinazione per i dati
    destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    data_folder = destination_folder.joinpath(GEODATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    for url in geodata_urls:
        data_file_name = url.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)
        logging.info(f"Percorso del file di destinazione: {data_file_path_dest}")

        # Scarica i dati
        download_base(
            data_link=url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

    return data_folder


def download_administrative_boundaries(
        output_data_folder: Path,
        census_year: int
) -> Path:
    """Scarica i confini amministrativi per un anno di censimento e li salva nella struttura dati.

    La funzione recupera dal dizionario dei censimenti l’URL dei confini
    amministrativi (regioni, province, comuni), prepara la struttura di
    cartelle dedicata all’anno censuario e scarica il file ZIP associato.
    Il contenuto non viene estratto: la funzione si limita al download.

    Args:
        output_data_folder (Path):
            Percorso principale in cui verrà creata la struttura per i dati del censimento.
        census_year (int):
            Anno censuario di riferimento (ad esempio: 1991, 2001, 2011).

    Returns:
        Path:
            Percorso della cartella contenente i confini amministrativi scaricati.

    Raises:
        Exception:
            Se si verifica un errore durante la creazione delle cartelle o durante il download.

    Notes:
        - I confini amministrativi includono comuni, province e regioni.
        - Il file viene salvato nella cartella definita dalla costante
          `BOUNDARIES_DATA_FOLDER`.
        - Il percorso restituito è la cartella dell’anno censuario, non il singolo file scaricato.
    """
    link_dict = get_census_dictionary(census_year=census_year)
    data_url = link_dict[f"census{census_year}"]["admin_boundaries_url"]

    try:
        # Creazione della cartella per i dati del censimento annuale
        logging.info(f"Creazione della cartella per i dati del censimento in {output_data_folder}")
        destination_folder = census_folder(output_data_folder=output_data_folder, year=census_year)

        # Creazione della cartella per i confini amministrativi
        data_folder = destination_folder.joinpath(BOUNDARIES_DATA_FOLDER)
        Path(data_folder).mkdir(parents=True, exist_ok=True)

        data_file_name = data_url.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        logging.info(f"Scaricamento dei confini amministrativi da {data_url}")
        download_base(
            data_link=data_url,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

        logging.info(f"Download dei confini amministrativi completato e salvato in {destination_folder}")
        return destination_folder

    except Exception as e:
        logging.error(f"Errore durante il download dei confini amministrativi: {str(e)}")
        raise e


def download_all_census_data_2011(
        output_data_folder: Path,
        region_list: List = []
) -> Path:
    """Scarica l’intero set di dati censuari e geografici relativi al Censimento 2011.

    Questa funzione coordina le tre operazioni fondamentali necessarie per
    ottenere tutti i dati relativi al Censimento della Popolazione 2011:

    1. Download dei dati censuari tabellari.
    2. Download dei geodati per una o più Regioni (o tutte, se `region_list` è vuota).
    3. Download dei confini amministrativi ufficiali.

    Oltre a scaricare i file, la funzione crea in automatico la struttura di
    cartelle necessaria all’interno della directory di output.

    Args:
        output_data_folder (Path):
            Percorso principale in cui salvare tutti i dati del censimento.
        region_list (List, optional):
            Lista contenente i codici o i nomi delle Regioni di cui scaricare i geodati.
            Se non viene fornita o è vuota, la funzione scarica i dati per tutte le Regioni.

    Returns:
        Path:
            Percorso della cartella radice contenente la struttura dei dati del Censimento 2011.

    Notes:
        - È una funzione specifica per il censimento 2011 (il parametro `census_year`
          è fissato internamente).
        - Usa le funzioni di supporto: `download_data()`, `download_geodata()`,
          `download_administrative_boundaries()`.
        - La cartella interna usata per il preprocessing è determinata dalla costante
          `PREPROCESSING_FOLDER`.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2011)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, census_year=2011
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2011)

    return output_data_folder
