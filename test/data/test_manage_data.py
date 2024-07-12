from pathlib import Path

from istatcelldata.data.manage_data import read_csv, merge_data, list_shared_columns
from test.test_generic import csv_data

test_path = Path('/home/max/Desktop/census_istat/preprocessing/census_2011/data/Sezioni di Censimento')


def test_read_csv(tmp_path: Path):
    print('test_read_csv')
    read_csv(csv_path=csv_data)


def test_merge_data(tmp_path: Path):
    print('test_merge_data')
    merge_data(
        csv_path=test_path,
        year=2011,
        output_path=test_path.parent,
    )


def test_list_shared_columns():
    print('test_list_shared_columns')
    list_shared_columns()
