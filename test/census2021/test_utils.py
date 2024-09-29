from pathlib import Path

import pandas as pd

from istatcelldata.census2021.utils import read_xlsx
from istatcelldata.config import DEMO_DATA_FOLDER


def test_read_xlsx(tmp_path: Path):
    print("test_read_xlsx")
    data = read_xlsx(
        #file_path=DEMO_DATA_FOLDER.joinpath("raw_2021", "R02_indicatori_2021_sezioni.xlsx"),
        file_path=DEMO_DATA_FOLDER.joinpath("raw_2021", "TRACCIATO FILE REGIONALI.xlsx"),
        output_path=tmp_path
    )
    print(data)
    assert isinstance(data, pd.DataFrame) or isinstance(data, Path)