from pathlib import Path
from unittest.mock import patch

from istatcelldata.census1991.download import download_data
from istatcelldata.census2001.download import download_all_census_data_2001
from istatcelldata.census2011.download import download_administrative_boundaries, download_geodata
from istatcelldata.config import PREPROCESSING_FOLDER

year = 2001


def test_download_data(tmp_path: Path):
    print("test_download_data")
    data = download_data(output_data_folder=tmp_path, census_year=year)
    print(data)
    assert isinstance(data, Path)


def test_download_geodata(tmp_path: Path):
    print("test_download_geodata")
    data = download_geodata(output_data_folder=tmp_path, census_year=year, region_list=[3, 15])
    print(data)
    assert isinstance(data, Path)


def test_download_administrative_boundaries(tmp_path: Path):
    print("test_download_administrative_boundaries")
    data = download_administrative_boundaries(
        output_data_folder=tmp_path,
        census_year=year,
    )
    print(data)
    assert isinstance(data, Path)


def test_download_all_census_data_2001(tmp_path: Path):
    print("test_download_all_census_data_2001")
    download_all_census_data_2001(output_data_folder=tmp_path, region_list=[2, 15])


# Mock-based unit tests for coverage


@patch("istatcelldata.census2001.download.download_administrative_boundaries")
@patch("istatcelldata.census2001.download.download_geodata")
@patch("istatcelldata.census2001.download.download_data")
def test_download_all_census_data_2001_unit(
    mock_download_data, mock_download_geodata, mock_download_admin, tmp_path: Path
):
    """Test download_all_census_data_2001 calls all download functions (unit test)."""
    output_folder = tmp_path / "census_2001"
    region_list = [1, 2, 3]

    # Call the function
    result = download_all_census_data_2001(
        output_data_folder=output_folder, region_list=region_list
    )

    # Verify the preprocessing folder was created
    expected_data_folder = output_folder / PREPROCESSING_FOLDER
    assert expected_data_folder.exists()

    # Verify all download functions were called with correct parameters
    mock_download_data.assert_called_once_with(
        output_data_folder=expected_data_folder, census_year=2001
    )

    mock_download_geodata.assert_called_once_with(
        output_data_folder=expected_data_folder, region_list=region_list, census_year=2001
    )

    mock_download_admin.assert_called_once_with(
        output_data_folder=expected_data_folder, census_year=2001
    )

    # Verify the function returns the output folder
    assert result == output_folder


@patch("istatcelldata.census2001.download.download_administrative_boundaries")
@patch("istatcelldata.census2001.download.download_geodata")
@patch("istatcelldata.census2001.download.download_data")
def test_download_all_census_data_2001_empty_region_list_unit(
    mock_download_data, mock_download_geodata, mock_download_admin, tmp_path: Path
):
    """Test download_all_census_data_2001 with empty region_list (unit test)."""
    output_folder = tmp_path / "census_2001_all_regions"

    # Call with empty region_list (default parameter)
    result = download_all_census_data_2001(output_data_folder=output_folder)

    # Verify the preprocessing folder was created
    expected_data_folder = output_folder / PREPROCESSING_FOLDER
    assert expected_data_folder.exists()

    # Verify geodata was called with empty list (downloads all regions)
    mock_download_geodata.assert_called_once_with(
        output_data_folder=expected_data_folder, region_list=[], census_year=2001
    )

    # Verify result
    assert result == output_folder
