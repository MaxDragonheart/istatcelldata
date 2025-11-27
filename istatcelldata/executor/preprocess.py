import datetime
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import List

from istatcelldata.config import census_data, YEAR_GEODATA_NAME
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
        output_data_folder: Path = None,
        delete_download_folder: bool = False,
        municipalities_code: list[int] = []
):
    """Preprocessa i dati censuari per uno o più anni, integrando geodati,
    confini amministrativi e dati tabellari.

    La funzione coordina l’intero workflow di preprocessing dei censimenti,
    eseguendo per ciascun anno richiesto:

    1. Preprocessing dei dati geografici (shapefile/simili).
    2. Preprocessing dei dati tabellari (CSV).
    3. Aggiunta delle informazioni amministrative (opzionale).
    4. Salvataggio dei dati risultanti all’interno di un GeoPackage.
    5. Eventuale eliminazione della cartella dei dati pre-processati.

    Gli input necessari vengono letti dal dizionario di configurazione
    `census_data`, che definisce paths, colonne, mapping e impostazioni specifiche
    per ogni anno censuario.

    Args:
        processed_data_folder (Path):
            Cartella contenente i dati pre-scaricati o pre-processati
            (geodati, dati tabellari, confini amministrativi).
        years (List[int]):
            Lista degli anni di censimento da processare (es. [1991, 2001, 2011, 2021]).
        output_data_folder (Path, optional):
            Cartella in cui salvare i dati elaborati (GeoPackage e layer associati).
            Se None, viene utilizzata la cartella padre di `processed_data_folder`.
        delete_download_folder (bool, optional):
            Se True, elimina la cartella `processed_data_folder` al termine del processo.
        municipalities_code (list[int], optional):
            Lista di codici ISTAT dei comuni da filtrare nei dati (chiave `PRO_COM`).
            Se vuota, vengono usati tutti i comuni disponibili.

    Returns:
        Path:
            Percorso della cartella finale che contiene i dati elaborati.

    Raises:
        KeyError:
            Se il dizionario `census_data` non contiene la configurazione per un anno richiesto.
        Exception:
            Per eventuali errori durante la lettura, il preprocessing o il salvataggio.

    Notes:
        - Il file GeoPackage è aperto e scritto tramite `sqlite3.connect()`.
        - I layer inseriti nel GeoPackage seguono convenzioni come:
            - `sezioni<anno>` per il layer geografico
            - `data<anno>` per il dataset tabellare
            - `tracciato<anno>` per il tracciato dei campi
        - Il parametro `municipalities_code` viene applicato nella fase dei geodati.
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
        regions_column = census_data[year]['regions_column']
        regions_column_remapping = census_data[year].get('regions_column_remapping', None)
        regions_index = census_data[year]['regions_index']
        provinces_root = census_data[year].get('provinces_root', None)
        provinces_column = census_data[year].get('provinces_column', None)
        provinces_column_remapping = census_data[year].get('provinces_column_remapping', None)
        provinces_index = census_data[year]['provinces_index']
        municipalities_root = census_data[year].get('municipalities_root', None)
        municipalities_column = census_data[year].get('municipalities_column', None)
        municipalities_column_remapping = census_data[year].get('municipalities_column_remapping', None)
        municipalities_index = census_data[year]['municipalities_index']
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
            municipalities_code=municipalities_code
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
