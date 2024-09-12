import logging
import os
from pathlib import Path
from typing import List

from tqdm.auto import tqdm

from istatcelldata.config import logger, console_handler, MAIN_LINK, CENSUS_DATA_FOLDER, GEODATA_FOLDER, \
    BOUNDARIES_DATA_FOLDER, PREPROCESSING_FOLDER
from istatcelldata.data.census_1991_2001 import census_trace, remove_xls
from istatcelldata.generic import census_folder, unzip_data, get_legacy_session

logger.addHandler(console_handler)


def download_data_core(
        data_link: str,
        data_file_path_destination: Path,
        data_folder: Path,
        destination_folder: Path,
) -> Path:
    """Funzione di download base.

    Args:
        data_link: Path
        data_file_path_destination: Path
        data_folder: Path
        destination_folder: Path

    Returns:
        Path

    Raises:
        Link {data_link} return status code {data.status_code}.
    """
    # Download data
    logging.info(f"Download census data | {data_link}")
    data = get_legacy_session().get(data_link)

    if data.status_code == 200:
        data_size = int(data.headers.get('Content-Length'))
        # Progress bar via tqdm
        with tqdm.wrapattr(data.raw, "read", total=data_size, desc="Downloading..."):
            open(data_file_path_destination, 'wb').write(data.content)
        logging.info("Download completed")
    else:
        raise Exception(f'Link {data_link} return status code {data.status_code}.')

    logging.info("Unzip file")
    unzip_data(data_file_path_destination, data_folder)

    logging.info(f"Deleting zip file | {data_file_path_destination}")
    os.remove(data_file_path_destination)
    logging.info("File deleted")

    return destination_folder.joinpath(data_folder)


def download_census_data(
        output_data_folder: Path,
        year: int
) -> Path:
    """Download dei dati censuari.

    Args:
        output_data_folder: Path
        year: Integer.

    Returns
        Path
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

    # Make data folder
    data_folder = destination_folder.joinpath('data')
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    if year == 2021:
        data_link = "https://esploradati.censimentopopolazione.istat.it/databrowser/DWL/PERMPOP/SUBCOM/Dati_regionali_2021.zip"
    else:
        data_link = f"{MAIN_LINK}/variabili-censuarie/dati-cpa_{year}.zip"

    data_file_name = Path(data_link).stem + Path(data_link).suffix
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    logging.info("Download census data")
    dowload_folder = download_data_core(
        data_link=data_link,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )

    if year in [1991, 2001]:
        logging.info(f'Convert xls to csv for {year}')
        files_list = list(dowload_folder.rglob("*.xls"))
        first_element = files_list[0]

        # Make data folder
        data_folder_1991_2001 = dowload_folder.joinpath(CENSUS_DATA_FOLDER)
        Path(data_folder_1991_2001).mkdir(parents=True, exist_ok=True)

        census_trace(
            file_path=first_element,
            year=year,
            output_path=data_folder_1991_2001
        )
        remove_xls(
            folder_path=dowload_folder,
            census_code=f'sez{year}',
            output_path=data_folder_1991_2001,
        )
    elif year == 2021:
        logging.info(f'Convert xls to csv for {year}')
        files_list = list(dowload_folder.rglob("*.xls"))
        first_element = files_list[0]

        # Make data folder
        data_folder_1991_2001 = dowload_folder.joinpath(CENSUS_DATA_FOLDER)
        Path(data_folder_1991_2001).mkdir(parents=True, exist_ok=True)
    else:
        pass
    logging.info(f"Download census data completed and saved to {destination_folder}")
    return destination_folder


def download_census_geodata(
        output_data_folder: Path,
        year: int,
        region_list: List = []
) -> Path:
    """Download dei geodati censuari.

    Args:
        output_data_folder: Path
        year: Integer.
        region_list: List

    Returns:
        Path
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    # Make data folder
    data_folder = destination_folder.joinpath(GEODATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    year_folder = str(year)[2:]
    if len(region_list) == 0:
        regions = tqdm(range(1, 21, 1))
    else:
        regions = region_list

    logging.info("Download census geodata")
    for region in regions:
        region = str(region).zfill(2)
        if year == 2021:
            data_link = f"http://www.istat.it/storage/cartografia/basi_territoriali/{year}/R{region}_21.zip"
        else:
            data_link = f"{MAIN_LINK}/basi_territoriali/WGS_84_UTM/{year}/R{region}_{year_folder}_WGS84.zip"

        data_file_name = data_link.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)

        download_data_core(
            data_link=data_link,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

    logging.info(f"Download census geodata completed and saved to {data_folder}")
    return data_folder


def download_administrative_boundaries(
        output_data_folder: Path,
        year: int
) -> Path:
    """Download dei limiti amministrativi dell'anno cenusario selezionato.

    Args:
        output_data_folder: Path
        year: int

    Returns:
        Path
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

    # Make data folder
    data_folder = destination_folder.joinpath(BOUNDARIES_DATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    if year == 2011:
        data_link = f"{MAIN_LINK}/confini_amministrativi/non_generalizzati/2011/Limiti_2011_WGS84.zip"

    else:
        data_link = f"{MAIN_LINK}/confini_amministrativi/non_generalizzati/Limiti{year}.zip"

    data_file_name = data_link.split('/')[-1]
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    logging.info("Download administrative boundaries")
    download_data_core(
        data_link=data_link,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )
    logging.info(f"Download administrative boundaries completed and saved to {destination_folder}")
    return destination_folder


def download_all_census_data(
        output_data_folder: Path,
        year: int,
        region_list: List = []
) -> None:
    """Download di tutti i dati censuari per l'anno selezionato. E' possibile
    effettuare il download per singola Regione ma anche per specifiche Regioni.
    Quando il campo `region_list` resta vuoto vengono scaricati i dati di tutte le Regioni.

    Args:
        output_data_folder: Path
        year: int
        region_list: List
    """
    # Make data folder
    data_folder = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    # Download data
    download_census_data(
        output_data_folder=data_folder, year=year
    )

    # Download geodata
    download_census_geodata(
        output_data_folder=data_folder, year=year, region_list=region_list
    )

    # Download administrative boundaries
    download_administrative_boundaries(
        output_data_folder=data_folder, year=year
    )
