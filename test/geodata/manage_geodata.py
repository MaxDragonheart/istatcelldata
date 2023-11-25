from pathlib import Path

from geopandas import GeoDataFrame
from shapely import Polygon
import geopandas as gpd

from istatcelldata.geodata.manage_geodata import read_raw_geodata, read_raw_census_geodata, join_year_census, \
    read_geodata, polygon_bbox

test_file_path = Path('/home/max/Desktop/census_istat/preprocessing/census_2001/geodata/R18_01_WGS84/R18_01_WGS84.shp')
test_path = Path('/home/max/Desktop/census_istat/preprocessing/census_2001')

demo_data = Path.cwd().parent.parent.joinpath('demo_data').joinpath('demo_data.gpkg')


def test_read_geodata() -> None:
    print("test_read_geodata")
    data = read_geodata(input_data=demo_data, layer='com_napoli')

    assert isinstance(data, GeoDataFrame)


def test_read_raw_geodata(tmp_path: Path) -> None:
    print('test_read_raw_geodata')
    read_raw_geodata(
        data_path=test_file_path,
        year=2001,
    )


def test_read_raw_census_geodata(tmp_path: Path) -> None:
    print('test_read_raw_census_geodata')
    read_raw_census_geodata(
        data_path=test_path,
        year=2011,
        output_path=tmp_path
    )


def test_join_year_census(tmp_path: Path) -> None:
    print('test_join_year_census')
    join_year_census(
        data_path=test_path,
        year=2001,
        output_path=tmp_path,
        remove_processed=False,
        only_shared=True
    )


def test_polygon_bbox(tmp_path: Path) -> None:
    print("test_polygon_bbox")
    bounds = [(14.0, 40.0, 42.0, 15.0), 4326]

    data = polygon_bbox(
        coordinates_list=bounds[0],
        crs=bounds[1],
        output_path=tmp_path
    )

    assert isinstance(data, Polygon) or isinstance(data, Path)
