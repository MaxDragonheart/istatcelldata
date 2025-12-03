import logging
import os
import time
from pathlib import Path

import requests
from tqdm import tqdm

from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import unzip_data

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def download_base(
    data_link: str,
    data_file_path_destination: Path,
    data_folder: Path,
    destination_folder: Path,
) -> Path:
    """Download a file from URL, display progress bar, and extract the resulting ZIP.

    This function handles the complete workflow for downloading an archive (typically
    ZIP format) from an HTTP/HTTPS URL. It saves the file to a local path, displays
    a progress bar using `tqdm`, extracts the content to the destination folder, and
    finally removes the compressed file.

    Args:
        data_link: URL from which to download the file (e.g., census data ZIP archive).
        data_file_path_destination: Complete local path where the downloaded compressed
            file will be saved.
        data_folder: Folder where the compressed file content will be extracted.
        destination_folder: Logical destination folder associated with the downloaded
            dataset. This path is returned at the end for consistency with the calling
            workflow.

    Returns:
        Path to `destination_folder`, usable as a reference to the root of the
        downloaded and extracted data.

    Raises:
        Exception: If the server returns an HTTP status code other than 200, or if
            any error occurs during download, file saving, or extraction.
    """
    start_time = time.time()
    try:
        logging.info(f"Starting data download from link: {data_link}")
        data = requests.get(data_link, stream=True)

        # Check download status
        if data.status_code == 200:
            data_size = int(data.headers.get("Content-Length", 0))

            # Progress bar via tqdm
            with open(data_file_path_destination, "wb") as output_file:
                # Use tqdm for progress bar
                with tqdm(
                    total=data_size,
                    desc="Downloading...",
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as pbar:
                    for chunk in data.iter_content(chunk_size=1024):  # Download file in chunks
                        if chunk:  # Avoid empty chunks
                            output_file.write(chunk)
                            pbar.update(len(chunk))  # Update progress bar

            end_time = time.time()  # End time
            elapsed_time = end_time - start_time  # Calculate elapsed time
            logging.info(f"Download completed successfully in {elapsed_time:.2f} seconds.")
        else:
            logging.error(f"Download failed. Status code: {data.status_code}")
            raise Exception(f"Link {data_link} returned status code {data.status_code}.")

        logging.info("Starting ZIP file extraction.")
        unzip_data(data_file_path_destination, data_folder)

        logging.info(f"Deleting ZIP file | {data_file_path_destination}")
        os.remove(data_file_path_destination)
        logging.info("ZIP file deleted successfully.")

    except Exception as e:
        logging.error(f"Error during download: {str(e)}")
        raise e

    return destination_folder
