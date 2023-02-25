from pathlib import Path

from census_istat.geodata.manage_geodata import read_geodata, read_census_geodata

test_file_path = Path('/home/max/Desktop/census_istat/preprocessing/census_1991/geodata/R01_91_WGS84/R01_91_WGS84.shp')
test_path = Path('/home/max/Desktop/census_istat/preprocessing/')


def test_read_geodata(tmp_path: Path) -> None:
    print('test_read_geodata')
    read_geodata(
        data_path=test_file_path,
        year=1991,
    )


def test_read_census_geodata(tmp_path: Path) -> None:
    print('test_read_census_geodata')
    read_census_geodata(
        data_path=test_path,
        year=2011,
    )