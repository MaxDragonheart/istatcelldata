import datetime
import logging
import shutil
import sqlite3
from pathlib import Path

from istatcelldata.config import YEAR_GEODATA_NAME, census_data
from istatcelldata.data import preprocess_data
from istatcelldata.geodata import preprocess_geodata
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def preprocess_census(
    processed_data_folder: Path,
    years: list[int],
    output_data_folder: Path | None = None,
    delete_download_folder: bool = False,
    municipalities_code: list[int] = [],
) -> Path:
    """Preprocess census data for one or more years, integrating geodata, boundaries, and tables.

    This function coordinates the entire census preprocessing workflow, executing
    for each requested year:

    1. Preprocessing of geographic data (shapefiles or similar).
    2. Preprocessing of tabular data (CSV).
    3. Addition of administrative information (optional).
    4. Saving of resulting data into a GeoPackage.
    5. Optional deletion of the pre-processed data folder.

    Required inputs are read from the `census_data` configuration dictionary, which
    defines paths, columns, mappings, and specific settings for each census year.

    Args:
        processed_data_folder: Folder containing pre-downloaded or pre-processed data
            (geodata, tabular data, administrative boundaries).
        years: List of census years to process (e.g., [1991, 2001, 2011, 2021]).
        output_data_folder: Optional folder where processed data will be saved
            (GeoPackage and associated layers). If None, the parent folder of
            `processed_data_folder` is used.
        delete_download_folder: If True, deletes the `processed_data_folder` at
            the end of the process.
        municipalities_code: Optional list of ISTAT municipality codes to filter
            in the data (`PRO_COM` key). If empty, all available municipalities
            are used.

    Returns:
        Path to the final folder containing the processed data.

    Raises:
        KeyError: If the `census_data` dictionary does not contain configuration
            for a requested year.
        Exception: For any errors during reading, preprocessing, or saving.

    Note:
        The GeoPackage file is opened and written via `sqlite3.connect()`.
        Layers inserted into the GeoPackage follow conventions such as:
        - `sezioni<year>` for the geographic layer
        - `data<year>` for the tabular dataset
        - `tracciato<year>` for the field trace record
        The `municipalities_code` parameter is applied during the geodata phase.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Starting census preprocessing at {time_start} for years: {years}")

    # If no output folder is provided, use the parent folder
    # of the processing folder
    if output_data_folder is None:
        output_data_folder = processed_data_folder.parent

    logging.info(f"Output folder: {output_data_folder}")

    # Loop through the provided years and preprocess data for each year
    for year in years:
        logging.info(f"\n\n\nProcessing data for year {year}")

        census_layer_name = f"{YEAR_GEODATA_NAME}{year}"

        # Extract paths and columns from census_data dictionary for the current year
        data_root = census_data[year]["data_root"]
        regions_root = census_data[year]["regions_root"]
        regions_column = census_data[year]["regions_column"]
        regions_column_remapping = census_data[year].get("regions_column_remapping", None)
        regions_index = census_data[year]["regions_index"]
        provinces_root = census_data[year].get("provinces_root", None)
        provinces_column = census_data[year].get("provinces_column", None)
        provinces_column_remapping = census_data[year].get("provinces_column_remapping", None)
        provinces_index = census_data[year]["provinces_index"]
        municipalities_root = census_data[year].get("municipalities_root", None)
        municipalities_column = census_data[year].get("municipalities_column", None)
        municipalities_column_remapping = census_data[year].get(
            "municipalities_column_remapping", None
        )
        municipalities_index = census_data[year]["municipalities_index"]
        census_shp_root = census_data[year].get("census_shp_root", None)
        census_shp_column = census_data[year].get("census_shp_column", None)
        census_shp_column_remapping = census_data[year].get("census_shp_column_remapping", None)
        tipo_loc_mapping = census_data[year].get("tipo_loc_mapping", None)
        add_administrative_informations = census_data[year].get(
            "add_administrative_informations", None
        )

        # Preprocess census geodata and administrative boundaries
        logging.info("Preprocessing geodata.")
        geodata_path = preprocess_geodata(
            census_shp_folder=processed_data_folder.joinpath(*census_shp_root),
            census_target_columns=census_shp_column,
            census_tipo_loc_mapping=tipo_loc_mapping,
            output_folder=output_data_folder,
            census_layer_name=census_layer_name,
            census_column_remapping=census_shp_column_remapping,
            regions_file_path=processed_data_folder.joinpath(*regions_root),
            regions_target_columns=regions_column,
            regions_index_column=regions_index,
            regions_column_remapping=regions_column_remapping,
            provinces_file_path=processed_data_folder.joinpath(*provinces_root),
            provinces_target_columns=provinces_column,
            provinces_index_column=provinces_index,
            provinces_column_remapping=provinces_column_remapping,
            municipalities_file_path=processed_data_folder.joinpath(*municipalities_root),
            municipalities_target_columns=municipalities_column,
            municipalities_index_column=municipalities_index,
            municipalities_column_remapping=municipalities_column_remapping,
            municipalities_code=municipalities_code,
        )

        # Connect to GeoPackage
        connection = sqlite3.connect(geodata_path)

        # Preprocess non-geographic data (CSV)
        logging.info("Preprocessing non-geographic data.")
        get_census_data = preprocess_data(
            data_folder=processed_data_folder.joinpath(*data_root),
            data_column_remapping=census_shp_column_remapping,
            add_administrative_informations=add_administrative_informations,
            regions_data_path=processed_data_folder.joinpath(*regions_root),
            regions_target_columns=regions_column,
            provinces_data_path=processed_data_folder.joinpath(*provinces_root),
            provinces_target_columns=provinces_column,
            municipalities_data_path=processed_data_folder.joinpath(*municipalities_root),
            municipalities_target_columns=municipalities_column,
        )

        # Save data to GeoPackage
        data = get_census_data["census_data"]
        data_layer_name = f"data{year}"
        logging.info("Saving non-geographic data.")
        data.to_sql(name=data_layer_name, con=connection, if_exists="replace")
        logging.info("Non-geographic data saved successfully.")

        # Save trace file to GeoPackage
        trace = get_census_data["trace"]
        trace_layer_name = f"tracciato{year}"
        logging.info("Saving non-geographic data trace record.")
        trace.to_sql(name=trace_layer_name, con=connection, if_exists="replace")
        logging.info("Non-geographic data trace record saved successfully.")

        logging.info(f"Data for year {year} processed and saved successfully to GeoPackage")

    # Delete pre-processed data folder if requested
    if delete_download_folder:
        logging.info(
            f"Deleting pre-processed data folder: {processed_data_folder}"
        )
        shutil.rmtree(processed_data_folder)

    time_end = datetime.datetime.now()
    elapsed_time = time_end - time_start
    logging.info(
        f"Preprocessing completed in {elapsed_time}. Data saved to {output_data_folder}"
    )

    return output_data_folder
