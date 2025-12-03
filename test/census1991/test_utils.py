from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from istatcelldata.census1991.utils import census_trace, read_xls
from istatcelldata.config import DEMO_DATA_FOLDER


@pytest.mark.skip(reason="Column name mismatch in demo data - needs investigation")
def test_read_xls(tmp_path: Path):
    print('test_read_xls')
    data = read_xls(
        file_path=DEMO_DATA_FOLDER.joinpath(r"dati-cpa_1991\R05_DatiCPA_1991.xls"),
        census_code='SEZ',
        output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


def test_census_trace(tmp_path: Path):
    print('test_census_trace')
    data = census_trace(
        file_path=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        year=1991,
        #output_path=tmp_path,
    )
    print(data)
    assert isinstance(data, Path) or isinstance(data, pd.DataFrame)


@patch('istatcelldata.census1991.utils.tqdm', side_effect=lambda x, **kwargs: x)
@patch('xlrd.open_workbook')
def test_read_xls_returns_dataframe(mock_open_workbook, mock_tqdm, tmp_path: Path):
    """Test reading xls file and returning DataFrame when output_path is None."""
    # Create mock workbook and sheet
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    # Setup mock data - use a callable to handle multiple row_values calls
    rows_data = [
        ['SEZ', 'COL1', 'COL2'],  # Header row
        [1001, 10, 20],  # Data row 1
        [1002, 30, 40],  # Data row 2
    ]

    def get_row(row_id):
        return rows_data[row_id]

    mock_workbook.sheet_names.return_value = ['Sheet1']
    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 3
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "test_file.xls"
    test_file.touch()

    # Call function without output_path
    result = read_xls(file_path=test_file, census_code='sez', output_path=None)

    # Verify result is DataFrame
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert 'col1' in result.columns
    assert 'col2' in result.columns
    assert result.index.name == 'sez'


@patch('istatcelldata.census1991.utils.tqdm', side_effect=lambda x, **kwargs: x)
@patch('xlrd.open_workbook')
def test_read_xls_saves_csv(mock_open_workbook, mock_tqdm, tmp_path: Path):
    """Test reading xls file and saving as CSV when output_path is provided."""
    # Create mock workbook and sheet
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    # Setup mock data - use a callable to handle multiple row_values calls
    rows_data = [
        ['SEZ', 'POPOLAZIONE'],  # Header row
        [1001, 5000],  # Data row
    ]

    def get_row(row_id):
        return rows_data[row_id]

    mock_workbook.sheet_names.return_value = ['Sheet1']
    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 2
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "R05\\test_data.xls"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    output_path = tmp_path / "output"
    output_path.mkdir()

    # Call function with output_path
    result = read_xls(file_path=test_file, census_code='sez', output_path=output_path)

    # Verify result is Path and CSV file was created
    assert isinstance(result, Path)
    assert result.exists()
    assert result.suffix == '.csv'

    # Verify CSV content
    saved_df = pd.read_csv(result, sep=';', index_col=0)
    assert len(saved_df) == 1


@patch('istatcelldata.census1991.utils.tqdm', side_effect=lambda x, **kwargs: x)
@patch('xlrd.open_workbook')
def test_read_xls_ignores_metadati_sheet(mock_open_workbook, mock_tqdm, tmp_path: Path):
    """Test that read_xls ignores 'Metadati' sheet and uses first data sheet."""
    # Create mock workbook and sheet
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    # Setup mock data with Metadati sheet - use callable
    rows_data = [
        ['SEZ', 'VALUE'],
        [1001, 100],
    ]

    def get_row(row_id):
        return rows_data[row_id]

    mock_workbook.sheet_names.return_value = ['Metadati', 'Dati']
    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 2
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "test_file.xls"
    test_file.touch()

    # Call function
    result = read_xls(file_path=test_file, census_code='sez', output_path=None)

    # Verify that sheet_by_name was called with 'Dati' not 'Metadati'
    mock_workbook.sheet_by_name.assert_called_with('Dati')
    assert isinstance(result, pd.DataFrame)


def test_read_xls_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    non_existent_file = Path("/fake/path/nonexistent.xls")

    with pytest.raises(FileNotFoundError):
        read_xls(file_path=non_existent_file, census_code='sez', output_path=None)


@patch('xlrd.open_workbook')
def test_census_trace_returns_dataframe(mock_open_workbook, tmp_path: Path):
    """Test census_trace returns DataFrame when output_path is None."""
    # Create mock workbook and sheet
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    # Setup mock metadata sheet (first 7 rows are skipped, then header, then data)
    rows_data = [
        ['Info', 'Value'],  # Row 0 (skipped)
        ['Info', 'Value'],  # Row 1 (skipped)
        ['Info', 'Value'],  # Row 2 (skipped)
        ['Info', 'Value'],  # Row 3 (skipped)
        ['Info', 'Value'],  # Row 4 (skipped)
        ['Info', 'Value'],  # Row 5 (skipped)
        ['Info', 'Value'],  # Row 6 (skipped)
        ['NOME CAMPO', 'DESCRIZIONE'],  # Row 7 (header)
        ['SEZ', 'Codice sezione'],  # Row 8 (data)
        ['POP', 'Popolazione totale'],  # Row 9 (data)
    ]

    def get_row(row_id):
        return [rows_data[row_id][0], rows_data[row_id][1]]

    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 10
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "test_file.xls"
    test_file.touch()

    # Call function without output_path
    result = census_trace(file_path=test_file, year=1991, output_path=None)

    # Verify result is DataFrame
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert result.index.name == 'NOME CAMPO'
    assert 'DESCRIZIONE' in result.columns


@patch('xlrd.open_workbook')
def test_census_trace_saves_csv(mock_open_workbook, tmp_path: Path):
    """Test census_trace saves CSV when output_path is provided."""
    # Create mock workbook and sheet
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    # Setup mock metadata sheet - use callable
    rows_data = [
        ['', ''], ['', ''], ['', ''], ['', ''], ['', ''], ['', ''], ['', ''],
        ['NOME CAMPO', 'DESCRIZIONE'],
        ['SEZ', 'Codice sezione'],
    ]

    def get_row(row_id):
        return [rows_data[row_id][0], rows_data[row_id][1]]

    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 9
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "test_file.xls"
    test_file.touch()

    output_path = tmp_path / "output"
    output_path.mkdir()

    # Call function with output_path
    result = census_trace(file_path=test_file, year=1991, output_path=output_path)

    # Verify result is Path and CSV file was created
    assert isinstance(result, Path)
    assert result.exists()
    assert result.name == 'tracciato_1991_sezioni.csv'

    # Verify CSV content
    saved_df = pd.read_csv(result, sep=';', index_col=0)
    assert len(saved_df) == 1


def test_census_trace_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    non_existent_file = Path("/fake/path/nonexistent.xls")

    with pytest.raises(FileNotFoundError):
        census_trace(file_path=non_existent_file, year=1991, output_path=None)
