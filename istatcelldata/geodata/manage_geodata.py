import logging
import shutil
from pathlib import Path
from typing import Union, Any, List

import geopandas as gpd
import pandas as pd

from geopandas import GeoDataFrame
from shapely import Polygon, MultiPolygon
from shapely.validation import make_valid
from tqdm import tqdm

from istatcelldata.config import GEODATA_FOLDER, logger, console_handler
from istatcelldata.data.manage_data import read_csv, list_shared_columns

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


def read_geodata(
        input_data: Union[str, Path],
        layer: str = None,
        bbox: Any = None,
        mask: Any = None,
        rows: Any = None,
) -> GeoDataFrame:
    """Read vector data

    Args:
        input_data: Union[str, Path]
        layer: str
        bbox: Any
        mask: Any
        rows: Any

    Returns:
        GeoDataFrame
    """
    if isinstance(input_data, Path) or isinstance(input_data, str):
        # TODO Waiting for solution
        # https://gis.stackexchange.com/questions/435156/geopandas-doesnt-read-fid-column-from-geopackage
        # https://github.com/geopandas/geopandas/issues/1035
        data = gpd.read_file(
            input_data,
            engine='pyogrio',
            fid_as_index=True,
            layer=layer,
            bbox=bbox,
            mask=mask,
            rows=rows
        )

    else:
        raise Exception('Not accepted file format. Format must be `Path` or `str`')

    return data


def read_raw_geodata(
        data_path: Path,
        year: int,
) -> GeoDataFrame:
    """Lettura del singolo geodato censuario grezzo e pulizia topologica delle geometrie.

    Args:
        data_path: Path
        year: int

    Returns:
        GeoDataFrame
    """
    read_data = read_geodata(data_path)
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
        data_path: Path,
        year: int,
        output_path: Path = None,
) -> Union[Path, GeoDataFrame]:
    """Lettura di tutti i geodati censuari grezzi per anno e
    creazione di un unico GeoDataFrame.

    Args:
        data_path: Path
        year: int
        output_path: Path

    Returns:
        Union[Path, GeoDataFrame]
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


def join_year_census(
        data_path: Path,
        year: int,
        remove_processed: bool = False,
        only_shared: bool = True,
        output_path: Path = None,
) -> Union[Path, GeoDataFrame]:
    """Generazione di un unico GeoDataFrame che unisce dati e geodati censuari per l'anno selezionato.

    Args:
        data_path: Path
        year: int
        remove_processed: bool
        only_shared: bool
        output_path: Path

    Returns:
        Union[Path, GeoDataFrame]
    """
    # Read data
    data = read_csv(csv_path=data_path.joinpath(f'data{year}.csv'))

    if only_shared:
        # Filter shared columns
        shared_data_columns = list_shared_columns()
        administrative_columns = ['codreg', 'regione', 'codpro', 'provincia', 'codcom', 'comune', 'procom', f'sez{year}']
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


def polygon_bbox(
        coordinates_list: List,
        crs: Union[str, int] = None,
        output_path: Path = None
) -> Union[Polygon, Path]:
    """Make polygon bbox from list of coordinates.

    Args:
        coordinates_list: List
        crs: Union[str, int]
        output_path: Path

    Returns:
        Polygon

    Raises:
        The list must contain 4 objects. Your list has {len(coordinates_list)} objects.
    """
    if len(coordinates_list) == 4:
        shape = Polygon(
            [
                (coordinates_list[0], coordinates_list[3]),
                (coordinates_list[2], coordinates_list[3]),
                (coordinates_list[2], coordinates_list[1]),
                (coordinates_list[0], coordinates_list[1]),
                (coordinates_list[0], coordinates_list[3]),
            ]
        )

        if output_path is None:
            return shape
        else:
            gdf = gpd.GeoDataFrame(index=[0], geometry=[shape], crs=crs)
            file_path = output_path.joinpath("bbox.gpkg")
            gdf.to_file(
                file_path,
                layer="bbox",
                driver="GPKG"
            )
            return file_path
    else:
        raise Exception(f"The list must contain 4 objects. Your list has {len(coordinates_list)} objects.")
