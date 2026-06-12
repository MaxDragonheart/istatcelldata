from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from istatcelldata.census1991.process import add_administrative_info
from istatcelldata.config import census_data
from istatcelldata.utils import check_encoding

year = 1991

DATA_ROOT = census_data[year]["data_root"]
REGIONS_ROOT = census_data[year]["regions_root"]
REGIONS_COLUMN = census_data[year]["regions_column"]
PROVINCES_ROOT = census_data[year]["provinces_root"]
PROVINCES_COLUMN = census_data[year]["provinces_column"]
MUNICIPALITIES_ROOT = census_data[year]["municipalities_root"]
MUNICIPALITIES_COLUMN = census_data[year]["municipalities_column"]

main_folder = Path("/home/max/Desktop/census/preprocessing")


@pytest.mark.skipif(not main_folder.exists(), reason="External data directory not available")
def test_add_administrative_info():
    print("test_add_administrative_info")
    census_data_path = main_folder.joinpath(*DATA_ROOT)
    csv_list = sorted(list(census_data_path.glob("*.csv")))[0]
    encoding = check_encoding(data=csv_list)
    census_data_df = pd.read_csv(filepath_or_buffer=csv_list, sep=";", encoding=encoding)

    data = add_administrative_info(
        census_data=census_data_df,
        regions_data_path=main_folder.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        provinces_data_path=main_folder.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        municipalities_data_path=main_folder.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
    )
    print(data)
    assert isinstance(data, pd.DataFrame)


def test_add_administrative_info_handles_cod_prov_without_cod_pro(tmp_path: Path):
    """Test cleanup works when province data already uses COD_PROV."""
    census_data_df = pd.DataFrame({"PRO_COM": [1001], "POP_TOT": [12]})
    regions_columns = ["COD_REG", "DEN_REG"]
    provinces_columns = ["COD_PROV", "DEN_PROV", "SIGLA"]
    municipalities_columns = ["PRO_COM", "COMUNE", "COD_REG", "COD_PROV"]

    def fake_read_boundaries(file_path, target_columns, index_column):
        if target_columns == regions_columns:
            return pd.DataFrame(
                {"DEN_REG": ["Lazio"]},
                index=pd.Index([1], name="COD_REG"),
            )
        if target_columns == provinces_columns:
            return pd.DataFrame(
                {"DEN_PROV": ["Roma"], "SIGLA": ["RM"]},
                index=pd.Index([10], name="COD_PROV"),
            )
        if target_columns == municipalities_columns:
            return pd.DataFrame(
                {"COMUNE": ["Roma"], "COD_REG": [1], "COD_PROV": [10]},
                index=pd.Index([1001], name="PRO_COM"),
            )
        raise AssertionError(f"Unexpected target columns: {target_columns}")

    with patch(
        "istatcelldata.census1991.process.read_administrative_boundaries",
        side_effect=fake_read_boundaries,
    ):
        data = add_administrative_info(
            census_data=census_data_df,
            regions_data_path=tmp_path / "regions.shp",
            regions_target_columns=regions_columns,
            provinces_data_path=tmp_path / "provinces.shp",
            provinces_target_columns=provinces_columns,
            municipalities_data_path=tmp_path / "municipalities.shp",
            municipalities_target_columns=municipalities_columns,
        )

    assert "CODPRO" in data.columns
    assert "COD_PRO" not in data.columns
    assert "PRO_COM" not in data.columns
    assert data.loc[0, "CODPRO"] == 10
