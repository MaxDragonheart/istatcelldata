from pathlib import Path

from istatcelldata.data.census_1991_2001 import read_xls, remove_xls, census_trace, merge_data_1991_2001

test_path = Path("/home/max/Desktop/preprocessing/census_2001/data")
sample_xls = test_path.joinpath("dati-cpa_2001\\R01_DatiCPA_2001.xls")


def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    read_xls(
        file_path=sample_xls,
        census_code='sez2001',
        output_path=tmp_path,
        metadata=False
    )


def test_remove_xls(tmp_path: Path):
    print('test_remove_xls')
    remove_xls(
        folder_path=test_path,
        output_path=tmp_path,
        census_code='sez2001'
    )


def test_make_tracciato(tmp_path: Path):
    print('test_make_tracciato')
    census_trace(
        file_path=sample_xls,
        output_path=tmp_path,
    )


def test_merge_data_1991_2001(tmp_path: Path):
    print('test_merge_data_1991_2001')
    merge_data_1991_2001(
        csv_path=test_path,
        year=1991,
        output_path=test_path.parent,
    )
