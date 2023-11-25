from pathlib import Path

from geopandas import GeoDataFrame

from istatcelldata.geodata.h3_hexagons import get_h3_hexagons, select_hexagons
from istatcelldata.geodata.manage_geodata import read_geodata

demo_data = Path.cwd().parent.parent.joinpath('demo_data').joinpath('demo_data.gpkg')
target_area = read_geodata(input_data=demo_data, layer='com_napoli')
hex_lvl = 10


def test_get_h3_hexagons(tmp_path: Path) -> None:
    print("test_get_h3_hexagons")
    data = get_h3_hexagons(
        vector=target_area,
        hex_lvl=hex_lvl,
        output_path=tmp_path
    )

    assert isinstance(data, GeoDataFrame) or isinstance(data, Path)


def test_select_hexagons(tmp_path: Path) -> None:
    print("test_select_hexagons")
    data = select_hexagons(
        aoi=target_area,
        hex_lvl=hex_lvl,
        output_path=tmp_path
    )

    assert isinstance(data, Path) or isinstance(data, GeoDataFrame)
