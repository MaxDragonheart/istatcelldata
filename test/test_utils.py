from pathlib import Path

import requests

from istatcelldata.config import DEMO_DATA_FOLDER
from istatcelldata.utils import check_encoding, csv_from_excel, census_folder, unzip_data, get_region, get_census_dictionary


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


def test_get_census_dictionary():
    print("test_get_census_dictionary")
    target_year = 2021
    data = get_census_dictionary(
        census_year=target_year,
        region_list=[3, 5]
    )

    for x, y in data[f"census{target_year}"].items():
        if isinstance(y, list):
            target_link = y[0]
        else:
            target_link = y

        try:
            response = requests.get(target_link, timeout=5)
            if response.status_code == 200:
                print(f"Il link è raggiungibile: {target_link}")
            else:
                print(f"Il link risponde, ma con codice {response.status_code}: {target_link}")
        except requests.RequestException:
            print(f"Il link NON è raggiungibile: {target_link}")

    assert isinstance(data, dict)

