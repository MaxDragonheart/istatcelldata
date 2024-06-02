from pathlib import Path

from istatcelldata.generic import check_encoding, csv_from_excel, census_folder

csv_data = Path.cwd().parent.joinpath('demo_data', 'R02_DatiCPA_1991.csv')
xls_data = Path.cwd().parent.joinpath('demo_data', 'R02_DatiCPA_1991.xls')


def test_check_encoding():
    print('test_check_encoding')
    data = check_encoding(data=csv_data)
    print(data)
    assert isinstance(data, str)


def test_csv_from_excel(tmp_path: Path):
    print('test_csv_from_excel')
    data = csv_from_excel(
        data=xls_data,
        output_path=tmp_path.joinpath('output.csv'),
        metadata=True
    )
    print(data)
    assert isinstance(data, Path)


def test_census_folder(tmp_path: Path):
    print('test_census_folder')
    data = census_folder(output_data_folder=tmp_path)
    print(data)
    assert isinstance(data, Path)
