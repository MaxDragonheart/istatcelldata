import logging
import datetime
import shutil
from pathlib import Path
from typing import Union, List

from istatcelldata.config import logger, console_handler, TARGET_YEARS, PREPROCESSING_FOLDER, DATA_FOLDER, \
    CENSUS_DATA_FOLDER
from istatcelldata.data.census_1991_2001 import merge_data_1991_2001
from istatcelldata.data.manage_data import merge_data
from istatcelldata.download import download_all_census_data
from istatcelldata.geodata.manage_geodata import read_raw_census_geodata, join_year_census

logger.addHandler(console_handler)


def download_raw_data(
        output_data_folder: Union[str, Path],
        year_list: List = [],
        region_list: List = [],
):
    """Download nel path di destinazione di tutti i dati grezzi sui censimenti. E' possibile
    effettuare il download per singolo anno e per singola Regione ma anche per specifici anni e specifiche Regioni.
    Quando i campi `year_list` e `region_list` restano vuoti vengono scaricati i dati di tutti gli anni censuari
    e di tutte le Regioni.

    Args:
        output_data_folder: Union[str, Path]
        year_list: List
        region_list: List
    """
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')

    if len(year_list) == 0:
        target = TARGET_YEARS
    else:
        target = year_list

    for year in target:
        logging.info(f'Start download census data for year {year}')
        download_all_census_data(
            output_data_folder=output_data_folder,
            year=year,
            region_list=region_list
        )

    time_end = datetime.datetime.now() - time_start
    logging.info(f'End analysis in {time_end}')


def process_raw_data(output_data_folder: Union[str, Path], region_list: List = []):
    """Analisi dei dati grezzi e creazione nel path di destinazione
    di un .csv ed un .gpkg per ogni anno censuario.

    Args:
        output_data_folder: Union[str, Path]
        region_list: List
    """
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')
    data_path = output_data_folder.joinpath(PREPROCESSING_FOLDER)

    for year in TARGET_YEARS:
        logging.info(f'Process data {year}')
        csv_path = data_path.joinpath(f'census_{year}').joinpath(DATA_FOLDER).joinpath(CENSUS_DATA_FOLDER)

        if csv_path.exists():
            output_data_path = csv_path.parent.parent

            if year in [1991, 2001]:
                merge_data_1991_2001(
                    csv_path=csv_path,
                    year=year,
                    output_path=output_data_path,
                    region_list=region_list
                )
                read_raw_census_geodata(
                    data_path=data_path,
                    year=year,
                    output_path=output_data_path
                )
            else:
                merge_data(
                    csv_path=csv_path,
                    year=year,
                    output_path=output_data_path
                )
                read_raw_census_geodata(
                    data_path=data_path,
                    year=year,
                    output_path=output_data_path
                )

    time_end = datetime.datetime.now() - time_start
    logging.info(f'End analysis in {time_end}')


def process_data(output_data_folder: Union[str, Path], delete_process_folder: bool = True):
    """Unione del .csv e del .gpkg di ogni anno censuario in un unico .gpkg creato
    nel path di destinazione. Le cartelle di preprocessamento vengono eliminate di default.

    Args:
        output_data_folder: Union[str, Path]
        delete_process_folder: bool
    """
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')
    data_path = output_data_folder.joinpath(PREPROCESSING_FOLDER)
    output_path = data_path.parent

    for year in TARGET_YEARS:
        year_data = data_path.joinpath(f'census_{year}')

        if year_data.exists():
            logging.info(f'Process census for {year}')
            join_year_census(
                data_path=year_data,
                year=year,
                output_path=output_path,
                remove_processed=delete_process_folder,
                only_shared=True
            )

    if delete_process_folder:
        logging.info(f'Delete data path {data_path}')
        shutil.rmtree(data_path)

    time_end = datetime.datetime.now() - time_start
    logging.info(f'End analysis in {time_end}')
