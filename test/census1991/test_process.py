from pathlib import Path

import pandas as pd

from istatcelldata.census1991.process import add_administrative_info
from istatcelldata.config import census_data
from istatcelldata.utils import check_encoding

year = 1991

DATA_ROOT = census_data[year]['data_root']
REGIONS_ROOT = census_data[year]['regions_root']
REGIONS_COLUMN = census_data[year]['regions_column']
PROVINCES_ROOT = census_data[year]['provinces_root']
PROVINCES_COLUMN = census_data[year]['provinces_column']
MUNICIPALITIES_ROOT = census_data[year]['municipalities_root']
MUNICIPALITIES_COLUMN = census_data[year]['municipalities_column']

main_folder = Path("/home/max/Desktop/census/preprocessing")


def test_add_administrative_info():
    print("test_add_administrative_info")
    census_data_path = main_folder.joinpath(*DATA_ROOT)
    csv_list = sorted(list(census_data_path.glob('*.csv')))[0]
    census_data_df = pd.read_csv(filepath_or_buffer=csv_list, sep=';', encoding=check_encoding(data=csv_list))

    data = add_administrative_info(
        census_data=census_data_df,
        regions_data_path=main_folder.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        provinces_data_path=main_folder.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        municipalities_data_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
    )
    print(data)
    assert isinstance(data, pd.DataFrame)
