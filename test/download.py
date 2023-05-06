from pathlib import Path

from istatcelldata.download import download_census_data, download_census_geodata, download_administrative_boundaries, \
    download_all_census_data

target_year = 1991


def test_download_census_data(tmp_path: Path):
    print('test_download_census_data')
    download_census_data(output_data_folder=tmp_path, year=target_year)


def test_download_census_geodata(tmp_path: Path):
    print('test_download_census_geodata')
    download_census_geodata(
        output_data_folder=tmp_path,
        year=target_year,
        target_area=[12]
    )


def test_download_administrative_boundaries(tmp_path: Path):
    print('test_download_administrative_boundaries')
    download_administrative_boundaries(output_data_folder=tmp_path, year=target_year)


def test_download_all_census_data(tmp_path: Path):
    print('test_download_all_census_data')
    download_all_census_data(output_data_folder=tmp_path, year=target_year)
