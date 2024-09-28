from pathlib import Path

from istatcelldata.census2001.download import download_all_census_data_2001, DATA_LINK, GEODATA_LINK, ADMIN_BOUNDARIES, \
    YEAR


def test_download_all_census_data_2001(tmp_path: Path):
    print("test_download_all_census_data_2001")
    download_all_census_data_2001(
        output_data_folder=tmp_path,
        data_url=DATA_LINK,
        geodata_url=GEODATA_LINK,
        boudaries_url=ADMIN_BOUNDARIES,
        year=YEAR,
        region_list=[2, 15]
    )

