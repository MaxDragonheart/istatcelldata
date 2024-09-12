from pathlib import Path

from istatcelldata.download import download_census_data, download_census_geodata, download_administrative_boundaries, \
    download_all_census_data, download_data_core
from istatcelldata.generic import census_folder

target_year = 2021
target_region = 15

data_link_2021 = "https://esploradati.censimentopopolazione.istat.it/databrowser/DWL/PERMPOP/SUBCOM/Dati_regionali_2021.zip"


def test_download_data_core(tmp_path: Path):
    print('test_download_data_core')

    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=tmp_path, year=target_year)

    # Make data folder
    data_folder = destination_folder.joinpath('data')
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    data_file_name = Path(data_link_2021).stem + Path(data_link_2021).suffix
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    data = download_data_core(
        data_link=data_link_2021,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )
    print(data)
    assert isinstance(data, Path)


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
