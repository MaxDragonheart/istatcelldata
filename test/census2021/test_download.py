from pathlib import Path

from istatcelldata.census2011.download import download_administrative_boundaries, download_geodata
from istatcelldata.census2021.download import download_all_census_data_2021, download_data

year = 2021


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(output_data_folder=tmp_path, census_year=year)
    print(data)
    assert isinstance(data, Path)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(output_data_folder=tmp_path, census_year=year, region_list=[3, 15])
    print(data)
    assert isinstance(data, Path)


def test_download_administrative_boundaries(tmp_path: Path):
    print("test_download_administrative_boundaries")
    data = download_administrative_boundaries(
        output_data_folder=tmp_path,
        census_year=year,
    )
    print(data)
    assert isinstance(data, Path)


def test_download_all_census_data_2021(tmp_path: Path):
    print("test_download_all_census_data_2021")
    download_all_census_data_2021(
        output_data_folder=tmp_path,
        # region_list=[2, 15]
    )
