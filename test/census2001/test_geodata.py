from pathlib import Path

import pandas as pd

from istatcelldata.census2001.config import REGIONS_ROOT, REGIONS_COLUMN, PROVINCES_ROOT, PROVINCES_COLUMN
from istatcelldata.geodata import read_major_boundaries

main_folder = Path("/home/max/Desktop/census/preprocessing")
# boundaries = main_folder.joinpath(*REGIONS_ROOT)
# target_columns = REGIONS_COLUMN

boundaries = main_folder.joinpath(*PROVINCES_ROOT)
target_columns = PROVINCES_COLUMN


def test_read_major_boundaries():
    print("test_read_major_boundaries")
    data = read_major_boundaries(
        file_path=boundaries,
        target_columns=target_columns,
        index_column=target_columns[0]
    )
    print(data)
    assert isinstance(data, pd.DataFrame)
