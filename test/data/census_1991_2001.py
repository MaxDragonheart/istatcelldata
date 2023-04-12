from pathlib import Path

from census_istat.data.census_1991_2001 import read_xls, remove_xls, census_trace, merge_data_1991_2001

test_dataset = Path('/home/max/Desktop/census_istat/output/census_2001/data/dati-cpa_2001\\R01_DatiCPA_2001.xls')
test_path = Path('/home/max/Desktop/census_istat/preprocessing/census_1991/data/Sezioni di Censimento')


def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    read_xls(
        file_path=test_dataset,
        census_code='sez2001',
        output_path=tmp_path,
        metadata=False
    )


def test_remove_xls(tmp_path: Path):
    print('test_remove_xls')
    remove_xls(
        folder_path=test_path,
        census_code='sez2001'
    )


def test_make_tracciato(tmp_path: Path):
    print('test_make_tracciato')
    census_trace(
        file_path=test_dataset,
        output_path=tmp_path,
    )


def test_merge_data_1991_2001(tmp_path: Path):
    print('test_merge_data_1991_2001')
    merge_data_1991_2001(
        csv_path=test_path,
        year=1991,
        output_path=test_path.parent,
    )
