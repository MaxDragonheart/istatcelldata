import logging
import os
from pathlib import Path, PosixPath
from typing import Union

import requests
from tqdm.auto import tqdm

from census_istat.config import logger, console_handler, MAIN_LINK
from census_istat.data.census_1991_2001 import make_tracciato, remove_xls
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

    logging.info("Download census data")
    _download_data(
        data_link=data_link,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )

    if year in [1991, 2001]:
        logging.info(f'Convert xls to csv for {year}')
        files_list = list(data_folder.rglob("*.xls"))
        first_element = files_list[0]
        make_tracciato(
            file_path=first_element,
            year=year,
            output_path=data_folder
        )
        remove_xls(
            folder_path=data_folder,
            census_code=f'sez{year}'
        )
    logging.info("Download census data completed")


def download_census_geodata(
        output_data_folder: Union[Path, PosixPath],
        year: int = 2011
) -> None:
    """Download census geodata
    Args:
        output_data_folder: Union[Path, PosixPath]
        year: Integer. Default 2011.
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    # Make data folder
    data_folder = destination_folder.joinpath('geodata')
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    year_folder = str(year)[2:]
    regions = tqdm(range(1, 21, 1))

    logging.info("Download census geodata")
    for region in regions:
        region = str(region).zfill(2)
        data_link = f"{MAIN_LINK}/basi_territoriali/WGS_84_UTM/{year}/R{region}_{year_folder}_WGS84.zip"

        data_file_name = data_link.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        _download_data(
            data_link=data_link,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

    logging.info("Download census geodata completed")


def download_administrative_boundaries(
        output_data_folder: Union[Path, PosixPath],
        year: int = 2011
):
    """Download official boundaries for census year.
    Args:
        output_data_folder: Union[Path, PosixPath]
        year: int
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

    # Make data folder
    data_folder = destination_folder.joinpath('administrative_boundaries')
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    data_link = f"{MAIN_LINK}/confini_amministrativi/non_generalizzati/Limiti{year}.zip"

    data_file_name = data_link.split('/')[-1]
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    logging.info("Download administrative boundaries")
    _download_data(
        data_link=data_link,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )
    logging.info("Download administrative boundaries completed")


def download_all_census_data(
        output_data_folder: Union[Path, PosixPath],
        year: int = 2011
) -> None:
    """Download all census data. Must be downloaded both data
    and geodata per selected year.
    Args:
        output_data_folder: Union[Path, PosixPath]
        year: int
    """
    # Download data
    download_census_data(
        output_data_folder=output_data_folder, year=year
    )

    # Download geodata
    download_census_geodata(
        output_data_folder=output_data_folder, year=year
    )

    # Download administrative boundaries
    download_administrative_boundaries(
        output_data_folder=output_data_folder, year=year
    )


def _download_data(
        data_link: str,
        data_file_path_destination: Union[Path, PosixPath],
        data_folder: Union[Path, PosixPath],
        destination_folder: Union[Path, PosixPath],
) -> Union[Path, PosixPath]:
    """Download base function.

    Args:
        data_link: Union[Path, PosixPath]
        data_file_path_destination: Union[Path, PosixPath]
        data_folder: Union[Path, PosixPath]
        destination_folder: Union[Path, PosixPath]

    Returns:
        Union[Path, PosixPath]
    """
    try:
        # Download data
        logging.info(f"Download census data | {data_link}")
        data = requests.get(data_link)

        if data.status_code == 200:
            data_size = int(data.headers.get('Content-Length'))
            # Progress bar via tqdm
            with tqdm.wrapattr(data.raw, "read", total=data_size, desc="Downloading..."):
                open(data_file_path_destination, 'wb').write(data.content)
            logging.info("Download completed")
        else:
            raise Exception()

        logging.info("Unzip file")
        unzip_data(data_file_path_destination, data_folder)

        logging.info(f"Deleting zip file | {data_file_path_destination}")
        os.remove(data_file_path_destination)
        logging.info("File deleted")

        return destination_folder

    except:
        logging.info("Something went wrong!!!")
        logging.info(f'Link {data_link} return status code {data.status_code}.')
