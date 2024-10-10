from pathlib import Path

import pandas as pd

from istatcelldata.config import census_data
from istatcelldata.data import preprocess_data

year = 1991

DATA_ROOT = census_data[year]['data_root']
REGIONS_ROOT = census_data[year]['regions_root']
REGIONS_COLUMN = census_data[year]['regions_column']
PROVINCES_ROOT = census_data[year]['provinces_root']
PROVINCES_COLUMN = census_data[year]['provinces_column']
MUNICIPALITIES_ROOT = census_data[year]['municipalities_root']
MUNICIPALITIES_COLUMN = census_data[year]['municipalities_column']

main_folder = Path("/home/max/Desktop/census/preprocessing")

def test_preprocess_data(tmp_path: Path):
    print("test_preprocess_data")
    data = preprocess_data(
        data_folder=main_folder.joinpath(*DATA_ROOT),
        add_administrative_informations=True,
        regions_data_path=main_folder.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        provinces_data_path=main_folder.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        municipalities_data_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
        #output_folder=tmp_path,
    )
    print(data)
    print(data['census_data'].columns)
    assert isinstance(data, dict)
    assert isinstance(data['census_data'], pd.DataFrame)
    assert isinstance(data['trace'], pd.DataFrame)
