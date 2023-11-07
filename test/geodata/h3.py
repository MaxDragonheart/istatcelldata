from pathlib import Path

from istatcelldata.geodata.manage_geodata import read_geodata

demo_data = Path.cwd().parent.parent.joinpath('demo_data').joinpath('demo_data.gpkg')
target_area = read_geodata(input_data=demo_data, layer='com_napoli')


def test_get_hexagons(tmp_path: Path) -> None:
    print("get_hexagons")
    print(target_area)

