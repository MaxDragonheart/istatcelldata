import logging
import datetime
import shutil

from census_istat.config import logger, console_handler, MAIN_PATH, PREPROCESSING_FOLDER
from census_istat.geodata.manage_geodata import join_year_census

logger.addHandler(console_handler)
target_years = [1991, 2001, 2011]
delete_process_folder = True

if __name__ == '__main__':
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')
    data_path = MAIN_PATH.joinpath(PREPROCESSING_FOLDER)
    output_path = data_path.parent

    for year in target_years:
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
