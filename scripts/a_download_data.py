import logging
import datetime

from census_istat.config import logger, console_handler, OUTPUT_FOLDER
from census_istat.download import download_census_data

logger.addHandler(console_handler)
target_years = [2011]

if __name__ == '__main__':
    time_start = datetime.datetime.now()
    logging.info(f'Start analysis at {time_start}')

    logging.info(f"Start download of data and geodata for {year}")

    for year in target_years:
        logging.info(f'Download census data for year {year}')
        download_census_data(
            output_data_folder=OUTPUT_FOLDER,
            year=year
        )

    time_end = datetime.datetime.now() - time_start
    logging.info(f'End analysis in {time_end}')
