from pathlib import Path

import pandas as pd

from istatcelldata.census1991.utils import read_xls, census_trace
from istatcelldata.config import DEMO_DATA_FOLDER


def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    data = read_xls(
        file_path=DEMO_DATA_FOLDER.joinpath("dati-cpa_1991\R05_DatiCPA_1991.xls"),
        output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


def test_census_trace(tmp_path: Path):
    print('test_census_trace')
    data = census_trace(
        file_path=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        #output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)
