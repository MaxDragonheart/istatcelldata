from pathlib import Path

import pandas as pd

from istatcelldata.config import DOWNLOAD_RAW_DATA, census_data
from istatcelldata.data import preprocess_data

year = 1991

DATA_ROOT = census_data[year]["data_root"]


def test_preprocess_data(tmp_path: Path):
    print("test_preprocess_data")
    data = preprocess_data(data_folder=DOWNLOAD_RAW_DATA.joinpath(*DATA_ROOT))
    print(data)
    assert isinstance(data, dict)
    assert isinstance(data["census_data"], pd.DataFrame)
    assert isinstance(data["trace"], pd.DataFrame)
