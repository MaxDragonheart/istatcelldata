import datetime
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import List

from istatcelldata.config import census_data, YEAR_GEODATA_NAME, GLOBAL_ENCODING
from istatcelldata.data import preprocess_data
from istatcelldata.geodata import preprocess_geodata
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

def preprocess_census(
        processed_data_folder: Path,
        years: List[int],
        regions: bool = False,
        provinces: bool = False,
        municipalities: bool = False,
        output_data_folder: Path = None,
        delete_download_folder: bool = False,
):
    """Preprocessa i dati del censimento per più anni, includendo l'opzione di processare anche
    i confini amministrativi.

    Args:
        processed_data_folder (Path): Cartella contenente i dati pre-processati.
        years (List[int]): Lista degli anni del censimento da processare.
        regions (bool, opzionale): Se True, processa i confini regionali. Default: False.
        provinces (bool, opzionale): Se True, processa i confini provinciali. Default: False.
        municipalities (bool, opzionale): Se True, processa i confini comunali. Default: False.
        output_data_folder (Path, opzionale): Cartella di destinazione per i dati elaborati. Default: None.
        delete_download_folder (bool, opzionale): Se True, elimina la cartella di dati pre-processati dopo
        il completamento del download. Default: False.

    Returns:
        Path: Percorso della cartella con i dati elaborati.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Inizio preprocessing del censimento alle {time_start} per gli anni: {years}")

    # Se non viene fornita una cartella di output, utilizza la cartella padre di quella di elaborazione
    if output_data_folder is None:
        output_data_folder = processed_data_folder.parent

    logging.info(f"Cartella di output: {output_data_folder}")

    # Cicla attraverso gli anni forniti e preprocessa i dati per ciascun anno
    for year in years:
        logging.info(f"\n\n\nProcessamento dei dati per l'anno {year}")

        census_layer_name = f"{YEAR_GEODATA_NAME}{year}"

        # Estrae i percorsi e le colonne dal dizionario census_data per l'anno corrente
        data_root = census_data[year]['data_root']
        regions_root = census_data[year]['regions_root']
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
        add_administrative_informations = census_data[year].get('add_administrative_informations', None)

        # Preprocessa i dati geografici del censimento e i confini amministrativi
        logging.info(f"Preprocessamento dei dati geografici.")
        geodata_path = preprocess_geodata(
            census_shp_folder=processed_data_folder.joinpath(*census_shp_root),
            census_target_columns=census_shp_column,
            census_tipo_loc_mapping=tipo_loc_mapping,
            output_folder=output_data_folder,
            census_layer_name=census_layer_name,
            census_column_remapping=census_shp_column_remapping,
            regions=regions,
            regions_file_path=processed_data_folder.joinpath(*regions_root),
            regions_target_columns=regions_column,
            regions_index_column=regions_column[0],
            regions_column_remapping=regions_column_remapping,
            provinces=provinces,
            provinces_file_path=processed_data_folder.joinpath(*provinces_root),
            provinces_target_columns=provinces_column,
            provinces_index_column=provinces_column[0],
            provinces_column_remapping=provinces_column_remapping,
            municipalities=municipalities,
            municipalities_file_path=processed_data_folder.joinpath(*municipalities_root),
            municipalities_target_columns=municipalities_column,
            municipalities_index_column=municipalities_column[0],
            municipalities_column_remapping=municipalities_column_remapping
        )

        # Connessione al GeoPackage
        connection = sqlite3.connect(geodata_path)

        # Preprocessamento dei dati non geografici (CSV)
        logging.info(f"Preprocessamento dei dati non geografici.")
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

        # Salvataggio dei dati nel GeoPackage
        data = get_census_data['census_data']
        data_layer_name = f"data{year}"
        logging.info(f"Salvataggio dei dati non geografici.")
        data.to_sql(name=data_layer_name, con=connection, if_exists='replace')
        logging.info(f"Salvataggio dei dati non geografici effettuato.")

        # Salvataggio del file di trace nel GeoPackage
        trace = get_census_data['trace']
        trace_layer_name = f"tracciato{year}"
        logging.info(f"Salvataggio del tracciato dati non geografici.")
        trace.to_sql(name=trace_layer_name, con=connection, if_exists='replace')
        logging.info(f"Salvataggio del tracciato dati non geografici effettuato.")

        logging.info(f"Dati per l'anno {year} processati e salvati con successo nel GeoPackage")

    # Eliminazione della cartella dei dati pre-processati, se richiesto
    if delete_download_folder:
        logging.info(f"Eliminazione della cartella dei dati pre-processati: {processed_data_folder}")
        shutil.rmtree(processed_data_folder)

    time_end = datetime.datetime.now()
    elapsed_time = time_end - time_start
    logging.info(f"Preprocessing completato in {elapsed_time}. Dati salvati in {output_data_folder}")

    return output_data_folder
