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
    """Finalizza i dati del censimento unendo geodati e dati tabellari in un GeoPackage unico.

    Per ciascun anno indicato, la funzione:
    1. Legge i dati geografici (sezioni di censimento) dal layer `census<anno>`.
    2. Legge i dati tabellari dal layer `data<anno>`.
    3. Rimuove eventuali colonne non necessarie dai dati tabellari.
    4. Esegue il join tra dati geografici e tabellari sulla chiave `SEZ<anno>`.
    5. Ordina i dati e costruisce un GeoDataFrame finale.
    6. Salva il risultato in un GeoPackage denominato `census_data.gpkg`,
       con un layer per anno (`census<anno>`).

    Args:
        census_data_path (Path):
            Cartella contenente il file GeoPackage pre-processato (`census.gpkg`),
            generato dalle fasi precedenti del workflow.
        years (list):
            Lista degli anni di censimento da finalizzare (es. [1991, 2001, 2011, 2021]).
        output_data_folder (Path, optional):
            Cartella in cui salvare il GeoPackage finale `census_data.gpkg`.
            Se None, il file viene salvato in `census_data_path`.
        delete_preprocessed_data (bool, optional):
            Se True, elimina il file `census.gpkg` dopo il completamento della
            finalizzazione.

    Raises:
        FileNotFoundError:
            Se il file GeoPackage principale `census.gpkg` non esiste nel percorso
            indicato da `census_data_path`.
        KeyError:
            Se la colonna di join `SEZ<anno>` non è presente nei dati geografici o
            tabellari, oppure se nel dizionario `census_data` non sono definite
            le colonne da rimuovere per l'anno in esame.

    Notes:
        - La chiave di join tra dati geografici e tabellari è dinamica e segue
          la convenzione `SEZ<anno>`.
        - Le colonne da rimuovere dai dati tabellari sono definite in
          `census_data[year]['data_columns_to_remove']`.
        - Il GeoPackage finale può contenere più layer, uno per ogni anno
          processato.
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
