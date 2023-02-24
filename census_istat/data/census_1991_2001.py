import logging
import os
from pathlib import Path, PosixPath
from typing import Union

import pandas as pd
import xlrd
from pandas import DataFrame
from tqdm import tqdm

from census_istat.config import logger, console_handler, PREPROCESSING_FOLDER, BOUNDARIES_DATA_FOLDER
from census_istat.data.manage_data import merge_data
from census_istat.generic import get_metadata

logger.addHandler(console_handler)


def read_xls(
        file_path: Union[Path, PosixPath],
        census_code: str = 'sez1991',
        output_path: Union[Path, PosixPath] = None,
        metadata: bool = False
) -> Union[DataFrame, Path, PosixPath]:
    """Read census data for years 1991 and 2001 and return
    DataFrame or csv.

    Args:
        file_path: Union[Path, PosixPath]
        census_code: str
        output_path: Union[Path, PosixPath]
        metadata: bool

    Returns:
        Union[DataFrame, Path, PosixPath]
    """
    logging.info(f'Read data from {file_path}')
    read_data = xlrd.open_workbook(file_path)

    if metadata:
        sheet_name = 'Metadati'
    else:
        sheet_list = read_data.sheet_names()
        sheet_list.remove('Metadati')
        sheet_name = sheet_list[0]

    get_sheet = read_data.sheet_by_name(sheet_name)

    dataset = []
    for row_id in tqdm(range(get_sheet.nrows)):
        dataset.append(get_sheet.row_values(row_id))

    # Make DataFrame columns
    df_columns = [column_name.lower() for column_name in dataset[0]]

    # Make DataFrame data
    df_data = dataset[1:]

    # Make DataFrame
    logging.info('Make DataFrame')
    df = pd.DataFrame(data=df_data, columns=df_columns)
    df = df.astype(int)
    df.set_index(census_code, inplace=True)
    df.sort_index(inplace=True)

    if output_path is None:
        return df

    else:
        file_name = file_path.stem.split('\\')[1]
        logging.info(f"Save data to {output_path.joinpath(f'{file_name}.csv')}")
        df.to_csv(path_or_buf=output_path.joinpath(f'{file_name}.csv'), sep=';')


def make_tracciato(
        file_path: Union[Path, PosixPath],
        year: int,
        output_path: Union[Path, PosixPath],
) -> Union[Path, PosixPath]:
    """Make tracciato

    Args:
        file_path: Union[Path, PosixPath]
        year: int
        output_path: Union[Path, PosixPath]

    Returns:
        Union[Path, PosixPath]
    """
    logging.info(f'Read data from {file_path}')
    read_data = xlrd.open_workbook(file_path)

    get_sheet = read_data.sheet_by_name('Metadati')

    dataset = []
    for row_id in range(get_sheet.nrows):
        dataset.append(get_sheet.row_values(row_id)[:2])
    dataset = dataset[7:]

    # Make DataFrame columns
    df_columns = [column_name for column_name in dataset[0]]

    # Make DataFrame data
    df_data = dataset[1:]

    df = pd.DataFrame(data=df_data, columns=df_columns)
    df.set_index('NOME CAMPO', inplace=True)

    file_name = f'tracciato_{year}_sezioni.csv'
    logging.info(f"Save data to {output_path.joinpath(file_name)}")
    df.to_csv(output_path.joinpath(file_name))


def remove_xls(
        folder_path: Union[Path, PosixPath],
        census_code: str,
        output_path: Union[Path, PosixPath]
):
    files_path = list(folder_path.rglob("*.xls"))

    # Convert xls to csv
    for file_path in files_path:
        read_xls(
            file_path=file_path,
            census_code=census_code,
            output_path=output_path
        )

    # Remove xls
    for file_path in files_path:
        os.remove(file_path)


def compare_dataframe(data: list) -> DataFrame:

    df_list = []
    for file_data in data:

        df_csv = pd.read_csv(file_data)
        df_csv = df_csv.iloc[7:, 0:2]
        df_csv.rename(columns={'Unnamed: 0': 'nome_campo', 'Unnamed: 1': 'definizione'}, inplace=True)
        df_csv.set_index('nome_campo', inplace=True)

        name_csv = ['id', file_data.stem]

        df_csv_name = pd.DataFrame([name_csv], columns=['nome_campo', 'definizione'])
        df_csv_name.set_index('nome_campo', inplace=True)

        data_df = pd.concat([df_csv, df_csv_name])

        data_df_t = data_df.transpose()
        data_df_t.set_index('id', inplace=True)
        data_df_t.columns = data_df_t.columns.str.lower()

        df_list.append(data_df_t)

    df = pd.concat(df_list)
    df.sort_index(inplace=True)

    return df


def preprocess_csv_1991_2001(
        census_year: int,
        output_path: Union[Path, PosixPath],
        census_data_folder: Union[Path, PosixPath]
):
    # Make preprocess folder
    processing_folder = output_path.joinpath(PREPROCESSING_FOLDER)
    Path(processing_folder).mkdir(parents=True, exist_ok=True)

    # Read metadata
    processing_file_list = get_metadata(input_path=census_data_folder, output_path=processing_folder)

    # Compare DataFrame
    df = compare_dataframe(data=processing_file_list)
    df.to_csv(processing_folder.joinpath(f'check_metadata_{census_year}.csv'))


def merge_data_1991_2001(
        csv_path: Union[Path, PosixPath],
        year: int,
        separator: str = ';',
        output_path: Union[Path, PosixPath] = None,
) -> Union[Path, PosixPath, DataFrame]:
    administrative_boundaries = csv_path.parent.parent.joinpath(BOUNDARIES_DATA_FOLDER)

    if year == 1991:
        municipality_path = administrative_boundaries.joinpath(f'Limiti{year}')
    elif year == 2001:
        municipality_path = administrative_boundaries.joinpath(f'Limiti{year}').joinpath(f'Limiti{year}')
    else:
        pass

    target_data = list(municipality_path.rglob('*.xls'))

    if len(target_data) > 1:
        raise Exception(f'Only one Excel file must be present in folder {municipality_path}')

    # Get Municipality data
    municipality_data = _merge_administrative_data(data_path=target_data[0], year=year)
    municipality_data.columns = municipality_data.columns.str.lower()

    # Get census data
    census_data = merge_data(
        csv_path=csv_path,
        year=year,
        separator=separator
    )
    # Dask DataFrame to Pandas DataFrame
    census_data = census_data.compute()

    # Join all
    join_data = pd.merge(
        left=census_data,
        right=municipality_data,
        on='pro_com'
    )

    if output_path is None:
        # Pandas DataFrame to Dask DataFrame
        return join_data.from_pandas()

    else:
        output_data = output_path.joinpath(f'data{year}.csv')
        logging.info(f'Save data to {output_data}')
        join_data.to_csv(output_data, sep=separator, index=False)


def _merge_administrative_data(data_path: Union[Path, PosixPath], year: int) -> DataFrame:
    # Get Municipality data
    municipality_data = pd.read_excel(data_path, sheet_name=f'Comuni{year}')
    municipality_data = municipality_data[['COD_REG', 'COD_PROV', 'PRO_COM', 'COMUNE']]

    # Get regional and subregional data
    other_data = pd.read_excel(data_path, sheet_name=f'RipRegProv{year}')
    other_data = other_data[['COD_REG', 'DEN_REG', 'COD_PROV', 'DEN_PROV']]

    # Join all
    administrative_data = pd.merge(
        left=municipality_data,
        right=other_data,
        on='COD_PROV',
    )
    administrative_data.drop(columns={'COD_REG_x'}, inplace=True)
    administrative_data.rename(columns={'COD_REG_y': 'COD_REG'}, inplace=True)
    administrative_data = administrative_data[['COD_REG', 'DEN_REG', 'COD_PROV', 'DEN_PROV', 'PRO_COM', 'COMUNE']]

    return administrative_data
