import datetime
import logging
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

from istatcelldata.config import census_data
from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)

def finalize_census_data(
        census_data_path: Path,
        years: list,
        output_data_folder: Path = None,
        delete_preprocessed_data: bool = False,
):
    """Finalizza i dati del censimento unendo i dati geografici con i dati tabellari e salva il risultato.

    Args:
        census_data_path (Path): Cartella contenente i dati pre-processati del censimento.
        years (List[int]): Lista degli anni del censimento da processare.
        output_data_folder (Path, opzionale): Cartella di destinazione per i dati finali. Default: None.
        delete_preprocessed_data (bool, opzionale): Se True, elimina i dati pre-processati dopo il completamento.
            Default: False.

    Raises:
        FileNotFoundError: Se il file GeoPackage principale non esiste.
        KeyError: Se non viene trovata la colonna di unione corretta tra i dati.
    """
    time_start = datetime.datetime.now()
    logging.info(f"Inizio preprocessing del censimento alle {time_start} per gli anni: {years}")

    # Percorso del file GeoPackage principale
    main_data = census_data_path.joinpath("census.gpkg")

    for year in years:
        logging.info(f"Inizio finalizzazione dei dati del censimento per l'anno {year}")

        if not main_data.exists():
            error_message = f"File GeoPackage principale non trovato: {main_data}"
            logging.error(error_message)
            raise FileNotFoundError(error_message)

        logging.info(f"Caricamento dei dati geografici dal layer 'census{year}'")
        geodata = gpd.read_file(
            filename=main_data,
            layer=f"census{year}"
        )

        logging.info(f"Caricamento dei dati tabellari dal layer 'data{year}'")
        data = gpd.read_file(
            filename=main_data,
            layer=f"data{year}"
        )
        columns_to_remove = census_data[year]['data_columns_to_remove']
        data.drop(columns=columns_to_remove, inplace=True)

        # Unione dei dati geografici con i dati tabellari
        join_key = f"SEZ{year}"

        if join_key not in geodata.columns or join_key not in data.columns:
            error_message = f"Colonna di unione '{join_key}' non trovata nei dati geografici o tabellari"
            logging.error(error_message)
            raise KeyError(error_message)

        logging.info(f"Unione dei dati sui campi '{join_key}'")
        join_data = pd.merge(
            left=geodata,
            right=data,
            how="left",
            on=join_key,
        )
        join_data.fillna(value=0, inplace=True)

        # Rimozione della colonna "index" e ordinamento dei dati
        if "index" in join_data.columns:
            join_data.drop(columns=["index"], inplace=True)
            logging.info("Colonna 'index' rimossa dai dati")

        join_data.sort_values(by=join_key, inplace=True)
        logging.info(f"Dati ordinati per la colonna '{join_key}'")

        # Creazione del GeoDataFrame finale
        gdf = gpd.GeoDataFrame(data=join_data, geometry=geodata.geometry.name, crs=geodata.crs)

        # Definizione del percorso del file di output
        filename = "census_data.gpkg"
        file_path = output_data_folder.joinpath(filename) if output_data_folder else census_data_path.joinpath(filename)

        # Salvataggio del file finale come GeoPackage
        logging.info(f"Salvataggio dei dati finali nel file {file_path}")
        gdf.to_file(filename=str(file_path), driver='GPKG', layer=f"census{year}")

    # Eliminazione dei dati pre-processati se richiesto
    if delete_preprocessed_data:
        logging.info(f"Eliminazione del file pre-processato: {main_data}")
        os.remove(str(main_data))

    time_end = datetime.datetime.now()
    elapsed_time = time_end - time_start
    logging.info(f"Preprocessing completato in {elapsed_time}.")
