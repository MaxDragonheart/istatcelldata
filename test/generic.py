from pathlib import Path

from census_istat.config import main_path
from census_istat.generic import check_encoding, csv_from_excel, census_folder

csv_data = main_path.joinpath('tmp/csv/R03_indicatori_2011_sezioni.csv')
xls_data = main_path.joinpath('tmp/xls/dati-cpa_1991\R03_DatiCPA_1991.xls')


def test_check_encoding():
    print('test_check_encoding')
    check_encoding(data=xls_data)


def test_csv_from_excel(tmp_path: Path):
    print('test_csv_from_excel')
    csv_from_excel(
        data=xls_data,
        output_path=tmp_path.joinpath('output.csv')
    )


def test_census_folder(tmp_path: Path):
    print('test_census_folder')
    census_folder(output_data_folder=tmp_path)

