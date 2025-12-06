import logging
from pathlib import Path

import pandas as pd

from istatcelldata.geodata import read_administrative_boundaries
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def add_administrative_info(
    census_data: pd.DataFrame,
    regions_data_path: Path,
    regions_target_columns: list,
    provinces_data_path: Path,
    provinces_target_columns: list,
    municipalities_data_path: Path,
    municipalities_target_columns: list,
) -> pd.DataFrame:
    """Enrich census data with administrative information (municipalities, provinces, regions).

    This function integrates corresponding administrative codes and names into the
    census data, sourced from three external datasets: regional, provincial, and
    municipal boundaries.

    The logical workflow includes:
    1. Standardization of census dataset column names.
    2. Reading of administrative datasets (regions, provinces, municipalities).
    3. Merge of municipalities with provinces.
    4. Merge of result with regions.
    5. Final join with census dataset on the municipal key (`PRO_COM`).
    6. Cleanup and renaming of final administrative columns.

    Args:
        census_data: Census dataset to which administrative information will be added.
        regions_data_path: Path to the file containing regional data.
        regions_target_columns: List of columns to extract from the regional dataset
            (the first column is used as the index).
        provinces_data_path: Path to the file containing provincial data.
        provinces_target_columns: List of columns to extract from the provincial dataset
            (the first column is used as the index).
        municipalities_data_path: Path to the file containing municipal data.
        municipalities_target_columns: List of columns to extract from the municipal
            dataset (the first column is used as the index).

    Returns:
        Census DataFrame enriched with administrative information on municipalities,
        provinces, and regions.

    Note:
        Administrative codes used for merges are assumed to be:
        `PRO_COM` (municipality), `COD_PROV`/`COD_PRO` (province), `COD_REG` (region).
        The function uses `read_administrative_boundaries()` to load and filter
        administrative datasets.
    """
    logging.info("Starting to add administrative information to census data.")

    # Convert census column names to uppercase for uniformity
    census_data.columns = census_data.columns.str.upper()
    logging.info("Census dataset column names converted to uppercase.")

    # Read regional administrative boundaries
    logging.info(f"Reading regional data from {regions_data_path}")
    regions_data = read_administrative_boundaries(
        file_path=regions_data_path,
        target_columns=regions_target_columns,
        index_column=regions_target_columns[0],
    )
    if isinstance(regions_data, Path):
        raise ValueError("Expected DataFrame but got Path from read_administrative_boundaries")
    regions_data.reset_index(inplace=True)
    logging.info(f"Regional data read successfully. {len(regions_data)} records found.")

    # Read provincial administrative boundaries
    logging.info(f"Reading provincial data from {provinces_data_path}")
    provinces_data = read_administrative_boundaries(
        file_path=provinces_data_path,
        target_columns=provinces_target_columns,
        index_column=provinces_target_columns[0],
    )
    if isinstance(provinces_data, Path):
        raise ValueError("Expected DataFrame but got Path from read_administrative_boundaries")
    provinces_data.reset_index(inplace=True)
    logging.info(f"Provincial data read successfully. {len(provinces_data)} records found.")

    # Read municipal administrative boundaries
    logging.info(f"Reading municipal data from {municipalities_data_path}")
    municipalities_data = read_administrative_boundaries(
        file_path=municipalities_data_path,
        target_columns=municipalities_target_columns,
        index_column=municipalities_target_columns[0],
    )
    if isinstance(municipalities_data, Path):
        raise ValueError("Expected DataFrame but got Path from read_administrative_boundaries")
    municipalities_data.reset_index(inplace=True)
    logging.info(f"Municipal data read successfully. {len(municipalities_data)} records found.")

    # Merge municipal data with provincial data
    logging.info("Starting merge between municipal and provincial data.")
    add_provinces = pd.merge(
        left=municipalities_data, right=provinces_data, how="left", on="COD_PROV"
    )
    logging.info(
        f"Merge between municipalities and provinces completed. "
        f"{len(add_provinces)} resulting records."
    )

    # Merge resulting data with regional data
    logging.info("Starting merge between municipal-provincial and regional data.")
    add_regions = pd.merge(left=add_provinces, right=regions_data, how="left", on="COD_REG")
    logging.info(
        f"Merge between municipalities, provinces and regions completed. "
        f"{len(add_regions)} resulting records."
    )

    # Final merge of census data with added administrative information
    logging.info("Starting final merge with census data.")
    add_municipalities = pd.merge(left=census_data, right=add_regions, how="left", on="PRO_COM")
    logging.info(f"Final merge completed. {len(add_municipalities)} records in final dataset.")
    add_municipalities.drop(columns=["COD_PRO", "PRO_COM"], inplace=True)
    add_municipalities.rename(
        columns={
            "COD_COM": "CODCOM",
            "COD_PROV": "CODPRO",
            "COD_REG": "CODREG",
            "DEN_PROV": "PROVINCIA",
            "DEN_REG": "REGIONE",
        },
        inplace=True,
    )

    logging.info("Addition of administrative information completed successfully.")

    return add_municipalities
