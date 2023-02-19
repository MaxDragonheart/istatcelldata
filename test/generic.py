from census_istat.config import main_path
from census_istat.generic import check_encoding


csv_data = main_path.joinpath('tmp/csv/R03_indicatori_2011_sezioni.csv')
xls_data = main_path.joinpath('tmp/xls/dati-cpa_1991\R03_DatiCPA_1991.xls')


def test_check_encoding():
    print('test_check_encoding')
    check_encoding(data=xls_data)
