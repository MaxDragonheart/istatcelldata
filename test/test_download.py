import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from istatcelldata.download import download_base


def test_download_mock_success(tmp_path: Path):
    """Test successful download and extraction with mocked HTTP response."""
    download_folder = tmp_path / "download"
    download_folder.mkdir()

    extract_folder = tmp_path / "extract"
    extract_folder.mkdir()

    destination_folder = tmp_path / "destination"
    destination_folder.mkdir()

    # Create a mock ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("test_file.txt", "test content")
    zip_data = zip_buffer.getvalue()

    # Mock the requests.get response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Length": str(len(zip_data))}
    mock_response.iter_content = lambda chunk_size: [
        zip_data[i : i + chunk_size] for i in range(0, len(zip_data), chunk_size)
    ]

    with patch("istatcelldata.download.requests.get", return_value=mock_response):
        result = download_base(
            data_link="https://example.com/data.zip",
            data_file_path_destination=download_folder / "data.zip",
            data_folder=extract_folder,
            destination_folder=destination_folder,
        )

    # Verify the result
    assert result == destination_folder

    # Verify the zip was extracted
    extracted_file = extract_folder / "test_file.txt"
    assert extracted_file.exists()
    assert extracted_file.read_text() == "test content"

    # Verify the zip file was removed
    assert not (download_folder / "data.zip").exists()


def test_mock_http_error(tmp_path: Path):
    """Test download failure with non-200 HTTP status."""
    download_folder = tmp_path / "download"
    download_folder.mkdir()

    extract_folder = tmp_path / "extract"
    extract_folder.mkdir()

    destination_folder = tmp_path / "destination"

    # Mock a 404 response
    mock_response = Mock()
    mock_response.status_code = 404

    with patch("istatcelldata.download.requests.get", return_value=mock_response):
        with pytest.raises(Exception, match="returned status code 404"):
            download_base(
                data_link="https://example.com/notfound.zip",
                data_file_path_destination=download_folder / "data.zip",
                data_folder=extract_folder,
                destination_folder=destination_folder,
            )


def test_mock_network_error(tmp_path: Path):
    """Test download failure with network exception."""
    download_folder = tmp_path / "download"
    download_folder.mkdir()

    extract_folder = tmp_path / "extract"
    destination_folder = tmp_path / "destination"

    # Mock a network error
    with patch("istatcelldata.download.requests.get", side_effect=Exception("Network error")):
        with pytest.raises(Exception, match="Network error"):
            download_base(
                data_link="https://example.com/data.zip",
                data_file_path_destination=download_folder / "data.zip",
                data_folder=extract_folder,
                destination_folder=destination_folder,
            )


def test_mock_no_content_length(tmp_path: Path):
    """Test download when Content-Length header is missing."""
    download_folder = tmp_path / "download"
    download_folder.mkdir()

    extract_folder = tmp_path / "extract"
    extract_folder.mkdir()

    destination_folder = tmp_path / "destination"
    destination_folder.mkdir()

    # Create a mock ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("test.txt", "content")
    zip_data = zip_buffer.getvalue()

    # Mock response without Content-Length
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}  # No Content-Length
    mock_response.iter_content = lambda chunk_size: [zip_data]

    with patch("istatcelldata.download.requests.get", return_value=mock_response):
        result = download_base(
            data_link="https://example.com/data.zip",
            data_file_path_destination=download_folder / "data.zip",
            data_folder=extract_folder,
            destination_folder=destination_folder,
        )

    assert result == destination_folder
    assert (extract_folder / "test.txt").exists()


@pytest.mark.download
def test_download_base_real_integration(tmp_path: Path):
    """Integration test with real download (slow, skipped by default)."""
    print("test_download_base_real_integration")
    download_folder = tmp_path.joinpath("download")
    download_folder.mkdir(parents=True, exist_ok=True)

    extract_folder = tmp_path.joinpath("extract")
    extract_folder.mkdir(parents=True, exist_ok=True)

    destination_folder = tmp_path.joinpath("destination")
    destination_folder.mkdir(parents=True, exist_ok=True)

    download_url = "https://www.istat.it/storage/cartografia/basi_territoriali/WGS_84_UTM/1991/R15_91_WGS84.zip"
    data_file_name = Path(download_url).stem + Path(download_url).suffix
    print(data_file_name)

    data = download_base(
        data_link=download_url,
        data_file_path_destination=download_folder.joinpath(data_file_name),
        data_folder=extract_folder,
        destination_folder=destination_folder,
    )
    print(data)
    assert isinstance(data, Path)
