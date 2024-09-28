from pathlib import Path

from istatcelldata.census1991.download import download_geodata, download_data, download_administrative_boundaries, \
    download_all_census_data_1991, DATA_LINK, GEODATA_LINK, ADMIN_BOUNDARIES, YEAR


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(
        output_data_folder=tmp_path,
        url=DATA_LINK,
        year=YEAR
    )
    print(data)
    assert isinstance(data, Path)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(
        output_data_folder=tmp_path,
        url=GEODATA_LINK,
        year=YEAR,
        region_list=[3]
    )
    print(data)
    assert isinstance(data, Path)


def test_download_administrative_boundaries(tmp_path: Path):
    print("test_download_administrative_boundaries")
    data = download_administrative_boundaries(
        output_data_folder=tmp_path,
        year=YEAR,
        url=ADMIN_BOUNDARIES
    )
    print(data)
    assert isinstance(data, Path)


def test_download_all_census_data_1991(tmp_path: Path):
    print("test_download_all_census_data_1991")
    download_all_census_data_1991(
        output_data_folder=tmp_path,
        data_url=DATA_LINK,
        geodata_url=GEODATA_LINK,
        boudaries_url=ADMIN_BOUNDARIES,
        year=YEAR,
        region_list=[2, 15]
    )

