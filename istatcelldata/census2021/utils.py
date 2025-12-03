import logging
from pathlib import Path

import pandas as pd

from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def read_xlsx(
    file_path: Path,
    output_path: Path | None = None,
) -> pd.DataFrame | Path:
    """Read an Excel file (XLSX format) and convert to a Pandas DataFrame.

    If specified, saves the data in CSV format.

    Args:
        file_path: Path to the Excel file to read.
        output_path: Path where the generated CSV file will be saved.
            If not specified, returns the DataFrame.

    Returns:
        A DataFrame if `output_path` is None, otherwise returns the path to
        the saved CSV file.

    Raises:
        FileNotFoundError: If the specified Excel file is not found.
        ValueError: If the Excel file cannot be read correctly.
    """
    try:
        logging.info(f"Reading Excel file from {file_path}")
        # Read Excel file using 'openpyxl' engine
        df = pd.read_excel(file_path, engine="openpyxl")

        # If no output path is provided, return DataFrame
        if output_path is None:
            logging.info("Returning DataFrame without saving to disk.")
            return df
        else:
            if file_path.stem[:1] == "R":
                file_name = file_path.stem
                census_data_path = output_path.joinpath(f"{file_name}.csv")
                logging.info(f"Saving data to CSV format at {census_data_path}")
                # Save data to specified path
                df.to_csv(path_or_buf=census_data_path, sep=";", index=False)
                logging.info(f"Data saved successfully to {census_data_path}")
                return census_data_path
            else:
                trace_data_path = output_path.joinpath("tracciato_2021_sezioni.csv")
                logging.info(f"Saving trace data to {trace_data_path}")
                # Save data to specified path
                df.to_csv(path_or_buf=trace_data_path, sep=";", index=False)
                logging.info(f"Data saved successfully to {trace_data_path}")
                return trace_data_path

    except FileNotFoundError as e:
        logging.error(f"File not found: {file_path}")
        raise e
    except ValueError as e:
        logging.error(f"Error reading Excel file: {file_path}. Details: {str(e)}")
        raise e
