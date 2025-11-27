import logging
from pathlib import Path
from typing import List

from istatcelldata.census1991.download import download_data
from istatcelldata.census2011.download import download_geodata, download_administrative_boundaries
from istatcelldata.config import PREPROCESSING_FOLDER
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_all_census_data_2001(
        output_data_folder: Path,
        region_list: List = []
) -> Path:
    """Scarica l'intero set di dati censuari e geografici relativi al Censimento 2001.

    Questa funzione coordina tutte le operazioni necessarie per ottenere i dati
    censuari e le informazioni geografiche associate al Censimento 2001.
    In particolare, si occupa di:

    - scaricare i dati censuari tabellari;
    - scaricare i geodati (per tutte le Regioni o per un sottoinsieme specificato);
    - scaricare i confini amministrativi ufficiali.

    Se `region_list` è vuota, vengono scaricati i geodati per tutte le Regioni
    disponibili.

    Args:
        output_data_folder (Path):
            Percorso principale in cui salvare tutti i dati scaricati e processati.
        region_list (List, optional):
            Lista dei codici o nomi delle Regioni di cui scaricare i geodati.
            Se lasciata vuota, la funzione considera tutte le Regioni.

    Returns:
        Path:
            Percorso della cartella radice `output_data_folder` contenente la
            struttura dei dati del Censimento 2001.

    Notes:
        - La funzione è specifica per il Censimento 2001 (il parametro `census_year`
          è fissato internamente a 2001).
        - Utilizza le funzioni di supporto:
          `download_data()`, `download_geodata()` e
          `download_administrative_boundaries()`.
        - Crea automaticamente una sottocartella dedicata al preprocessing,
          definita dalla costante `PREPROCESSING_FOLDER`.
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_data(output_data_folder=data_folder, census_year=2001)

    # Download geodata
    download_geodata(
        output_data_folder=data_folder, region_list=region_list, census_year=2001
    )

    # Download administrative boundaries
    download_administrative_boundaries(output_data_folder=data_folder, census_year=2001)

    return output_data_folder
