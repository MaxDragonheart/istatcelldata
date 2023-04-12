from pathlib import Path

from census_istat.download import download_census_data, download_census_geodata, download_administrative_boundaries, \
    download_all_census_data, _download_data


def test__download_data(tmp_path: Path):
    print('test__download_data')
    _download_data(
        data_link="https://www.istat.it/storage/cartografia/variabili-censuarie/dati-cpa_2001.zip",
        data_file_path_destination=tmp_path,
        data_folder=tmp_path,
        destination_folder=tmp_path
    )


def test_download_census_data(tmp_path: Path):
    print('test_download_census_data')
    download_census_data(output_data_folder=tmp_path, year=2001)


def test_download_census_geodata(tmp_path: Path):
    print('test_download_census_geodata')
    download_census_geodata(output_data_folder=tmp_path, year=1991)


def test_download_administrative_boundaries(tmp_path: Path):
    print('test_download_administrative_boundaries')
    download_administrative_boundaries(output_data_folder=tmp_path, year=1991)


def test_download_all_census_data(tmp_path: Path):
    print('test_download_all_census_data')
    download_all_census_data(output_data_folder=tmp_path, year=1991)
