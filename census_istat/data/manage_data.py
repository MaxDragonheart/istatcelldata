import logging
from pathlib import Path, PosixPath
from typing import Union

import pandas as pd
# TODO Multithread processing with Dask #15
# import dask.dataframe as dd
# from dask.dataframe import DataFrame
# from dask.distributed import Client, LocalCluster
from pandas import DataFrame

from census_istat.config import logger, console_handler, SHARED_DATA
from census_istat.generic import check_encoding

logger.addHandler(console_handler)
# TODO Multithread processing with Dask #15
# cluster = LocalCluster(n_workers=8, threads_per_worker=N_CORES, processes=True)
# client = Client(cluster)


def read_csv(
        csv_path: Union[Path, PosixPath],
        separator: str = ';'
) -> DataFrame:
    """Read csv and return DataFrame.

    Args:
        csv_path: Union[Path, PosixPath]
        separator: str

    Returns:
        DataFrame
    """
    # Get encoding
    logging.info('Get encoding')
    data_encoding = check_encoding(data=csv_path)

    # Read data
    logging.info('Read data')
    # TODO Multithread processing with Dask #15
    # ddf = dd.read_csv(csv_path, encoding=data_encoding, sep=separator, sample=100000, assume_missing=True)
    ddf = pd.read_csv(csv_path, encoding=data_encoding, sep=separator)
    ddf.columns = ddf.columns.str.lower()
    ddf = ddf.replace(['nan', 'NaN'], 0)

    return ddf


def merge_data(
        csv_path: Union[Path, PosixPath],
        year: int,
        separator: str = ';',
        output_path: Union[Path, PosixPath] = None,
) -> Union[Path, PosixPath, DataFrame]:
    """Merge all census data per selected year in one
    object.

    Args:
        csv_path: Union[Path, PosixPath]
        year: int
        separator: str
        output_path: Union[Path, PosixPath]

    Returns:
        Union[Path, PosixPath, DataFrame]
    """
    # List all csv paths
    files_path = list(csv_path.rglob("*.csv"))

    data_list = []
    for file in files_path:
        if not file.stem == f'tracciato_{year}_sezioni':
            data = read_csv(csv_path=file, separator=separator)
            data_list.append(data)

    # Make Dask DataFrame
    logging.info('Make Dask DataFrame')
    # TODO Multithread processing with Dask #15
    # ddf = dd.concat(data_list)
    ddf = pd.concat(data_list)
    ddf = ddf.sort_values(f'sez{year}')

    if output_path is None:
        return ddf

    else:
        output_data = output_path.joinpath(f'data{year}.csv')
        logging.info(f'Save data to {output_data}')
        # TODO Multithread processing with Dask #15
        # df = ddf.compute()
        df = ddf
        df.to_csv(output_data, sep=separator, index=False)


def list_shared_columns() -> list:
    """Make list of alla shared data.

    Returns:
        list
    """
    column_list = []
    for key, value in SHARED_DATA.items():
        column_code = value['codice'].lower()
        column_list.append(column_code)

    return column_list
