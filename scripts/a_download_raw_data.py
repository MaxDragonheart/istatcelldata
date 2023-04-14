import logging
import datetime

from istatcelldata.config import logger, console_handler, MAIN_PATH
from istatcelldata.download import download_all_census_data

logger.addHandler(console_handler)
target_years = [1991, 2001, 2011]

if __name__ == '__main__':
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')

    for year in target_years:
        logging.info(f'Start download census data for year {year}')
        download_all_census_data(
            output_data_folder=MAIN_PATH,
            year=year
        )

    time_end = datetime.datetime.now() - time_start
    logging.info(f'End analysis in {time_end}')
