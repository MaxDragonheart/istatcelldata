import logging
from pathlib import Path
from typing import Union

import pandas as pd
import geopandas as gpd
from shapely.validation import make_valid
from tqdm import tqdm

from istatcelldata.config import GEOMETRY_COLUMN_NAME, BOUNDARIES_DATA_FOLDER, GLOBAL_ENCODING
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
    data_db = file_path.parent.joinpath(f"{file_path.stem}.dbf")
    encoding = check_encoding(data=data_db)
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
        gdf.to_file(filename=str(geopackage_path), driver="GPKG", layer=layer_name, encoding=GLOBAL_ENCODING)
        logging.info(f"GeoPackage salvato in {geopackage_path} con il layer {layer_name}")
        return geopackage_path

    # Ritorna il DataFrame senza geometria
    else:
        return data_target


def read_census(
        shp_folder: Path,
        target_columns: list,
        tipo_loc_mapping: dict,
        column_remapping: dict = None,
        output_folder: Path = None,
) -> Union[gpd.GeoDataFrame, Path]:
    """Legge i dati del censimento da una cartella contenente file shapefile e li restituisce come GeoDataFrame o
    salva in un GeoPackage.

    Args:
        shp_folder (Path): Percorso della cartella contenente i file shapefile del censimento.
        target_columns (list): Lista delle colonne da selezionare dai file shapefile.
        tipo_loc_mapping (dict): Mappatura dei codici di località per il campo 'tipo_loc'.
        column_remapping (dict, opzionale): Mappatura per rinominare le colonne del DataFrame. Default: None.
        output_folder (Path, opzionale): Percorso della cartella di output per salvare il GeoPackage. Default: None.

    Returns:
        Union[gpd.GeoDataFrame, Path]: Un GeoDataFrame con i dati del censimento o il percorso del GeoPackage salvato.

    Raises:
        ValueError: Se non ci sono shapefile nella cartella specificata.
    """
    logging.info(f"Lettura dei file shapefile dalla cartella {shp_folder}")

    # Lista di file shapefile nella cartella
    shp_list = list(shp_folder.rglob("*.shp"))
    if not shp_list:
        raise ValueError(f"Nessun file shapefile trovato nella cartella {shp_folder}")

    census_cells = []
    columns_list = []
    crs_list = []

    # Iterazione sui file shapefile trovati
    for shp in shp_list:
        data_db = shp.parent.joinpath(f"{shp.stem}.dbf")
        encoding = check_encoding(data=data_db)  # Determina la codifica del file .dbf associato
        logging.info(f"Lettura del file shapefile {shp} con codifica {encoding}")

        # Lettura del file shapefile
        data = gpd.read_file(filename=shp, encoding=encoding)
        crs_list.append(data.crs)  # Salva il sistema di riferimento spaziale (CRS)
        census_data = data[target_columns]
        logging.info(f"Colonne selezionate: {target_columns}")

        # Rinominazione delle colonne se specificato
        if column_remapping is not None:
            census_data.rename(columns=column_remapping, inplace=True)
            logging.info(f"Colonne rinominate secondo la mappa: {column_remapping}")

        columns_list.append(list(census_data.columns))

        # Iterazione sulle righe del DataFrame per costruire le celle del censimento
        for index, row in tqdm(census_data.iterrows(), total=census_data.shape[0]):
            census_geometry = make_valid(row[GEOMETRY_COLUMN_NAME])  # Corregge la geometria se necessario
            tipo_loc = tipo_loc_mapping.get(row[1], None)  # Mappa il codice di località
            census_row = [row[0], row[1], tipo_loc, census_geometry]
            census_cells.append(census_row)

    df_columns = columns_list[0]  # Recupera i nomi delle colonne
    df_columns.insert(df_columns.index(GEOMETRY_COLUMN_NAME), 'DEN_LOC')  # Aggiunge 'DEN_LOC' come colonna
    logging.info(f"Colonne finali: {df_columns}")

    # Creazione del DataFrame e GeoDataFrame
    df = pd.DataFrame(data=census_cells, columns=df_columns)
    gdf = gpd.GeoDataFrame(df, crs=crs_list[0])
    gdf['area_mq'] = round(gdf['geometry'].area, 2)
    gdf.set_index(df_columns[0], inplace=True)
    logging.info(f"GeoDataFrame creato con CRS: {crs_list[0]}")

    # Se viene fornito un percorso di output, salva il GeoDataFrame in un GeoPackage
    if output_folder is not None:
        geopackage_path = output_folder.joinpath("census_cells.gpkg")
        gdf.to_file(filename=str(geopackage_path), driver="GPKG", encoding=GLOBAL_ENCODING)
        logging.info(f"GeoPackage salvato in {geopackage_path}")
        return geopackage_path

    # Se nessun percorso di output è fornito, restituisce il GeoDataFrame
    else:
        return gdf
