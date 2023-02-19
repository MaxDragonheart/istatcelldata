from pathlib import Path, PosixPath
from typing import Union

import pandas as pd
from pandas import DataFrame

from census_istat.generic import get_metadata


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
    processing_folder = output_path.joinpath('preprocessing')
    Path(processing_folder).mkdir(parents=True, exist_ok=True)

    # Read metadata
    processing_file_list = get_metadata(input_path=census_data_folder, output_path=processing_folder)

    # Compare DataFrame
    df = compare_dataframe(data=processing_file_list)
    df.to_csv(processing_folder.joinpath(f'check_metadata_{census_year}.csv'))
