import logging
from pathlib import Path
from typing import List, Union

import pandas as pd
import xlrd
from tqdm import tqdm

from istatcelldata.config import GEODATA_FOLDER, DATA_FOLDER
from istatcelldata.download import download_base
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import census_folder, get_region

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


YEAR = 1991
CENSUS_CODE = f"sez{YEAR}"

MAIN_LINK = "https://www.istat.it/storage/cartografia"
GEODATA_LINK = f"{MAIN_LINK}/basi_territoriali/WGS_84_UTM/1991/"
DATA_LINK = f"{MAIN_LINK}/variabili-censuarie/dati-cis_1991.zip"


def read_xls(
        file_path: Path,
        output_path: Path = None,
) -> Union[pd.DataFrame, Path]:
    """Legge un file Excel (.xls) e restituisce un DataFrame pandas o salva i dati in CSV.

    La funzione legge i dati da un file Excel e restituisce un DataFrame pandas
    contenente i dati. Se viene fornito un percorso di output, i dati vengono
    salvati anche in un file CSV.

    Args:
        file_path (Path): Il percorso del file Excel da leggere.
        output_path (Path, optional): Il percorso in cui salvare il file CSV.
            Se None, la funzione restituisce il DataFrame (default: None).

    Returns:
        Union[pd.DataFrame, Path]: Un DataFrame pandas contenente i dati letti,
            o il percorso del file CSV salvato.

    Raises:
        FileNotFoundError: Se il file Excel non viene trovato.
        xlrd.XLRDError: Se si verifica un errore durante la lettura del file Excel.
        Exception: Per altri errori durante il processo di lettura o salvataggio.
    """
    try:
        logging.info(f"Lettura del file Excel da {file_path}")

        # Legge il file Excel
        read_data = xlrd.open_workbook(file_path)

        # Estrae il nome del foglio, ignorando 'Metadati'
        sheet_list = read_data.sheet_names()
        if 'Metadati' in sheet_list:
            sheet_list.remove('Metadati')
        sheet_name = sheet_list[0]
        get_sheet = read_data.sheet_by_name(sheet_name)

        # Estrae i dati dal foglio
        dataset = []
        for row_id in tqdm(range(get_sheet.nrows), desc="Lettura righe..."):
            dataset.append(get_sheet.row_values(row_id))

        # Crea il DataFrame
        df_columns = [column_name.lower() for column_name in dataset[0]]
        df_data = dataset[1:]
        df = pd.DataFrame(data=df_data, columns=df_columns)

        # Imposta il tipo di dati e l'indice
        df = df.astype(int)
        df.set_index(CENSUS_CODE, inplace=True)
        df.sort_index(inplace=True)

        # Se non viene fornito un percorso di output, restituisce il DataFrame
        if output_path is None:
            return df
        else:
            file_name = file_path.stem
            logging.info(f"Salvataggio dei dati in {output_path.joinpath(f'{file_name}.csv')}")
            df.to_csv(path_or_buf=output_path.joinpath(f'{file_name}.csv'), sep=';')
            return output_path.joinpath(f'{file_name}.csv')  # Restituisce il percorso del file CSV salvato

    except FileNotFoundError as e:
        logging.error(f"File Excel non trovato: {file_path}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Errore nella lettura del file Excel: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Errore durante la lettura del file Excel o il salvataggio dei dati: {str(e)}")
        raise e


def download_geodata(
    output_data_folder: Path,
    region_list: List[int] = []
) -> Path:
    """Scarica i dati geocensuari per le regioni specificate.

    Questa funzione crea una struttura di cartelle per i dati censuari e scarica i file
    ZIP contenenti i dati geocensuari per le regioni indicate. Se non vengono fornite
    regioni, vengono scaricati i dati per tutte le 20 regioni.

    Args:
        output_data_folder (Path): La cartella di output principale per i dati.
        region_list (List[int], optional): Lista di regioni da scaricare. Se vuota,
            scarica i dati per tutte le regioni (default: []).

    Returns:
        Path: La cartella contenente i dati geocensuari scaricati.
    """
    # Creazione della cartella di destinazione per i dati
    destination_folder = census_folder(output_data_folder=output_data_folder, year=YEAR)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    data_folder = destination_folder.joinpath(GEODATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    year_folder = str(YEAR)[2:]  # Ultime due cifre dell'anno

    # Imposta la lista delle regioni da scaricare
    regions = get_region(region_list=region_list)

    for region in regions:
        region_str = str(region).zfill(2)
        data_link = f"{GEODATA_LINK}/R{region_str}_{year_folder}_WGS84.zip"
        logging.info(f"Link dei dati: {data_link}")

        data_file_name = data_link.split('/')[-1]
        data_file_path_dest = Path(data_folder).joinpath(data_file_name)
        logging.info(f"Percorso del file di destinazione: {data_file_path_dest}")

        # Scarica i dati
        download_base(
            data_link=data_link,
            data_file_path_destination=data_file_path_dest,
            data_folder=data_folder,
            destination_folder=destination_folder
        )

    return data_folder


def download_data(
    output_data_folder: Path,
) -> Path:
    # Creazione della cartella di destinazione per i dati
    destination_folder = census_folder(output_data_folder=output_data_folder, year=YEAR)
    Path(destination_folder).mkdir(parents=True, exist_ok=True)

    data_folder = destination_folder.joinpath(DATA_FOLDER)
    Path(data_folder).mkdir(parents=True, exist_ok=True)

    data_file_name = Path(DATA_LINK).stem + Path(DATA_LINK).suffix
    data_file_path_dest = Path(data_folder).joinpath(data_file_name)

    download_base(
        data_link=DATA_LINK,
        data_file_path_destination=data_file_path_dest,
        data_folder=data_folder,
        destination_folder=destination_folder
    )
