import logging
from pathlib import Path

import pandas as pd
import geopandas as gpd

from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def read_major_boundaries(
        file_path: Path,
        target_columns: list,
        index_column: str
) -> pd.DataFrame:
    """Legge i confini amministrativi principali da un file e restituisce un DataFrame filtrato.

    Args:
        file_path (Path): Percorso del file contenente i confini amministrativi in formato shapefile.
        target_columns (list): Lista delle colonne da selezionare dal file shapefile.
        index_column (str): Nome della colonna da utilizzare come indice per il DataFrame.

    Returns:
        pd.DataFrame: DataFrame con le colonne selezionate e ordinato in base all'indice specificato.
    """
    logging.info(f"Lettura dei confini amministrativi da {file_path}")

    # Determina la codifica del file
    regions_db = file_path.parent.joinpath(f"{file_path.stem}.dbf")
    encoding = check_encoding(data=regions_db)
    logging.info(f"Codifica rilevata: {encoding}")

    # Lettura del file shapefile con la codifica appropriata
    data = gpd.read_file(filename=file_path, encoding=encoding)
    logging.info(f"File {file_path} letto con successo")

    # Selezione delle colonne di interesse
    data_target = data[target_columns]
    logging.info(f"Colonne selezionate: {target_columns}")

    # Imposta la colonna indice e ordina i dati
    data_target.set_index(index_column, inplace=True)
    logging.info(f"Impostata colonna indice: {index_column}")
    data_target.sort_index(inplace=True)
    logging.info(f"Dati ordinati in base alla colonna {index_column}")

    return data_target
