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
        municipalities_target_columns: list
) -> pd.DataFrame:
    """Aggiunge informazioni amministrative (regioni, province e comuni) ai dati del censimento.

    Args:
        census_data (pd.DataFrame): Dati del censimento a cui aggiungere informazioni amministrative.
        regions_data_path (Path): Percorso del file con i confini regionali.
        regions_target_columns (list): Colonne target da estrarre dai dati delle regioni.
        provinces_data_path (Path): Percorso del file con i confini provinciali.
        provinces_target_columns (list): Colonne target da estrarre dai dati delle province.
        municipalities_data_path (Path): Percorso del file con i confini comunali.
        municipalities_target_columns (list): Colonne target da estrarre dai dati dei comuni.

    Returns:
        pd.DataFrame: DataFrame del censimento con informazioni aggiuntive su comuni, province e regioni.
    """
    logging.info("Inizio aggiunta delle informazioni amministrative ai dati del censimento.")

    # Convertiamo i nomi delle colonne del censimento in maiuscolo per uniformità
    census_data.columns = census_data.columns.str.upper()
    logging.info("Nomi delle colonne del dataset del censimento convertiti in maiuscolo.")

    # Lettura dei confini amministrativi regionali
    logging.info(f"Lettura dei dati delle regioni da {regions_data_path}")
    regions_data = read_administrative_boundaries(
        file_path=regions_data_path,
        target_columns=regions_target_columns,
        index_column=regions_target_columns[0]
    )
    regions_data.reset_index(inplace=True)
    logging.info(f"Dati delle regioni letti con successo. {len(regions_data)} record trovati.")

    # Lettura dei confini amministrativi provinciali
    logging.info(f"Lettura dei dati delle province da {provinces_data_path}")
    provinces_data = read_administrative_boundaries(
        file_path=provinces_data_path,
        target_columns=provinces_target_columns,
        index_column=provinces_target_columns[0]
    )
    provinces_data.reset_index(inplace=True)
    logging.info(f"Dati delle province letti con successo. {len(provinces_data)} record trovati.")

    # Lettura dei confini amministrativi comunali
    logging.info(f"Lettura dei dati dei comuni da {municipalities_data_path}")
    municipalities_data = read_administrative_boundaries(
        file_path=municipalities_data_path,
        target_columns=municipalities_target_columns,
        index_column=municipalities_target_columns[0]
    )
    municipalities_data.reset_index(inplace=True)
    logging.info(f"Dati dei comuni letti con successo. {len(municipalities_data)} record trovati.")

    # Merge dei dati comunali con quelli provinciali
    logging.info("Inizio merge tra dati comunali e provinciali.")
    add_provinces = pd.merge(
        left=municipalities_data,
        right=provinces_data,
        how='left',
        on='COD_PROV'
    )
    logging.info(f"Merge tra comuni e province completato. {len(add_provinces)} record risultanti.")

    # Merge dei dati risultanti con i dati regionali
    logging.info("Inizio merge tra dati comunali-province e regionali.")
    add_regions = pd.merge(
        left=add_provinces,
        right=regions_data,
        how='left',
        on='COD_REG'
    )
    logging.info(f"Merge tra comuni, province e regioni completato. {len(add_regions)} record risultanti.")

    # Merge finale dei dati del censimento con le informazioni amministrative aggiunte
    logging.info("Inizio merge finale con i dati del censimento.")
    add_municipalities = pd.merge(
        left=census_data,
        right=add_regions,
        how='left',
        on='PRO_COM'
    )
    logging.info(f"Merge finale completato. {len(add_municipalities)} record nel dataset finale.")
    add_municipalities.drop(columns=['COD_PRO', 'PRO_COM'], inplace=True)
    add_municipalities.rename(
        columns={'COD_COM': 'CODCOM', 'COD_PROV': 'CODPRO', 'COD_REG': 'CODREG', 'DEN_PROV': 'PROVINCIA', 'DEN_REG': 'REGIONE'},
        inplace=True
    )

    logging.info("Aggiunta delle informazioni amministrative completata con successo.")

    return add_municipalities
