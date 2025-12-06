from pathlib import Path

from istatcelldata.executor.download import download_census


def test_download_census(tmp_path: Path):
    print("test_download_census")
    download_census(years=[1991, 2021], output_data_folder=tmp_path, region_list=[1, 20])
