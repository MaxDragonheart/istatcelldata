import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
import xlrd

from istatcelldata.config import DEMO_DATA_FOLDER
from istatcelldata.utils import (
    census_folder,
    check_encoding,
    csv_from_excel,
    get_census_dictionary,
    get_region,
    remove_files,
    unzip_data,
)


def test_check_encoding():
    print('test_check_encoding')
    data = check_encoding(data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.csv"))
    print(data)
    assert isinstance(data, str)


@patch('chardet.detect')
def test_check_encoding_ascii_to_latin1(mock_detect, tmp_path: Path):
    """Test that ascii encoding is converted to latin1."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content")

    # Mock chardet to return ascii
    mock_detect.return_value = {'encoding': 'ascii'}

    result = check_encoding(test_file)

    # Verify ascii was converted to latin1
    assert result == 'latin1'


@patch('chardet.detect')
def test_check_encoding_utf8(mock_detect, tmp_path: Path):
    """Test that utf-8 encoding is returned as-is."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"test content")

    # Mock chardet to return utf-8
    mock_detect.return_value = {'encoding': 'utf-8'}

    result = check_encoding(test_file)

    # Verify utf-8 is unchanged
    assert result == 'utf-8'


def test_csv_from_excel(tmp_path: Path):
    print('test_csv_from_excel')
    data = csv_from_excel(
        data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.xls"),
        output_path=tmp_path.joinpath('output.csv'),
        metadata=True
    )
    print(data)
    assert isinstance(data, Path)


def test_census_folder(tmp_path: Path):
    print('test_census_folder')
    data = census_folder(output_data_folder=tmp_path, year=1991)
    print(data)
    assert isinstance(data, Path)


def test_unzip_data(tmp_path: Path):
    print("test_unzip_data")
    data = unzip_data(
        input_data=DEMO_DATA_FOLDER.joinpath("R02_DatiCPA_1991.zip"),
        output_folder=tmp_path
    )
    print(data)
    assert isinstance(data, Path)


def test_get_region():
    print("test_get_region")
    data = get_region(
        #region_list=[3, 5]
    )
    print(data)
    assert isinstance(data, list)


def test_get_census_dictionary():
    print("test_get_census_dictionary")
    target_year = 2021
    data = get_census_dictionary(
        census_year=target_year,
        region_list=[3, 5]
    )

    for x, y in data[f"census{target_year}"].items():
        if isinstance(y, list):
            target_link = y[0]
        else:
            target_link = y

        try:
            response = requests.get(target_link, timeout=5)
            if response.status_code == 200:
                print(f"Il link è raggiungibile: {target_link}")
            else:
                print(f"Il link risponde, ma con codice {response.status_code}: {target_link}")
        except requests.RequestException:
            print(f"Il link NON è raggiungibile: {target_link}")

    assert isinstance(data, dict)


@patch('istatcelldata.utils.tqdm', side_effect=lambda x, **kwargs: x)
@patch('xlrd.open_workbook')
def test_csv_from_excel_no_metadata(mock_open_workbook, mock_tqdm, tmp_path: Path):
    """Test csv_from_excel with metadata=False and Metadati sheet present."""
    mock_workbook = MagicMock()
    mock_sheet = MagicMock()

    rows_data = [
        ['Header1', 'Header2'],
        ['Data1', 'Data2']
    ]

    def get_row(row_id):
        return rows_data[row_id]

    # Simulate sheet_names with Metadati present
    mock_workbook.sheet_names.return_value = ['Metadati', 'DatiSheet']
    mock_workbook.sheet_by_name.return_value = mock_sheet
    mock_sheet.nrows = 2
    mock_sheet.row_values.side_effect = get_row

    mock_open_workbook.return_value = mock_workbook

    test_file = tmp_path / "test.xls"
    test_file.touch()
    output_file = tmp_path / "output.csv"

    result = csv_from_excel(data=test_file, output_path=output_file, metadata=False)

    # Verify sheet_by_name was called with 'DatiSheet' not 'Metadati'
    mock_workbook.sheet_by_name.assert_called_with('DatiSheet')
    assert result == output_file
    assert output_file.exists()


def test_csv_from_excel_file_not_found(tmp_path: Path):
    """Test csv_from_excel raises FileNotFoundError for non-existent file."""
    non_existent_file = tmp_path / "non_existent.xls"
    output_file = tmp_path / "output.csv"

    with pytest.raises(FileNotFoundError):
        csv_from_excel(data=non_existent_file, output_path=output_file)


@patch('xlrd.open_workbook')
def test_csv_from_excel_xlrd_error(mock_open_workbook, tmp_path: Path):
    """Test csv_from_excel handles XLRDError."""
    mock_open_workbook.side_effect = xlrd.XLRDError("Invalid XLS file")

    test_file = tmp_path / "invalid.xls"
    test_file.touch()
    output_file = tmp_path / "output.csv"

    with pytest.raises(xlrd.XLRDError):
        csv_from_excel(data=test_file, output_path=output_file)


def test_census_folder_creates_directory(tmp_path: Path):
    """Test census_folder creates proper directory structure."""
    result = census_folder(output_data_folder=tmp_path, year=2011)

    expected_path = tmp_path / "census_2011"
    assert result == expected_path
    assert result.exists()
    assert result.is_dir()


def test_unzip_data_file_not_found(tmp_path: Path):
    """Test unzip_data raises FileNotFoundError for non-existent ZIP."""
    non_existent_zip = tmp_path / "non_existent.zip"
    output_folder = tmp_path / "output"

    with pytest.raises(FileNotFoundError):
        unzip_data(input_data=non_existent_zip, output_folder=output_folder)


def test_unzip_data_bad_zip_file(tmp_path: Path):
    """Test unzip_data raises BadZipFile for invalid ZIP."""
    invalid_zip = tmp_path / "invalid.zip"
    invalid_zip.write_text("This is not a ZIP file")
    output_folder = tmp_path / "output"

    with pytest.raises(zipfile.BadZipFile):
        unzip_data(input_data=invalid_zip, output_folder=output_folder)


def test_get_region_with_list():
    """Test get_region returns provided list."""
    regions = get_region(region_list=[1, 5, 10])

    assert regions == [1, 5, 10]


def test_get_region_empty_list():
    """Test get_region returns all 20 regions when list is empty."""
    regions = get_region(region_list=[])

    assert regions == list(range(1, 21))
    assert len(regions) == 20


def test_get_census_dictionary_1991():
    """Test get_census_dictionary for year 1991."""
    result = get_census_dictionary(census_year=1991, region_list=[1, 2])

    assert 'census1991' in result
    assert 'data_url' in result['census1991']
    assert 'geodata_urls' in result['census1991']
    assert 'admin_boundaries_url' in result['census1991']
    assert 'census_code' in result['census1991']

    # Verify census_code for 1991
    assert result['census1991']['census_code'] == 'sez1991'

    # Verify geodata URLs format for 1991
    assert len(result['census1991']['geodata_urls']) == 2
    assert 'R01_91_WGS84.zip' in result['census1991']['geodata_urls'][0]
    assert 'WGS_84_UTM/1991' in result['census1991']['geodata_urls'][0]


def test_get_census_dictionary_2001():
    """Test get_census_dictionary for year 2001."""
    result = get_census_dictionary(census_year=2001, region_list=[3])

    assert 'census2001' in result
    assert result['census2001']['census_code'] == 'sez2001'

    # Verify geodata URLs format for 2001
    assert 'R03_01_WGS84.zip' in result['census2001']['geodata_urls'][0]
    assert 'WGS_84_UTM/2001' in result['census2001']['geodata_urls'][0]


def test_get_census_dictionary_2011():
    """Test get_census_dictionary for year 2011."""
    result = get_census_dictionary(census_year=2011, region_list=[5])

    assert 'census2011' in result
    assert result['census2011']['census_code'] == 'sez2011'

    # Verify geodata URLs format for 2011
    assert 'R05_11_WGS84.zip' in result['census2011']['geodata_urls'][0]
    assert 'WGS_84_UTM/2011' in result['census2011']['geodata_urls'][0]

    # Verify boundaries folder for 2011 (special case)
    assert 'Limiti_2011_WGS84.zip' in result['census2011']['admin_boundaries_url']


def test_get_census_dictionary_2021():
    """Test get_census_dictionary for year 2021."""
    result = get_census_dictionary(census_year=2021, region_list=[10])

    assert 'census2021' in result
    assert result['census2021']['census_code'] == 'sez21_id'

    # Verify geodata URLs format for 2021 (different structure)
    assert 'R10_21.zip' in result['census2021']['geodata_urls'][0]
    assert 'basi_territoriali/2021' in result['census2021']['geodata_urls'][0]

    # Verify data URL for 2021 (different from other years)
    assert 'esploradati.istat.it' in result['census2021']['data_url']


def test_get_census_dictionary_unsupported_year():
    """Test get_census_dictionary raises ValueError for unsupported year."""
    with pytest.raises(ValueError) as exc_info:
        get_census_dictionary(census_year=2015, region_list=[])

    assert "The selected census year is not supported" in str(exc_info.value)
    assert "[1991, 2001, 2011, 2021]" in str(exc_info.value)


def test_remove_files(tmp_path: Path):
    """Test remove_files deletes files from filesystem."""
    # Create test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("content1")
    file2.write_text("content2")

    # Verify files exist
    assert file1.exists()
    assert file2.exists()

    # Remove files
    remove_files([file1, file2])

    # Verify files are deleted
    assert not file1.exists()
    assert not file2.exists()

