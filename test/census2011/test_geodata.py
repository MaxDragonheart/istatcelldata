from pathlib import Path

import pandas as pd
import geopandas as gpd

from istatcelldata.config import census_data, DOWNLOAD_RAW_DATA
from istatcelldata.geodata import read_administrative_boundaries, read_census, preprocess_geodata

year = 2011

REGIONS_ROOT = census_data[year]['regions_root']
REGIONS_COLUMN = census_data[year]['regions_column']
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


def test_read_regions():
    print("test_read_regions")
    data = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_INDEX
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


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
        index_column=MUNICIPALITIES_INDEX
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_make_admin_boundaries_gpkg(tmp_path: Path):
    print("test_make_admin_boundaries_gpkg")
    regions = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_INDEX,
        output_folder=tmp_path,
        layer_name="confini_regionali"
    )
    print(regions)
    provinces = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*PROVINCES_ROOT),
        target_columns=PROVINCES_COLUMN,
        index_column=PROVINCES_INDEX,
        column_remapping=PROVINCES_COLUMN_REMAPPING,
        output_folder=tmp_path,
        layer_name="confini_provinciali"
    )
    print(provinces)
    municipalities = read_administrative_boundaries(
        file_path=DOWNLOAD_RAW_DATA.joinpath(*MUNICIPALITIES_ROOT),
        target_columns=MUNICIPALITIES_COLUMN,
        index_column=MUNICIPALITIES_INDEX,
        output_folder=tmp_path,
        layer_name="confini_comunali"
    )
    print(municipalities)


def test_read_census(tmp_path: Path):
    print("test_read_census")
    data = read_census(
        shp_folder=DOWNLOAD_RAW_DATA.joinpath(*CENSUS_SHP_ROOT),
        target_columns=CENSUS_SHP_COLUMN,
        tipo_loc_mapping=TIPO_LOC_MAPPING,
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
        regions_file_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        regions_index_column=REGIONS_INDEX,
        regions_column_remapping=R
        provinces_file_path=DOWNLOAD_RAW_DATA.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        provinces_column_remapping=PROVINCES_COLUMN_REMAPPING,
        provinces_index_column=PROVINCES_INDEX,
        municipalities_file_path=DOWNLOAD_RAW_DATA.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
        municipalities_index_column=MUNICIPALITIES_INDEX,
        output_folder=tmp_path
    )
    print(data)
    assert isinstance(data, Path)

