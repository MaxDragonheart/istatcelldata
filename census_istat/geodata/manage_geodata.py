import logging
from pathlib import Path, PosixPath
from typing import Union

import geopandas as gpd
import pandas as pd

from geopandas import GeoDataFrame
from tqdm import tqdm

from census_istat.config import GEODATA_FOLDER, logger, console_handler

logger.addHandler(console_handler)


tipo_localita = {
    1991: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'case sparse'
    },
    2001: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'case sparse'
    },
    2011: {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'località produttiva',
        4: 'case sparse'
    }
}


def read_geodata(
        data_path: Union[Path, PosixPath],
        year: int,
) -> GeoDataFrame:
    """Read single geodata file.

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
        codice_localita = tipo_localita[year][row['TIPO_LOC']]
        data = [int(row[f'SEZ{year}']), codice_localita, row['geometry']]
        data_list.append(data)

    df = pd.DataFrame(data_list, columns=[f'sez{year}', 'tipo_loc', 'geometry'])
    df.sort_values(f'sez{year}', ascending=True, inplace=True)
    #df.set_index(f'sez{year}', inplace=True)
    gdf = gpd.GeoDataFrame(df, crs=read_data.crs)

    return gdf


def read_census_geodata(
        data_path: Union[Path, PosixPath],
        year: int,
        output_path: Union[Path, PosixPath] = None,
):
    main_path = data_path.joinpath(f'census_{year}').joinpath(GEODATA_FOLDER)
    files_list = list(main_path.rglob('*.shp'))

    geodata_list = []
    for path in tqdm(files_list):
        geodata = read_geodata(data_path=path, year=year)
        geodata_list.append(geodata)
        #break

    df = pd.concat(geodata_list)
    print(df.columns)
    print(df.dtypes)

    # if output_path is None:
    #     return ddf
    #
    # else:
    #     output_data = output_path.joinpath(f'data{year}.csv')
    #     logging.info(f'Save data to {output_data}')

