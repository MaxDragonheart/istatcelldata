from pathlib import Path

from istatcelldata.processes import download_raw_data


def test_download_raw_data(tmp_path: Path):
    print('test_download_raw_data')
    download_raw_data(
        output_data_folder=tmp_path,
        census_year=[2011],
        target_area=[20]
    )
