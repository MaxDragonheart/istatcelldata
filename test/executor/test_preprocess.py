from pathlib import Path

from istatcelldata.config import DOWNLOAD_RAW_DATA
from istatcelldata.executor.preprocess import preprocess_census


def test_preprocess_census(tmp_path: Path):
    print("test_preprocess_census")
    data = preprocess_census(
        processed_data_folder=DOWNLOAD_RAW_DATA,
        years=[2021],
        output_data_folder=tmp_path
        #delete_download_folder=True
    )
    print(data)
    assert isinstance(data, Path)