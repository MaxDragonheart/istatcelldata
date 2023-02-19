from pathlib import Path

from census_istat.download import download_census_data


def test_download_census_data(tmp_path: Path):
    print('test_download_census_data')
    download_census_data(output_data_folder=tmp_path)
