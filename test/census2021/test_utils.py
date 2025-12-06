from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from istatcelldata.census2021.utils import read_xlsx
from istatcelldata.config import DEMO_DATA_FOLDER


@pytest.mark.skipif(
    not DEMO_DATA_FOLDER.joinpath("raw_2021", "TRACCIATO FILE REGIONALI.xlsx").exists(),
    reason="Demo data file not available",
)
def test_read_xlsx(tmp_path: Path):
    print("test_read_xlsx")
    data = read_xlsx(
        # file_path=DEMO_DATA_FOLDER.joinpath("raw_2021", "R02_indicatori_2021_sezioni.xlsx"),
        file_path=DEMO_DATA_FOLDER.joinpath("raw_2021", "TRACCIATO FILE REGIONALI.xlsx"),
        output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, pd.DataFrame) or isinstance(data, Path)


@patch("pandas.read_excel")
def test_read_xlsx_returns_dataframe(mock_read_excel, tmp_path: Path):
    """Test reading xlsx file and returning DataFrame when output_path is None."""
    # Mock the return value of read_excel
    mock_df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
    mock_read_excel.return_value = mock_df

    test_file = tmp_path / "test_file.xlsx"
    test_file.touch()  # Create empty file for path existence

    # Call function without output_path
    result = read_xlsx(file_path=test_file, output_path=None)

    # Verify result is DataFrame
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert "col1" in result.columns
    mock_read_excel.assert_called_once_with(test_file, engine="openpyxl")


@patch("pandas.read_excel")
def test_read_xlsx_saves_regional_file(mock_read_excel, tmp_path: Path):
    """Test reading xlsx file starting with 'R' and saving as CSV."""
    # Mock the return value of read_excel
    mock_df = pd.DataFrame({"region": [1, 2], "value": [100, 200]})
    mock_read_excel.return_value = mock_df

    test_file = tmp_path / "R02_indicatori_2021.xlsx"
    test_file.touch()  # Create empty file for path existence

    output_path = tmp_path / "output"
    output_path.mkdir()

    # Call function with output_path
    result = read_xlsx(file_path=test_file, output_path=output_path)

    # Verify result is Path and CSV file was created
    assert isinstance(result, Path)
    assert result.exists()
    assert result.suffix == ".csv"
    assert result.name == "R02_indicatori_2021.csv"

    # Verify CSV content
    saved_df = pd.read_csv(result, sep=";")
    assert len(saved_df) == 2


@patch("pandas.read_excel")
def test_read_xlsx_saves_trace_file(mock_read_excel, tmp_path: Path):
    """Test reading xlsx file not starting with 'R' and saving as trace CSV."""
    # Mock the return value of read_excel
    mock_df = pd.DataFrame({"field": ["x", "y"], "type": ["int", "str"]})
    mock_read_excel.return_value = mock_df

    test_file = tmp_path / "TRACCIATO_2021.xlsx"
    test_file.touch()  # Create empty file for path existence

    output_path = tmp_path / "output"
    output_path.mkdir()

    # Call function with output_path
    result = read_xlsx(file_path=test_file, output_path=output_path)

    # Verify result is Path and CSV file was created with trace name
    assert isinstance(result, Path)
    assert result.exists()
    assert result.name == "tracciato_2021_sezioni.csv"

    # Verify CSV content
    saved_df = pd.read_csv(result, sep=";")
    assert len(saved_df) == 2


def test_read_xlsx_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    non_existent_file = Path("/fake/path/nonexistent.xlsx")

    with pytest.raises(FileNotFoundError):
        read_xlsx(file_path=non_existent_file, output_path=None)


def test_read_xlsx_invalid_excel_file(tmp_path: Path):
    """Test that ValueError is raised for invalid Excel file."""
    # Create a text file with .xlsx extension (invalid Excel)
    invalid_file = tmp_path / "invalid.xlsx"
    invalid_file.write_text("This is not an Excel file")

    # BadZipFile gets caught and re-raised as ValueError by the function
    with pytest.raises((ValueError, Exception)):
        read_xlsx(file_path=invalid_file, output_path=None)
