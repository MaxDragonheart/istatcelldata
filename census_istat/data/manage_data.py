import logging
from pathlib import Path, PosixPath
from typing import Union

import dask.dataframe as dd
from dask.dataframe import DataFrame
from dask.distributed import Client, LocalCluster

from census_istat.config import logger, console_handler, N_CORES
from census_istat.generic import check_encoding

logger.addHandler(console_handler)
# cluster = LocalCluster(n_workers=8, threads_per_worker=N_CORES, processes=True)
# client = Client(cluster)


def read_csv(
        csv_path: Union[Path, PosixPath],
        separator: str = ';'
) -> DataFrame:
    """Read csv using Dask and return a Dask DataFrame.

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
    ddf = dd.read_csv(csv_path, encoding=data_encoding, sep=separator, sample=100000, assume_missing=True)
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
    ddf = dd.concat(data_list)
    ddf = ddf.sort_values(f'sez{year}')

    if output_path is None:
        return ddf

    else:
        output_data = output_path.joinpath(f'data{year}.csv')
        logging.info(f'Save data to {output_data}')
        df = ddf.compute()
        df.to_csv(output_data, sep=separator, index=False)

