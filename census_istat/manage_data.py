import logging

import dask.dataframe as dd

from census_istat.config import logger, console_handler
from census_istat.generic import check_encoding

logger.addHandler(console_handler)


def read_csv(csv_path: str, separator: str = ';'):
    # Get encoding
    logging.info('Get encoding')
    data_encoding = check_encoding(data=csv_path)

    # Read data
    logging.info('Read data')
    ddf = dd.read_csv(csv_path, encoding=data_encoding, sep=separator)

    return ddf
