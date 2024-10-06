from pathlib import Path

import pandas as pd

from istatcelldata.census2001.config import REGIONS_ROOT, REGIONS_COLUMN, PROVINCES_ROOT, PROVINCES_COLUMN, \
    MUNICIPALITIES_ROOT, MUNICIPALITIES_COLUMN
from istatcelldata.census2011.config import REGIONS_COLUMN_REMAPPING, PROVINCES_COLUMN_REMAPPING, \
    MUNICIPALITIES_COLUMN_REMAPPING
from istatcelldata.geodata import read_administrative_boundaries

main_folder = Path("/home/max/Desktop/census/preprocessing")

def test_read_regions():
    print("test_read_regions")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_COLUMN[0],
        column_remapping=REGIONS_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


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
        index_column=MUNICIPALITIES_COLUMN[0],
        column_remapping=MUNICIPALITIES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_read_regions_geo(tmp_path: Path):
    print("test_read_regions_geo")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_regionali",
        column_remapping=REGIONS_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, Path)


def test_read_provinces_geo(tmp_path: Path):
    print("test_read_provinces_geo")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*PROVINCES_ROOT),
        target_columns=PROVINCES_COLUMN,
        index_column=PROVINCES_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_provinciali",
        column_remapping=PROVINCES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, Path)


def test_read_municipalities_geo(tmp_path: Path):
    print("test_read_municipalities_geo")
    data = read_administrative_boundaries(
        file_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        target_columns=MUNICIPALITIES_COLUMN,
        index_column=MUNICIPALITIES_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_comunali",
        column_remapping=MUNICIPALITIES_COLUMN_REMAPPING
    )
    print(data)
    assert isinstance(data, Path)


def test_make_admin_boundaries_gpkg(tmp_path: Path):
    print("test_make_admin_boundaries_gpkg")
    regions = read_administrative_boundaries(
        file_path=main_folder.joinpath(*REGIONS_ROOT),
        target_columns=REGIONS_COLUMN,
        index_column=REGIONS_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_regionali",
        column_remapping=REGIONS_COLUMN_REMAPPING
    )
    print(regions)
    provinces = read_administrative_boundaries(
        file_path=main_folder.joinpath(*PROVINCES_ROOT),
        target_columns=PROVINCES_COLUMN,
        index_column=PROVINCES_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_provinciali",
        column_remapping=PROVINCES_COLUMN_REMAPPING
    )
    print(provinces)
    municipalities = read_administrative_boundaries(
        file_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        target_columns=MUNICIPALITIES_COLUMN,
        index_column=MUNICIPALITIES_COLUMN[0],
        with_geometry=True,
        output_folder=tmp_path,
        layer_name="confini_comunali",
        column_remapping=MUNICIPALITIES_COLUMN_REMAPPING
    )
    print(municipalities)
