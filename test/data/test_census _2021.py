from pathlib import Path

from istatcelldata.data.census_2021 import read_xlsx

def test_read_xlsx(tmp_path: Path):
    print("test_read_xlsx")
    data = read_xlsx(
        file_path=Path("/home/max/Desktop/census/census_2021/data/R01_indicatori_2021_sezioni.xlsx")

    )