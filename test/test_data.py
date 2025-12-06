from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from istatcelldata.config import DOWNLOAD_RAW_DATA, census_data
from istatcelldata.data import preprocess_data

year = 1991

DATA_ROOT = census_data[year]["data_root"]
REGIONS_ROOT = census_data[year]["regions_root"]
REGIONS_COLUMN = census_data[year]["regions_column"]
PROVINCES_ROOT = census_data[year]["provinces_root"]
PROVINCES_COLUMN = census_data[year]["provinces_column"]
MUNICIPALITIES_ROOT = census_data[year]["municipalities_root"]
MUNICIPALITIES_COLUMN = census_data[year]["municipalities_column"]


def test_preprocess_data(tmp_path: Path):
    print("test_preprocess_data")
    data = preprocess_data(
        data_folder=DOWNLOAD_RAW_DATA.joinpath(*DATA_ROOT),
        add_administrative_informations=True,
        regions_data_path=DOWNLOAD_RAW_DATA.joinpath(*REGIONS_ROOT),
        regions_target_columns=REGIONS_COLUMN,
        provinces_data_path=DOWNLOAD_RAW_DATA.joinpath(*PROVINCES_ROOT),
        provinces_target_columns=PROVINCES_COLUMN,
        municipalities_data_path=DOWNLOAD_RAW_DATA.joinpath(*MUNICIPALITIES_ROOT),
        municipalities_target_columns=MUNICIPALITIES_COLUMN,
        # output_folder=tmp_path,
    )
    print(data)
    print(data["census_data"].columns)
    assert isinstance(data, dict)
    assert isinstance(data["census_data"], pd.DataFrame)
    assert isinstance(data["trace"], pd.DataFrame)


def test_preprocess_data_no_csv_files(tmp_path: Path):
    """Test preprocess_data raises ValueError when no CSV files are found."""
    empty_folder = tmp_path / "empty"
    empty_folder.mkdir()

    with pytest.raises(ValueError, match="No CSV files found"):
        preprocess_data(data_folder=empty_folder)


@patch("istatcelldata.data.tqdm", side_effect=lambda x, **kwargs: x)
@patch("istatcelldata.data.check_encoding")
@patch("pandas.read_csv")
def test_preprocess_data_with_output_folder(
    mock_read_csv, mock_check_encoding, mock_tqdm, tmp_path: Path
):
    """Test preprocess_data saves files when output_folder is specified."""
    # Setup mock data folder with CSV files
    data_folder = tmp_path / "data"
    data_folder.mkdir()

    # Create mock CSV files
    csv1 = data_folder / "data1.csv"
    csv2 = data_folder / "trace.csv"
    csv1.write_text("col1;col2\nval1;val2")
    csv2.write_text("field;description\ncol1;desc1")

    # Mock encoding detection
    mock_check_encoding.return_value = "utf-8"

    # Mock pandas DataFrames
    mock_data_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    mock_trace_df = pd.DataFrame({"field": ["col1"], "description": ["desc1"]})

    # Mock read_csv to return different DataFrames
    mock_read_csv.side_effect = [mock_data_df, mock_trace_df]

    # Create output folder
    output_folder = tmp_path / "output"
    output_folder.mkdir()

    # Call function with output_folder
    result = preprocess_data(
        data_folder=data_folder,
        output_folder=output_folder,
    )

    # Verify output folder is returned
    assert result == output_folder

    # Verify files were created
    census_file = output_folder / "census_data.csv"
    trace_file = output_folder / "census_trace.csv"
    assert census_file.exists()
    assert trace_file.exists()
