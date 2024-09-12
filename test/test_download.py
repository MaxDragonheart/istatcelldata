from pathlib import Path

from istatcelldata.download import download_census_data, download_census_geodata, download_administrative_boundaries, \
    download_all_census_data

target_year = 2021


def test_download_census_data(tmp_path: Path):
    print('test_download_census_data')
    data = download_census_data(output_data_folder=tmp_path, year=target_year)
    print(data)
    assert isinstance(data, Path)


def test_download_census_geodata(tmp_path: Path):
    print('test_download_census_geodata')
    data = download_census_geodata(
        output_data_folder=tmp_path,
        year=target_year,
        region_list=[15, 17]
    )
    print(data)
    assert isinstance(data, Path)


def test_download_administrative_boundaries(tmp_path: Path):
    print('test_download_administrative_boundaries')
    data = download_administrative_boundaries(output_data_folder=tmp_path, year=target_year)
    print(data)
    assert isinstance(data, Path)


def test_download_all_census_data(tmp_path: Path):
    print('test_download_all_census_data')
    download_all_census_data(output_data_folder=tmp_path, year=target_year)
