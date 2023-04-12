import logging
import datetime

from census_istat.config import logger, console_handler, MAIN_PATH, DATA_FOLDER, PREPROCESSING_FOLDER, \
    CENSUS_DATA_FOLDER
from census_istat.data.census_1991_2001 import merge_data_1991_2001
from census_istat.data.manage_data import merge_data
from census_istat.geodata.manage_geodata import read_raw_census_geodata

logger.addHandler(console_handler)
target_years = [1991, 2001, 2011]

if __name__ == '__main__':
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')
    data_path = MAIN_PATH.joinpath(PREPROCESSING_FOLDER)

    for year in target_years:
        logging.info(f'Process data {year}')
        csv_path = data_path.joinpath(f'census_{year}').joinpath(DATA_FOLDER).joinpath(CENSUS_DATA_FOLDER)

        output_data_path = csv_path.parent.parent

        if year in [1991, 2001]:
            merge_data_1991_2001(
                csv_path=csv_path,
                year=year,
                output_path=output_data_path
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
