import logging
from pathlib import Path
from typing import Union

import pandas as pd
import geopandas as gpd
from shapely.validation import make_valid
from tqdm import tqdm

from istatcelldata.config import GEOMETRY_COLUMN_NAME, GLOBAL_ENCODING, YEAR_GEODATA_NAME
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
        output_folder: Path = None,
        layer_name: str = None,
) -> Union[pd.DataFrame, Path]:
    """Legge i confini amministrativi da un file shapefile e restituisce un DataFrame filtrato.

    Args:
        file_path (Path): Percorso del file shapefile contenente i confini amministrativi.
        target_columns (list): Lista delle colonne da selezionare dal file.
        index_column (str): Nome della colonna da utilizzare come indice per il DataFrame.
        column_remapping (dict, opzionale): Mappa di rinominazione per le colonne. Default: None.
        output_folder (Path, opzionale): Percorso della cartella di output per salvare il GeoPackage.
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

    # Selezione delle colonne di interesse
    target_columns.extend([GEOMETRY_COLUMN_NAME])
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

    if output_folder is None:
        data_target.drop(columns=[GEOMETRY_COLUMN_NAME], inplace=True)
        data_target = pd.DataFrame(data_target)

        return data_target

    else:
        # Gestione con geometria
        gdf = gpd.GeoDataFrame(data=data_target, crs=data.crs)

        geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
        gdf.to_file(filename=str(geopackage_path), driver="GPKG", layer=layer_name, encoding=GLOBAL_ENCODING)
        logging.info(f"GeoPackage salvato in {geopackage_path} con il layer {layer_name}")
        return geopackage_path


def read_census(
        shp_folder: Path,
        target_columns: list,
        tipo_loc_mapping: dict,
        column_remapping: dict = None,
        output_folder: Path = None,
        layer_name: str = None
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
            census_geometry = row[GEOMETRY_COLUMN_NAME]

            # Verifica se la geometria è presente
            if census_geometry is not None:
                validated_geometry = make_valid(census_geometry)  # Corregge la geometria se necessario
                row[GEOMETRY_COLUMN_NAME] = validated_geometry
                census_row = row.to_list()
                tipo_loc = tipo_loc_mapping.get(row['TIPO_LOC'], None)  # Mappa il codice di località
                census_row.extend([tipo_loc])
                census_cells.append(census_row)
            else:
                logging.warning(f"Per la sezione {row[0]} la geometria è `None` o irreparabilmente danneggiata.")
                pass

    df_columns = columns_list[0]  # Recupera i nomi delle colonne
    df_columns.extend(['DEN_LOC'])  # Aggiunge 'DEN_LOC' come colonna
    logging.info(f"Colonne finali: {df_columns}")

    # Creazione del DataFrame e GeoDataFrame
    df = pd.DataFrame(data=census_cells, columns=df_columns)
    gdf = gpd.GeoDataFrame(df, crs=crs_list[0])
    gdf['area_mq'] = round(gdf['geometry'].area, 2)
    gdf.set_index(df_columns[0], inplace=True)
    logging.info(f"GeoDataFrame creato con CRS: {crs_list[0]}")

    # Se viene fornito un percorso di output, salva il GeoDataFrame in un GeoPackage
    if output_folder is not None:
        geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
        gdf.to_file(filename=str(geopackage_path), driver="GPKG", encoding=GLOBAL_ENCODING, layer=layer_name)
        logging.info(f"GeoPackage salvato in {geopackage_path}")
        return geopackage_path

    # Se nessun percorso di output è fornito, restituisce il GeoDataFrame
    else:
        return gdf


def preprocess_geodata(
        census_shp_folder: Path,
        census_target_columns: list,
        census_tipo_loc_mapping: dict,
        output_folder: Path,
        census_layer_name: str,
        census_column_remapping: dict = None,
        regions_file_path: Path = None,
        regions_target_columns: list = None,
        regions_index_column: str = None,
        regions_column_remapping: dict = None,
        provinces_file_path: Path = None,
        provinces_target_columns: list = None,
        provinces_index_column: str = None,
        provinces_column_remapping: dict = None,
        municipalities_file_path: Path = None,
        municipalities_target_columns: list = None,
        municipalities_index_column: str = None,
        municipalities_column_remapping: dict = None
) -> Path:
    """Preprocessa e salva i dati geografici del censimento e, opzionalmente, i confini amministrativi.

    Args:
        census_shp_folder (Path): Cartella contenente i file shapefile del censimento.
        census_target_columns (list): Colonne da selezionare dai dati del censimento.
        census_tipo_loc_mapping (dict): Mappatura del tipo di località per il censimento.
        output_folder (Path): Cartella di output per salvare i risultati.
        census_layer_name (str): Nome del layer per il GeoPackage del censimento.
        census_column_remapping (dict, opzionale): Mappatura per rinominare le colonne del censimento. Default: None.
        regions_file_path (Path, opzionale): Percorso del file dei confini regionali. Default: None.
        regions_target_columns (list, opzionale): Colonne da selezionare dai dati regionali. Default: None.
        regions_index_column (str, opzionale): Colonna da usare come indice per i dati regionali. Default: None.
        regions_column_remapping (dict, opzionale): Mappatura per rinominare le colonne regionali. Default: None.
        provinces_file_path (Path, opzionale): Percorso del file dei confini provinciali. Default: None.
        provinces_target_columns (list, opzionale): Colonne da selezionare dai dati provinciali. Default: None.
        provinces_index_column (str, opzionale): Colonna da usare come indice per i dati provinciali. Default: None.
        provinces_column_remapping (dict, opzionale): Mappatura per rinominare le colonne provinciali. Default: None.
        municipalities_file_path (Path, opzionale): Percorso del file dei confini comunali. Default: None.
        municipalities_target_columns (list, opzionale): Colonne da selezionare dai dati comunali. Default: None.
        municipalities_index_column (str, opzionale): Colonna da usare come indice per i dati comunali. Default: None.
        municipalities_column_remapping (dict, opzionale): Mappatura per rinominare le colonne comunali. Default: None.

    Returns:
        Path: Il percorso della cartella di output con i dati elaborati.
    """
    census_year = census_layer_name[6:]
    logging.info(f"Anno del censimento rilevato: {census_year}")

    # Lettura e salvataggio dei confini regionali
    logging.info("Inizio elaborazione dei confini regionali")
    region = read_administrative_boundaries(
        file_path=regions_file_path,
        target_columns=regions_target_columns,
        index_column=regions_index_column,
        column_remapping=regions_column_remapping
    )

    # Lettura e salvataggio dei confini provinciali
    logging.info("Inizio elaborazione dei confini provinciali")
    province = read_administrative_boundaries(
        file_path=provinces_file_path,
        target_columns=provinces_target_columns,
        index_column=provinces_index_column,
        column_remapping=provinces_column_remapping
    )

    # Lettura e salvataggio dei confini comunali
    logging.info("Inizio elaborazione dei confini comunali")
    municipality = read_administrative_boundaries(
        file_path=municipalities_file_path,
        target_columns=municipalities_target_columns,
        index_column=municipalities_index_column,
        column_remapping=municipalities_column_remapping
    )
    municipality.reset_index(inplace=True)
    # Poichè i confini comunali 2021 non hanno la colonna 'COD_PROV' la aggiungo manualmente.
    # TODO https://github.com/MaxDragonheart/istatcelldata/issues/47
    logging.info("Poichè i confini comunali 2021 non hanno la colonna 'COD_PROV' la aggiungo manualmente. https://github.com/MaxDragonheart/istatcelldata/issues/47")
    if census_year == '2021':
        municipality['COD_PROV'] = municipality['PRO_COM_T'].str[:3]
        municipality['COD_PROV'] = municipality['COD_PROV'].astype(int)
        municipality.drop(columns=['PRO_COM_T'], inplace=True)

    # Aggiunta del dettaglio delle provincie ai comuni
    mun_prov = pd.merge(
        left=municipality,
        right=province,
        how='left',
        on='COD_PROV'
    )

    # Aggiunta del dettaglio delle regioni ai comuni
    mun_reg = pd.merge(
        left=mun_prov,
        right=region,
        how='left',
        on='COD_REG'
    )

    logging.info(f"Avvio del preprocessing dei dati del censimento dalla cartella {census_shp_folder}")
    # Lettura e salvataggio dei dati del censimento
    census_geodata = read_census(
        shp_folder=census_shp_folder,
        target_columns=census_target_columns,
        tipo_loc_mapping=census_tipo_loc_mapping,
        column_remapping=census_column_remapping,
    )
    census_geodata_full = pd.merge(
        left=census_geodata,
        right=mun_reg,
        how='left',
        on='PRO_COM'
    )

    gdf = gpd.GeoDataFrame(data=census_geodata_full, geometry=GEOMETRY_COLUMN_NAME, crs=census_geodata.crs)
    geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
    gdf.to_file(filename=str(geopackage_path), driver="GPKG", encoding=GLOBAL_ENCODING, layer=f"{YEAR_GEODATA_NAME}{census_year}")
    logging.info(f"Salvataggio del GeoPackage del censimento in {geopackage_path}")
    return geopackage_path
