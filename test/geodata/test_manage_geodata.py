from pathlib import Path

from geopandas import GeoDataFrame

from istatcelldata.geodata.manage_geodata import read_raw_geodata, read_raw_census_geodata, join_year_census

demo_data = Path.cwd().parent.parent.joinpath('demo_data')
test_file_path = demo_data.joinpath('census_2011', 'geodata', 'R14_11_WGS84', 'R14_11_WGS84.shp')
test_path = test_file_path.parent.parent.parent.parent


def test_read_raw_geodata(tmp_path: Path) -> None:
    print('test_read_raw_geodata')
    data = read_raw_geodata(
        data_path=test_file_path,
        year=2011,
    )
    print(data)
    assert isinstance(data, GeoDataFrame)


def test_read_raw_census_geodata(tmp_path: Path) -> None:
    print('test_read_raw_census_geodata')
    data = read_raw_census_geodata(
        data_path=test_path,
        year=2011,
        output_path=tmp_path
    )
    print(data)
    assert isinstance(data, GeoDataFrame) or isinstance(data, Path)


def test_join_year_census(tmp_path: Path) -> None:
    print('test_join_year_census')
    join_year_census(
        data_path=test_path,
        year=2011,
        output_path=tmp_path,
        remove_processed=False,
        only_shared=False
    )
