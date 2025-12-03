from pathlib import Path

import geopandas as gpd
import pandas as pd

from istatcelldata.config import DOWNLOAD_RAW_DATA, census_data
from istatcelldata.geodata import preprocess_geodata, read_administrative_boundaries, read_census

year = 2011

REGIONS_ROOT = census_data[year]['regions_root']
REGIONS_COLUMN = census_data[year]['regions_column']
REGIONS_COLUMN_REMAPPING = census_data[year].get('regions_column_remapping', None)
REGIONS_INDEX = census_data[year]['regions_index']
PROVINCES_ROOT = census_data[year]['provinces_root']
PROVINCES_COLUMN = census_data[year]['provinces_column']
PROVINCES_COLUMN_REMAPPING = census_data[year].get('provinces_column_remapping', None)
PROVINCES_INDEX = census_data[year]['provinces_index']
MUNICIPALITIES_ROOT = census_data[year]['municipalities_root']
MUNICIPALITIES_COLUMN = census_data[year]['municipalities_column']
MUNICIPALITIES_COLUMN_REMAPPING = census_data[year].get('municipalities_column_remapping', None)
MUNICIPALITIES_INDEX = census_data[year]['municipalities_index']
CENSUS_SHP_ROOT = census_data[year]['census_shp_root']
CENSUS_SHP_COLUMN = census_data[year]['census_shp_column']
CENSUS_SHP_COLUMN_REMAPPING = census_data[year].get('census_shp_column_remapping', None)
TIPO_LOC_MAPPING = census_data[year]['tipo_loc_mapping']


def test_read_regions(tmp_path: Path):
    print("test_read_regions")
    data = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_INDEX,
        output_folder=tmp_path,
        layer_name='test'
    )
    print(data)
    assert isinstance(data, pd.DataFrame) or isinstance(data, Path)


def test_read_provinces():
    print("test_read_provinces")
    data = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*PROVINCES_ROOT),
        target_columns=PROVINCES_COLUMN,
        index_column=PROVINCES_INDEX,
        column_remapping=PROVINCES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_read_municipalities():
    print("test_read_municipalities")
    data = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*MUNICIPALITIES_ROOT),
        target_columns=MUNICIPALITIES_COLUMN,
        index_column=MUNICIPALITIES_INDEX,
        column_remapping=MUNICIPALITIES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_read_census(tmp_path: Path):
    print("test_read_census")
    data = read_census(
        shp_folder=DOWNLOAD_RAW_DATA.joinpath(*CENSUS_SHP_ROOT),
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
        census_shp_folder=DOWNLOAD_RAW_DATA.joinpath(*CENSUS_SHP_ROOT),
        census_target_columns=CENSUS_SHP_COLUMN,
        census_tipo_loc_mapping=TIPO_LOC_MAPPING,
        census_layer_name=f"census{year}",
        census_column_remapping=CENSUS_SHP_COLUMN_REMAPPING,
        regions_file_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        regions_index_column=REGIONS_INDEX,
        provinces_file_path=DOWNLOAD_RAW_DATA.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        provinces_index_column=PROVINCES_INDEX,
        provinces_column_remapping=PROVINCES_COLUMN_REMAPPING,
        municipalities_file_path=DOWNLOAD_RAW_DATA.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
        municipalities_index_column=MUNICIPALITIES_INDEX,
        municipalities_column_remapping=MUNICIPALITIES_COLUMN_REMAPPING,
        output_folder=tmp_path,
        municipalities_code=[63049]
    )
    print(data)
    assert isinstance(data, Path)

