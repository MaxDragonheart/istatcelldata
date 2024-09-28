from pathlib import Path

from istatcelldata.census1991.download import download_data, download_geodata, download_administrative_boundaries
from istatcelldata.census2001.download import (download_all_census_data_2001, YEAR, DATA_LINK, GEODATA_LINK,
                                               ADMIN_BOUNDARIES)


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(
        output_data_folder=tmp_path,
        url=DATA_LINK,
        census_year=YEAR
    )
    print(data)
    assert isinstance(data, Path)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(
        output_data_folder=tmp_path,
        url=GEODATA_LINK,
        census_year=YEAR,
        region_list=[3]
    )
    print(data)
    assert isinstance(data, Path)


def test_download_administrative_boundaries(tmp_path: Path):
    print("test_download_administrative_boundaries")
    data = download_administrative_boundaries(
        output_data_folder=tmp_path,
        census_year=YEAR,
        url=ADMIN_BOUNDARIES
    )
    print(data)
    assert isinstance(data, Path)


def test_download_all_census_data_2001(tmp_path: Path):
    print("test_download_all_census_data_2001")
    download_all_census_data_2001(
        output_data_folder=tmp_path,
        data_url=DATA_LINK,
        geodata_url=GEODATA_LINK,
        boudaries_url=ADMIN_BOUNDARIES,
        census_year=YEAR,
        region_list=[2, 15]
    )

