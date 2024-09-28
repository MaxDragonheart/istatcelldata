import shutil
from pathlib import Path

import pandas as pd

from istatcelldata.config import DEMO_DATA_FOLDER
from istatcelldata.census1991.download import download_geodata, download_data, read_xls, census_trace, remove_xls


def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    data = read_xls(
        file_path=DEMO_DATA_FOLDER.joinpath("dati-cpa_1991\R05_DatiCPA_1991.xls"),
        output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


def test_census_trace(tmp_path: Path):
    print('test_census_trace')
    data = census_trace(
        file_path=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        #output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


def test_remove_xls(tmp_path: Path):
    print("test_remove_xls")
    data = DEMO_DATA_FOLDER.joinpath("dati-cpa_1991\R05_DatiCPA_1991.xls")

    shutil.copy(src=data, dst=tmp_path)

    remove_xls(folder_path=tmp_path, output_path=tmp_path)


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(
        output_data_folder=tmp_path,
    )
    print(data)
    assert isinstance(data, Path)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(
        output_data_folder=tmp_path,
        region_list=[3]
    )
    print(data)
    assert isinstance(data, Path)



