import logging
import os
from pathlib import Path, PosixPath
from typing import Union

import requests
from tqdm.auto import tqdm

from census_istat.config import logger, console_handler, MAIN_LINK
from census_istat.generic import census_folder, unzip_data

logger.addHandler(console_handler)


def download_census_data(
        output_data_folder: Union[Path, PosixPath],
        year: int = 2011
) -> Union[Path, PosixPath]:
    """Download census data
    Args:
        output_data_folder: Union[Path, PosixPath]
        year: Integer. Default 2011.
    Returns
        Union[Path, PosixPath]
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

    # Make data folder
    data_folder = destination_folder.joinpath('data')
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    data_link = f"{MAIN_LINK}/variabili-censuarie/dati-cpa_{year}.zip"

    data_file_name = Path(data_link).stem + Path(data_link).suffix
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    try:
        # Download data
        logging.info(f"Download census data | {data_link}")
        data = requests.get(data_link)
        data_size = int(data.headers.get('Content-Length'))

        if data.status_code == 200:
            # Progress bar via tqdm
            with tqdm.wrapattr(data.raw, "read", total=data_size, desc="Downloading..."):
                open(data_file_path_dest, 'wb').write(data.content)
            logging.info("Download completed")
        else:
            raise Exception(f'Link {data_link} return status code {data.status_code}.')

        logging.info("Unzip file")
        unzip_data(data_file_path_dest, data_folder)

    finally:
        try:
            logging.info(f"Deleting zip file | {data_file_path_dest}")
            os.remove(data_file_path_dest)
            logging.info("File deleted")

            return destination_folder

        except Exception:
            logging.info("Something went wrong!!")
    logging.info("- Download census data completed")
