import logging
from pathlib import Path

import pandas as pd
import xlrd
from tqdm import tqdm


def read_xls(
    file_path: Path,
    census_code: str,
    output_path: Path | None = None,
) -> pd.DataFrame | Path:
    """Read an Excel file (.xls) and return a DataFrame or save data as CSV.

    This function opens an Excel file in `.xls` format, automatically selects
    the first useful sheet (excluding any sheets named "Metadati"), extracts
    the sheet rows, constructs a pandas DataFrame, and sets as index the column
    corresponding to the provided census code.

    If an output path is specified, the DataFrame is saved in CSV format;
    otherwise, it is returned directly.

    Args:
        file_path: Path to the Excel file to read.
        census_code: Name of the column to use as the DataFrame index
            (e.g., ISTAT municipality code).
        output_path: Path to the folder where the resulting CSV will be saved.
            If None, the DataFrame is returned without saving.

    Returns:
        A DataFrame containing data read from the Excel file if `output_path`
        is None, or the path to the saved CSV file if `output_path` is specified.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        xlrd.XLRDError: If an error occurs while reading the Excel file.
        Exception: For any unexpected error during parsing or saving.
    """
    try:
        logging.info(f"Lettura del file Excel da {file_path}")

        # Legge il file Excel
        read_data = xlrd.open_workbook(file_path)

        # Estrae il nome del foglio, ignorando 'Metadati'
        sheet_list = read_data.sheet_names()
        if "Metadati" in sheet_list:
            sheet_list.remove("Metadati")
        sheet_name = sheet_list[0]
        get_sheet = read_data.sheet_by_name(sheet_name)

        # Estrae i dati dal foglio
        dataset = []
        for row_id in tqdm(range(get_sheet.nrows), desc="Lettura righe..."):
            dataset.append(get_sheet.row_values(row_id))

        # Crea il DataFrame
        df_columns = [column_name.lower() for column_name in dataset[0]]
        df_data = dataset[1:]
        df = pd.DataFrame(data=df_data, columns=df_columns)

        # Imposta il tipo di dati e l'indice
        df = df.astype(int)
        df.set_index(census_code, inplace=True)
        df.sort_index(inplace=True)

        # Se non viene fornito un percorso di output, restituisce il DataFrame
        if output_path is None:
            return df
        else:
            file_name = file_path.stem.split("\\")[1]
            logging.info(f"Salvataggio dei dati in {output_path.joinpath(f'{file_name}.csv')}")
            df.to_csv(path_or_buf=output_path.joinpath(f"{file_name}.csv"), sep=";")
            return output_path.joinpath(
                f"{file_name}.csv"
            )  # Restituisce il percorso del file CSV salvato

    except FileNotFoundError as e:
        logging.error(f"Excel file not found: {file_path}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Error reading Excel file: {str(e)}")
        raise e
    except Exception as e:
        logging.error(
            f"Error reading Excel file or saving data: {str(e)}"
        )
        raise e


def census_trace(file_path: Path, year: int, output_path: Path | None = None) -> Path:
    """Extract metadata trace record from the "Metadati" sheet of an Excel file.

    This function accesses the sheet named **"Metadati"** in an Excel file
    related to census data, extracts the fundamental columns (field name and
    description), and constructs a pandas DataFrame with an index based on the
    field name. If an output path is provided, the trace record is also saved
    in CSV format.

    Args:
        file_path: Path to the Excel file from which to extract metadata.
        year: Reference year for the census, used to generate the output file name.
        output_path: Path to the folder where the trace record CSV will be saved.
            If None, a DataFrame is returned directly.

    Returns:
        Path to the generated CSV file if `output_path` is provided, or a pandas
        DataFrame containing the metadata trace record if `output_path` is None.

    Raises:
        FileNotFoundError: If the specified Excel file does not exist.
        xlrd.XLRDError: If an error occurs while opening or reading the Excel file.
        Exception: For any unexpected errors during parsing or saving.
    """
    try:
        logging.info(f"Lettura dei dati da {file_path}")
        read_data = xlrd.open_workbook(file_path)

        get_sheet = read_data.sheet_by_name("Metadati")

        dataset = []
        for row_id in range(get_sheet.nrows):
            dataset.append(get_sheet.row_values(row_id)[:2])
        dataset = dataset[7:]  # Ignora le prime 7 righe

        # Crea le colonne del DataFrame
        df_columns = [column_name for column_name in dataset[0]]

        # Crea i dati del DataFrame
        df_data = dataset[1:]
        df = pd.DataFrame(data=df_data, columns=df_columns)
        df.set_index("NOME CAMPO", inplace=True)

        logging.info("Dati letti con successo.")

        if output_path is None:
            return df
        else:
            file_name = f"tracciato_{year}_sezioni.csv"
            logging.info(f"Salvataggio dei dati in {output_path.joinpath(file_name)}")
            df.to_csv(path_or_buf=output_path.joinpath(file_name), sep=";")
            return output_path.joinpath(file_name)  # Restituisce il percorso del file CSV salvato

    except FileNotFoundError as e:
        logging.error(f"Excel file not found: {file_path}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Error reading Excel file: {str(e)}")
        raise e
    except Exception as e:
        logging.error(
            f"Error reading Excel file or saving data: {str(e)}"
        )
        raise e
