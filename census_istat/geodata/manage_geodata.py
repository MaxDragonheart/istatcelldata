import logging
import shutil
from pathlib import Path, PosixPath
from typing import Union

import geopandas as gpd
import pandas as pd

from geopandas import GeoDataFrame
from shapely.validation import make_valid
from tqdm import tqdm

from census_istat.config import GEODATA_FOLDER, logger, console_handler
from census_istat.data.manage_data import read_csv, list_shared_columns

logger.addHandler(console_handler)


TIPO_LOC = {
    1991: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'case sparse'
    },
    2001: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'località produttiva',
        4: 'case sparse'
    },
    2011: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'località produttiva',
        4: 'case sparse'
    }
}


def read_raw_geodata(
        data_path: Union[Path, PosixPath],
        year: int,
) -> GeoDataFrame:
    """Lettura del singolo geodato censuario grezzo e pulizia topologica delle geometrie.

    Args:
        data_path: Union[Path, PosixPath]
        year: int

    Returns:
        GeoDataFrame
    """
    read_data = gpd.read_file(data_path)
    read_data = read_data[[f'SEZ{year}', 'TIPO_LOC', 'geometry']]

    data_list = []
    for index, row in tqdm(read_data.iterrows()):
        if row[f'SEZ{year}'] != 0:
            census_cell_tipe = TIPO_LOC[year][row['TIPO_LOC']]
            census_cell_code = int(row[f'SEZ{year}'])
            census_cell_geometry = make_valid(row['geometry'])
            data = [census_cell_code, census_cell_tipe, census_cell_geometry]
            data_list.append(data)

    df = pd.DataFrame(data_list, columns=[f'sez{year}', 'tipo_loc', 'geometry'])
    df.sort_values(f'sez{year}', ascending=True, inplace=True)
    gdf = gpd.GeoDataFrame(df, crs=read_data.crs)

    return gdf


def read_raw_census_geodata(
        data_path: Union[Path, PosixPath],
        year: int,
        output_path: Union[Path, PosixPath] = None,
) -> Union[Path, PosixPath, GeoDataFrame]:
    """Lettura di tutti i geodati censuari grezzi per anno e
    creazione di un unico GeoDataFrame.

    Args:
        data_path: Union[Path, PosixPath]
        year: int
        output_path: Union[Path, PosixPath]

    Returns:
        Union[Path, PosixPath, GeoDataFrame]
    """
    main_path = data_path.joinpath(f'census_{year}').joinpath(GEODATA_FOLDER)
    files_list = list(main_path.rglob('*.shp'))

    # List all geodata
    logging.info('List all geodata')
    geodata_list = []
    data_crs = []
    for path in tqdm(files_list):
        geodata = read_raw_geodata(data_path=path, year=year)
        data_crs.append(geodata.crs)
        geodata_list.append(geodata)

    # Make DataFrame
    df = pd.concat(geodata_list)
    df.sort_values(f'sez{year}', ascending=True, inplace=True)

    # Make GeoDataFrame
    logging.info(f'Make GeoDataFrame for {year}')
    gdf = gpd.GeoDataFrame(df, crs=data_crs[0])
    gdf['area_mq'] = round(gdf.geometry.area, 0)

    if output_path is None:
        return gdf

    else:
        output_data = output_path.joinpath(f'geodata{year}.gpkg')
        logging.info(f'Save data to {output_data}')
        gdf.to_file(output_data, driver='GPKG')


def read_geodata(
        geodata_path: Union[Path, PosixPath],
) -> GeoDataFrame:
    """Lettura del geodato. La funzione incapsula la funzione di lettura di
    GeoPandas ma andrà successivamente sviuppata per rendere più rapida la
    lettura dei dati.


    Args:
        geodata_path: Union[Path, PosixPath]

    Returns:
        GeoDataFrame
    """
    logging.info('Read geodata')
    gdf = gpd.read_file(geodata_path)

    return gdf


def join_year_census(
        data_path: Union[Path, PosixPath],
        year: int,
        remove_processed: bool = False,
        only_shared: bool = True,
        output_path: Union[Path, PosixPath] = None,
) -> Union[Path, PosixPath, GeoDataFrame]:
    """Generazione di un unico GeoDataFrame che unisce dati e geodati censuari per l'anno selezionato.

    Args:
        data_path: Union[Path, PosixPath]
        year: int
        remove_processed: bool
        only_shared: bool
        output_path: Union[Path, PosixPath]

    Returns:
        Union[Path, PosixPath, GeoDataFrame]
    """
    # Read data
    data = read_csv(csv_path=data_path.joinpath(f'data{year}.csv'))

    if only_shared:
        # Filter shared columns
        shared_data_columns = list_shared_columns()
        administrative_columns = [f'sez{year}', 'codreg', 'regione', 'codpro', 'provincia', 'codcom', 'comune']
        shared_columns = administrative_columns + shared_data_columns
        data = data[shared_columns]

    # Read geodata
    geodata = read_geodata(geodata_path=data_path.joinpath(f'geodata{year}.gpkg'))

    # Join all
    logging.info('Join all')
    df = pd.merge(
        left=geodata,
        right=data,
        on=f'sez{year}',
        how='right'
    )
    df = df[df['comune'].notna()]
    df.set_index(f'sez{year}', inplace=True)
    gdf = gpd.GeoDataFrame(df, crs=geodata.crs)

    if remove_processed:
        logging.info(f'Delete data path {data_path}')
        shutil.rmtree(data_path)

    if output_path is None:
        return gdf

    else:
        output_data = output_path.joinpath(f'census_{year}.gpkg')
        logging.info(f'Save data to {output_data}')
        gdf.to_file(output_data, driver='GPKG')
