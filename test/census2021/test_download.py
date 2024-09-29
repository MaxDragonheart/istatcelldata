from pathlib import Path

from istatcelldata.census2021.download import YEAR, download_data


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(
        output_data_folder=tmp_path,
        census_year=YEAR
    )
    print(data)
    assert isinstance(data, Path)
