import logging
from pathlib import Path
from typing import Union

import pandas as pd
import geopandas as gpd

from istatcelldata.config import GEOMETRY_COLUMN_NAME, BOUNDARIES_DATA_FOLDER
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def read_administrative_boundaries(
        file_path: Path,
        target_columns: list,
        index_column: str,
        column_remapping: dict = None,
        with_geometry: bool = False,
        output_folder: Path = None,
        layer_name: str = None,
) -> Union[pd.DataFrame, Path]:
    """Legge i confini amministrativi da un file shapefile e restituisce un DataFrame filtrato.

    Args:
        file_path (Path): Percorso del file shapefile contenente i confini amministrativi.
        target_columns (list): Lista delle colonne da selezionare dal file.
        index_column (str): Nome della colonna da utilizzare come indice per il DataFrame.
        column_remapping (dict, opzionale): Mappa di rinominazione per le colonne. Default: None.
        with_geometry (bool, opzionale): Se True, include la geometria nel GeoDataFrame. Default: False.
        output_folder (Path, opzionale): Percorso della cartella di output per salvare il GeoPackage.
        Obbligatorio se `with_geometry` è True.
        layer_name (str, opzionale): Nome del layer per il GeoPackage. Obbligatorio se `with_geometry` è True.

    Returns:
        pd.DataFrame o Path: DataFrame filtrato o percorso del file GeoPackage se `with_geometry` è True.

    Raises:
        ValueError: Se `with_geometry` è True, ma `output_folder` o `layer_name` non sono forniti.
    """
    logging.info(f"Lettura dei confini amministrativi da {file_path}")

    # Determina la codifica del file .dbf associato
    regions_db = file_path.parent.joinpath(f"{file_path.stem}.dbf")
    encoding = check_encoding(data=regions_db)
    logging.info(f"Codifica rilevata: {encoding}")

    # Lettura del file shapefile con la codifica appropriata
    data = gpd.read_file(filename=file_path, encoding=encoding)
    logging.info(f"File {file_path} letto con successo")

    # Aggiunta della geometria se richiesto
    if with_geometry:
        target_columns.append(GEOMETRY_COLUMN_NAME)

        # Controlla che output_folder e layer_name siano specificati
        if output_folder is None or layer_name is None:
            raise ValueError("Quando 'with_geometry' è True, 'output_folder' e 'layer_name' devono essere forniti.")

    # Selezione delle colonne di interesse
    data_target = data[target_columns]
    logging.info(f"Colonne selezionate: {target_columns}")

    # Rinominazione delle colonne se specificato
    if column_remapping is not None:
        data_target.rename(columns=column_remapping, inplace=True)
        logging.info(f"Colonne rinominate secondo la mappa: {column_remapping}")

    # Imposta la colonna indice e ordina i dati
    data_target.set_index(index_column, inplace=True)
    logging.info(f"Impostata colonna indice: {index_column}")
    data_target.sort_index(inplace=True)
    logging.info(f"Dati ordinati in base alla colonna {index_column}")

    # Gestione con geometria
    if with_geometry:
        gdf = gpd.GeoDataFrame(data_target, crs=data.crs)
        geopackage_path = output_folder.joinpath(f"{BOUNDARIES_DATA_FOLDER}.gpkg")
        gdf.to_file(filename=str(geopackage_path), driver="GPKG", layer=layer_name)
        logging.info(f"GeoPackage salvato in {geopackage_path} con il layer {layer_name}")
        return geopackage_path

    # Ritorna il DataFrame senza geometria
    else:
        return data_target
