from pathlib import Path

from census_istat.geodata.manage_geodata import read_raw_geodata, read_raw_census_geodata, join_year_census

test_file_path = Path('/home/max/Desktop/census_istat/preprocessing/census_2001/geodata/R18_01_WGS84/R18_01_WGS84.shp')
test_path = Path('/home/max/Desktop/census_istat/preprocessing/')


def test_read_raw_geodata(tmp_path: Path) -> None:
    print('test_read_raw_geodata')
    read_raw_geodata(
        data_path=test_file_path,
        year=2001,
    )


def test_read_raw_census_geodata(tmp_path: Path) -> None:
    print('test_read_raw_census_geodata')
    read_raw_census_geodata(
        data_path=test_path,
        year=2011,
        output_path=tmp_path
    )


def test_join_year_census(tmp_path: Path) -> None:
    print('test_join_year_census')
    join_year_census(
        data_path=test_path,
        year=1991,
        output_path=tmp_path,
        remove_processed=False
    )
