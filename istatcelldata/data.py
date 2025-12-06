import logging
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from istatcelldata.census1991.process import add_administrative_info
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def preprocess_data(
    data_folder: Path,
    data_column_remapping: dict | None = None,
    add_administrative_informations: bool | None = None,
    regions_data_path: Path | None = None,
    regions_target_columns: list | None = None,
    provinces_data_path: Path | None = None,
    provinces_target_columns: list | None = None,
    municipalities_data_path: Path | None = None,
    municipalities_target_columns: list | None = None,
    output_folder: Path | None = None,
) -> dict | Path:
    """Preprocess census CSV files and return aggregated data and trace record.

    This function performs the following operations:

    1. Searches for all CSV files in the specified folder.
    2. Uses the last CSV file (in alphabetical order) as the trace record file.
    3. Loads and concatenates all other CSV files into a single DataFrame.
    4. Applies column name remapping if `data_column_remapping` is provided.
    5. Adds administrative information (regions, provinces, municipalities) if requested.
    6. Replaces any NaN values with 0.
    7. Loads the trace record file into a dedicated DataFrame.
    8. Returns either:
       - A dictionary containing `census_data` and `trace` DataFrames, or
       - Saves the resulting CSV files to `output_folder` and returns the path.

    Args:
        data_folder: Folder containing the CSV files to process.
        data_column_remapping: Optional dictionary for renaming census dataset columns
            (e.g., `{"pro_com": "PRO_COM"}`).
        add_administrative_informations: If True, enriches data with administrative
            information (regions, provinces, municipalities) via `add_administrative_info()`.
        regions_data_path: Optional path to the file containing region data.
        regions_target_columns: Optional list of columns to extract/keep for region data.
        provinces_data_path: Optional path to the file containing province data.
        provinces_target_columns: Optional list of columns to extract/keep for province data.
        municipalities_data_path: Optional path to the file containing municipality data.
        municipalities_target_columns: Optional list of columns to extract/keep for
            municipality data.
        output_folder: Optional destination folder where the following files will be saved:
            - `census_data.csv` for concatenated data
            - `census_trace.csv` for the trace record
            If None, data is returned as a dictionary of DataFrames.

    Returns:
        Either a dictionary with keys:
            - `"census_data"`: DataFrame containing concatenated census data
            - `"trace"`: DataFrame containing field trace record
        Or the path to `output_folder` if specified, where `census_data.csv` and
        `census_trace.csv` have been saved.

    Raises:
        ValueError: If no CSV files are found in the specified folder.

    Note:
        The trace record file is considered to be the last CSV in alphabetical
        order within `data_folder`. The `check_encoding()` function is used to
        determine the correct encoding for CSV files.
    """
    logging.info(f"Starting data preprocessing in folder {data_folder}")

    # Find and sort all CSV files in the specified folder
    csv_list = sorted(list(data_folder.glob("*.csv")))

    if not csv_list:
        raise ValueError(f"No CSV files found in folder {data_folder}")

    logging.info(f"Found {len(csv_list)} CSV files")

    # Last CSV file considered as "trace"
    trace = csv_list[-1]
    logging.info(f"Trace file selected: {trace}")

    data_list = []

    # Iterate through CSV files and load data
    for csv in tqdm(csv_list, desc="Reading CSV files..."):
        if csv != trace:
            logging.info(f"Processing file: {csv}")

            # Read CSV file
            read_csv = pd.read_csv(
                filepath_or_buffer=csv, sep=";", encoding=check_encoding(data=csv)
            )
            data_list.append(read_csv)

    # Concatenate all loaded data into a single DataFrame
    df = pd.concat(data_list, ignore_index=True)
    if data_column_remapping is not None:
        df.rename(columns=data_column_remapping, inplace=True)

    if add_administrative_informations:
        if (regions_data_path is None or regions_target_columns is None or
            provinces_data_path is None or provinces_target_columns is None or
            municipalities_data_path is None or municipalities_target_columns is None):
            raise ValueError(
                "Administrative data paths and columns are required when "
                "add_administrative_informations is True"
            )
        df = add_administrative_info(
            census_data=df,
            regions_data_path=regions_data_path,
            regions_target_columns=regions_target_columns,
            provinces_data_path=provinces_data_path,
            provinces_target_columns=provinces_target_columns,
            municipalities_data_path=municipalities_data_path,
            municipalities_target_columns=municipalities_target_columns,
        )
    df.fillna(value=0, inplace=True)
    logging.info("Data concatenated successfully")

    # Read trace file
    trace_df = pd.read_csv(filepath_or_buffer=trace, sep=";", encoding=check_encoding(data=trace))
    logging.info(f"Trace file read successfully: {trace}")

    logging.info("Preprocessing completed successfully.")
    if output_folder is not None:
        logging.info("Saving files...")
        census_file_path = output_folder.joinpath("census_data.csv")
        df.to_csv(census_file_path, index=False, sep=";")

        trace_file_path = output_folder.joinpath("census_trace.csv")
        trace_df.to_csv(trace_file_path, index=False, sep=";")

        return output_folder

    else:
        # Return dictionary with concatenated data and trace file
        result = {
            "census_data": df,
            "trace": trace_df,
        }
        return result
