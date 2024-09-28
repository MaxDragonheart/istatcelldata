from pathlib import Path

import pandas as pd

from istatcelldata.config import DEMO_DATA_FOLDER
from istatcelldata.census1991.download import download_geodata, download_data, read_xls


def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    data = read_xls(
        file_path=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        #output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(
        output_data_folder=tmp_path,
        region_list=[3]
    )
    print(data)
    assert isinstance(data, Path)


def test_download_data(tmp_path: Path):
    print("test_download_geodata")
    data = download_data(
        output_data_folder=tmp_path,
    )
    # print(data)
    # assert isinstance(data, Path)
