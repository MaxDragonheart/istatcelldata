import csv
import logging
import ssl
import zipfile
from pathlib import Path, PosixPath
from typing import Union

import chardet
import requests
import urllib3
import xlrd
from fsspec import get_fs_token_paths
from tqdm import tqdm

from census_istat.config import logger, console_handler, GEODATA_FOLDER

logger.addHandler(console_handler)


def check_encoding(data: Union[Path, PosixPath]) -> str:
    """Verifica della codifica del dato.

    Args:
        data: Union[Path, PosixPath]

    Returns:
        str
    """
    # Look at the first ten thousand bytes to guess the character encoding
    with open(data, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))

        if result['encoding'] == 'ascii':
            result['encoding'] = 'latin1'

    return result['encoding']


def csv_from_excel(
        data: Union[Path, PosixPath],
        output_path: Union[Path, PosixPath],
        metadata: bool = False
) -> Union[Path, PosixPath]:
    """Conversione di un xls in csv.

    Args:
        data: Union[Path, PosixPath]
        output_path: Union[Path, PosixPath]
        metadata: bool

    Returns:
        Union[Path, PosixPath]
    """
    logging.info(f'Read data from {data}')
    read_data = xlrd.open_workbook(data)

    if metadata:
        sheet_name = 'Metadati'
    else:
        sheet_list = read_data.sheet_names()
        sheet_list.remove('Metadati')
        sheet_name = sheet_list[0]

    get_sheet = read_data.sheet_by_name(sheet_name)

    output_data = open(output_path, 'w')
    write_csv = csv.writer(output_data, quoting=csv.QUOTE_ALL)

    logging.info('Convert xls to csv')
    for row_id in tqdm(range(get_sheet.nrows)):
        write_csv.writerow(get_sheet.row_values(row_id))

    output_data.close()

    return output_path


def census_folder(
        output_data_folder: Union[Path, PosixPath],
        year: int = 2011  # last official census at 2023 02 19
) -> Union[Path, PosixPath]:
    """Creazione delle cartelle per dati e geodati censuari
    dell'anno selezionato.

    Args:
        output_data_folder: Union[Path, PosixPath]
        year: int

    Returns:
        Union[Path, PosixPath]
    """
    logging.info(f"Make folder for {year}' census data and geodata.")
    download_folder_name = f"census_{year}"
    fs, fs_token, paths = get_fs_token_paths(output_data_folder)

    destination_folder = Path(paths[0]).joinpath(download_folder_name)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    return destination_folder


def census_geodata_folder(
        output_data_folder: Union[Path, PosixPath],
        year: int
) -> Union[Path, PosixPath]:
    """Creazione della cartella dei geodati per l'anno censuario selezionato.

    Args:
        output_data_folder: Union[Path, PosixPath]
        year: int

    Returns:
        Union[Path, PosixPath]
    """
    # Make folder for yearly census data
    destination_folder = census_folder(output_data_folder=output_data_folder, year=year)

    folder = destination_folder.joinpath(GEODATA_FOLDER)

    return folder


def unzip_data(input_data: Union[Path, PosixPath], output_folder: Union[Path, PosixPath]) -> Union[Path, PosixPath]:
    """Decompressione dei dati.

    Args:
        input_data: Union[Path, PosixPath].
        output_folder: Union[Path, PosixPath].

    Returns:
        Union[Path, PosixPath]
    """
    with zipfile.ZipFile(input_data, "r") as zf:
        zf.extractall(output_folder)


def get_metadata(input_path: Union[Path, PosixPath], output_path: Union[Path, PosixPath]) -> list:
    """Lettura dei metadati.

    Args:
        input_path: Union[Path, PosixPath]
        output_path: Union[Path, PosixPath]

    Returns:
        list
    """
    file_list = list(input_path.rglob("*"))

    path_list = []
    for data_file in file_list:
        file_name = data_file.stem.split('\\')[1]
        process_data = csv_from_excel(
            data=data_file,
            output_path=output_path.joinpath(f'{file_name}.csv'),
            metadata=True
        )
        path_list.append(process_data)

    return path_list


class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.
    # Solution to issue #24 by https://stackoverflow.com/a/73519818/10012856
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


def get_legacy_session():
    # Solution to issue #24 by https://stackoverflow.com/a/73519818/10012856
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    session = requests.session()
    session.mount('https://', CustomHttpAdapter(ctx))
    return session

