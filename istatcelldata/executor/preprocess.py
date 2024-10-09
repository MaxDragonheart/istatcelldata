import logging
from pathlib import Path
from typing import List

from istatcelldata.config import census_data, YEAR_GEODATA_NAME
from istatcelldata.geodata import preprocess_geodata
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

def preprocess_census(
        processed_data_dir: Path,
        years: List[int],
        output_data_folder: Path,
        regions: bool = False,
        provinces: bool = False,
        municipalities: bool = False
):
    for year in years:
        # TODO
        # data
        print(year)
        census_layer_name = f"{YEAR_GEODATA_NAME}{year}"
        regions_root = census_data[year].get('regions_root', None)
        regions_column = census_data[year].get('regions_column', None)
        regions_column_remapping = census_data[year].get('regions_column_remapping', None)
        provinces_root = census_data[year].get('provinces_root', None)
        provinces_column = census_data[year].get('provinces_column', None)
        provinces_column_remapping = census_data[year].get('provinces_column_remapping', None)
        municipalities_root = census_data[year].get('municipalities_root', None)
        municipalities_column = census_data[year].get('municipalities_column', None)
        municipalities_column_remapping = census_data[year].get('municipalities_column_remapping', None)
        census_shp_root = census_data[year].get('census_shp_root', None)
        census_shp_column = census_data[year].get('census_shp_column', None)
        census_shp_column_remapping = census_data[year].get('census_shp_column_remapping', None)
        tipo_loc_mapping = census_data[year].get('tipo_loc_mapping', None)

        preprocess_geodata(
            census_shp_folder=processed_data_dir.joinpath(*census_shp_root),
            census_target_columns=census_shp_column,
            census_tipo_loc_mapping=tipo_loc_mapping,
            output_folder=output_data_folder,
            census_layer_name=census_layer_name,
            census_column_remapping=census_shp_column_remapping,
            regions=regions,
            regions_file_path=processed_data_dir.joinpath(*regions_root),
            regions_target_columns=regions_column,
            regions_index_column=regions_column[0],
            regions_column_remapping=regions_column_remapping,
            provinces=provinces,
            provinces_file_path=processed_data_dir.joinpath(*provinces_root),
            provinces_target_columns=provinces_column,
            provinces_index_column=provinces_column[0],
            provinces_column_remapping=provinces_column_remapping,
            municipalities=municipalities,
            municipalities_file_path=processed_data_dir.joinpath(*municipalities_root),
            municipalities_target_columns=municipalities_column,
            municipalities_index_column=municipalities_column[0],
            municipalities_column_remapping=municipalities_column_remapping
        )

    return output_data_folder