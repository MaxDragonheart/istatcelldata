from pathlib import Path

import pandas as pd
import geopandas as gpd

from istatcelldata.config import census_data
from istatcelldata.geodata import read_administrative_boundaries, read_census, preprocess_geodata

year = 1991

REGIONS_ROOT = census_data[year]['regions_root']
REGIONS_COLUMN = census_data[year]['regions_column']
PROVINCES_ROOT = census_data[year]['provinces_root']
PROVINCES_COLUMN = census_data[year]['provinces_column']
PROVINCES_COLUMN_REMAPPING = census_data[year].get('provinces_column_remapping', None)
MUNICIPALITIES_ROOT = census_data[year]['municipalities_root']
MUNICIPALITIES_COLUMN = census_data[year]['municipalities_column']
CENSUS_SHP_ROOT = census_data[year]['census_shp_root']
CENSUS_SHP_COLUMN = census_data[year]['census_shp_column']
CENSUS_SHP_COLUMN_REMAPPING = census_data[year].get('census_shp_column_remapping', None)
TIPO_LOC_MAPPING = census_data[year]['tipo_loc_mapping']

main_folder = Path("/home/max/Desktop/census/preprocessing")

def test_read_regions(tmp_path: Path):
    print("test_read_regions")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name='test'
    )
    print(data)
    assert isinstance(data, pd.DataFrame) or isinstance(data, Path)


def test_read_provinces():
    print("test_read_provinces")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*PROVINCES_ROOT),
        target_columns=PROVINCES_COLUMN,
        index_column=PROVINCES_COLUMN[0],
        column_remapping=PROVINCES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_read_municipalities():
    print("test_read_municipalities")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        target_columns=MUNICIPALITIES_COLUMN,
        index_column=MUNICIPALITIES_COLUMN[0]
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_read_census(tmp_path: Path):
    print("test_read_census")
    data = read_census(
        shp_folder=main_folder.joinpath(*CENSUS_SHP_ROOT),
        target_columns=CENSUS_SHP_COLUMN,
        tipo_loc_mapping=TIPO_LOC_MAPPING,
        column_remapping=CENSUS_SHP_COLUMN_REMAPPING,
        output_folder=tmp_path
    )
    print(data)
    assert isinstance(data, gpd.GeoDataFrame) or isinstance(data, Path)


def test_preprocess_geodata(tmp_path: Path):
    print("test_preprocess_geodata")
    data = preprocess_geodata(
        census_shp_folder=main_folder.joinpath(*CENSUS_SHP_ROOT),
        census_target_columns=CENSUS_SHP_COLUMN,
        census_tipo_loc_mapping=TIPO_LOC_MAPPING,
        census_layer_name="census2021",
        census_column_remapping=CENSUS_SHP_COLUMN_REMAPPING,
        regions=True,
        regions_file_path=main_folder.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        regions_index_column=REGIONS_COLUMN[0],
        provinces=True,
        provinces_file_path=main_folder.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        provinces_index_column=PROVINCES_COLUMN[0],
        provinces_column_remapping=PROVINCES_COLUMN_REMAPPING,
        municipalities=True,
        municipalities_file_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
        municipalities_index_column=MUNICIPALITIES_COLUMN[0],
        output_folder=tmp_path
    )
    print(data)
    assert isinstance(data, Path)

