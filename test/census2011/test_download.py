from pathlib import Path

from istatcelldata.census2011.download import DATA_LINK, YEAR, GEODATA_LINK, ADMIN_BOUNDARIES, \
    download_all_census_data_2011


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


def test_download_all_census_data_2011(tmp_path: Path):
    print("test_download_all_census_data_2011")
    download_all_census_data_2011(
        output_data_folder=tmp_path,
        data_url=DATA_LINK,
        geodata_url=GEODATA_LINK,
        boudaries_url=ADMIN_BOUNDARIES,
        census_year=YEAR,
        region_list=[2, 15]
    )

