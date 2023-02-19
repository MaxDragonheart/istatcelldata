from pathlib import Path

from census_istat.manage_data import read_csv
from test.generic import csv_data


def test_read_csv(tmp_path: Path):
    print('test_read_csv')
    read_csv(csv_path=csv_data)
