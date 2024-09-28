from pathlib import Path

from istatcelldata.config import DEMO_DATA_FOLDER
from istatcelldata.utils import check_encoding, csv_from_excel, census_folder, unzip_data, get_region


def test_check_encoding():
    print('test_check_encoding')
    data = check_encoding(data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.csv"))
    print(data)
    assert isinstance(data, str)


def test_csv_from_excel(tmp_path: Path):
    print('test_csv_from_excel')
    data = csv_from_excel(
        data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        output_path=tmp_path.joinpath('output.csv'),
        metadata=True
    )
    print(data)
    assert isinstance(data, Path)


def test_census_folder(tmp_path: Path):
    print('test_census_folder')
    data = census_folder(output_data_folder=tmp_path, year=1991)
    print(data)
    assert isinstance(data, Path)


def test_unzip_data(tmp_path: Path):
    print("test_unzip_data")
    data = unzip_data(
        input_data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.zip"),
        output_folder=tmp_path
    )
    print(data)
    assert isinstance(data, Path)


def test_get_region():
    print("test_get_region")
    data = get_region(
        #region_list=[3, 5]
    )
    print(data)
    assert isinstance(data, list)

