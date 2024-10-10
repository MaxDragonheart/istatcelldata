import csv
import logging
import os
import zipfile
from pathlib import Path
from typing import List

import chardet
import xlrd
from tqdm import tqdm

from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def check_encoding(data: Path) -> str:
    """Determina la codifica di un file.

    Questa funzione apre il file specificato, legge i primi 100.000 byte e tenta di
    determinare la codifica utilizzando la libreria `chardet`. Se la codifica rilevata è 'ascii',
    viene convertita in 'latin1' per evitare problemi di compatibilità con file testuali.

    Args:
        data (Path): Il percorso del file di cui si vuole determinare la codifica.

    Returns:
        str: La codifica rilevata del file. Se 'ascii' viene rilevato, restituisce 'latin1'.
    """
    # Apre il file in modalità binaria e legge i primi 100.000 byte per la rilevazione della codifica.
    with open(data, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))  # Utilizza chardet per rilevare la codifica

        # Se la codifica rilevata è 'ascii', la modifica a 'latin1' per maggiore compatibilità
        if result['encoding'] == 'ascii':
            result['encoding'] = 'latin1'

    # Restituisce la codifica rilevata
    return result['encoding']


def csv_from_excel(        data: Path,
        output_path: Path,
        metadata: bool = False
) -> Path:
    """Converte un file Excel (.xls) in CSV.

    La funzione legge un file Excel e converte i dati presenti in un foglio
    specificato in formato CSV. Se `metadata=True`, converte il foglio
    chiamato "Metadati", altrimenti converte il primo foglio disponibile,
    escluso "Metadati" se esistente.

    Args:
        data (Path): Il percorso del file Excel da convertire.
        output_path (Path): Il percorso dove salvare il file CSV generato.
        metadata (bool): Se True, converte il foglio "Metadati", altrimenti
            converte il primo foglio escluso "Metadati" (default: False).

    Returns:
        Path: Il percorso del file CSV creato.

    Raises:
        FileNotFoundError: Se il file Excel specificato non viene trovato.
        xlrd.XLRDError: Se non è possibile leggere il file Excel.
        Exception: Per eventuali altri errori durante la conversione.
    """
    try:
        logging.info(f"Lettura del file Excel da {data}")

        # Legge il file Excel
        read_data = xlrd.open_workbook(data)

        # Se è richiesto di leggere i metadati
        if metadata:
            sheet_name = 'Metadati'
            logging.info("Conversione del foglio 'Metadati'.")
        else:
            # Prende la lista dei fogli, escludendo 'Metadati' se presente
            sheet_list = read_data.sheet_names()
            if 'Metadati' in sheet_list:
                sheet_list.remove('Metadati')
            sheet_name = sheet_list[0]  # Primo foglio disponibile
            logging.info(f"Conversione del foglio: {sheet_name}")

        # Estrae il foglio da convertire
        get_sheet = read_data.sheet_by_name(sheet_name)

        # Crea e scrive nel file CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as output_data:
            write_csv = csv.writer(output_data, quoting=csv.QUOTE_ALL)

            logging.info(f"Conversione del foglio '{sheet_name}' in CSV.")
            for row_id in tqdm(range(get_sheet.nrows), desc="Conversione"):
                write_csv.writerow(get_sheet.row_values(row_id))

        logging.info(f"Dati convertiti salvati in {output_path}.")
        return output_path

    except FileNotFoundError as e:
        logging.error(f"File Excel non trovato: {data}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Errore nella lettura del file Excel: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Errore durante la conversione da Excel a CSV: {str(e)}")
        raise e


def census_folder(
        output_data_folder: Path,
        year: int
) -> Path:
    """Crea una cartella per i dati e geodati del censimento dell'anno selezionato.

    La funzione crea una cartella specifica per il censimento relativo all'anno indicato
    all'interno della directory specificata. Se la cartella esiste già, non verrà
    creata nuovamente, grazie al parametro `exist_ok=True`.

    Args:
        output_data_folder (Path): Il percorso della cartella principale in cui creare la
            cartella del censimento.
        year (int): L'anno del censimento. Il valore predefinito è il 2011.

    Returns:
        Path: Il percorso della cartella creata o esistente.

    Raises:
        Exception: In caso di problemi con la creazione della cartella.
    """
    try:
        # Log dell'inizio del processo
        logging.info(f"Creazione della cartella per i dati del censimento {year}.")

        # Nome della cartella basata sull'anno del censimento
        download_folder_name = f"census_{year}"

        # Percorso completo della cartella
        destination_folder = output_data_folder.joinpath(download_folder_name)

        # Creazione della cartella (se non esiste già)
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Log del successo
        logging.info(f"Cartella creata o già esistente: {destination_folder}")

        return destination_folder

    except Exception as e:
        # Log degli errori
        logging.error(f"Errore durante la creazione della cartella per il censimento {year}: {str(e)}")
        raise e


def unzip_data(input_data: Path, output_folder: Path) -> Path:
    """Decomprime un file ZIP nella cartella di destinazione specificata.

    La funzione apre un file ZIP e ne estrae tutto il contenuto nella
    cartella specificata. Se la cartella di destinazione non esiste,
    viene creata automaticamente.

    Args:
        input_data (Path): Il percorso del file ZIP da decomprimere.
        output_folder (Path): Il percorso della cartella dove estrarre i file.

    Returns:
        Path: Il percorso della cartella in cui sono stati estratti i file.

    Raises:
        FileNotFoundError: Se il file ZIP non viene trovato.
        zipfile.BadZipFile: Se il file fornito non è un file ZIP valido.
        Exception: Per eventuali errori generici durante la decompressione.
    """
    try:
        logging.info(f"Decompressione del file {input_data} nella cartella {output_folder}.")

        # Verifica se la cartella di output esiste, altrimenti la crea
        output_folder.mkdir(parents=True, exist_ok=True)

        # Decomprime il file ZIP
        with zipfile.ZipFile(input_data, "r") as zf:
            zf.extractall(output_folder)

        logging.info(f"Decompressione completata. File estratti in {output_folder}.")
        return output_folder

    except FileNotFoundError as e:
        logging.error(f"File ZIP non trovato: {input_data}")
        raise e
    except zipfile.BadZipFile as e:
        logging.error(f"Il file fornito non è un file ZIP valido: {input_data}")
        raise e
    except Exception as e:
        logging.error(f"Errore durante la decompressione: {str(e)}")
        raise e


def get_region(region_list: List[int] = []) -> List[int]:
    if len(region_list) == 0:
        regions = list(range(1, 21, 1))
    else:
        regions = region_list

    return regions


def get_census_dictionary(census_year: int, region_list: List[int] = []) -> dict:
    """Genera i link per il download dei dati censuari, geodati e confini amministrativi
    in base all'anno del censimento fornito.

    Args:
        census_year (int): L'anno del censimento per cui generare i link.

    Returns:
        dict: Un dizionario contenente i link per il download dei dati,
        geodati e confini amministrativi.

    Raises:
        ValueError: Se l'anno del censimento non è supportato.
    """
    main_link = "https://www.istat.it/storage/cartografia"
    census = [1991, 2001, 2011, 2021]
    if census_year in census:
        year_code = str(census_year)[2:]

        regions = get_region(region_list=region_list)

        geodata_urls = []

        for region in regions:
            region_str = str(region).zfill(2)

            if census_year in [1991, 2001, 2011]:
                geodata_file = f"R{region_str}_{year_code}_WGS84.zip"
                geodata_url = f"{main_link}/basi_territoriali/WGS_84_UTM/{census_year}/{geodata_file}"
            else:
                geodata_file = f"R{region_str}_{year_code}.zip"
                geodata_url = f"{main_link}/basi_territoriali/{census_year}/{geodata_file}"
            geodata_urls.append(geodata_url)

        if census_year in [1991, 2001, 2011]:
            data_url = f"{main_link}/variabili-censuarie/dati-cpa_{census_year}.zip"
            census_code = f"sez{census_year}"

        else:
            data_url = "https://esploradati.censimentopopolazione.istat.it/databrowser/DWL/PERMPOP/SUBCOM/Dati_regionali_2021.zip"
            census_code = "sez21_id"

        if census_year == 2011:
            boundaries_folder = f"{census_year}/Limiti_{census_year}_WGS84.zip"
        else:
            boundaries_folder = f"Limiti{census_year}.zip"

        links_dict = {
            f"census{census_year}": {
                "data_url": data_url,
                "geodata_urls": geodata_urls,
                "admin_boundaries_url": f"{main_link}/confini_amministrativi/non_generalizzati/{boundaries_folder}",
                "census_code": census_code
            }
        }

        return links_dict

    else:
        raise ValueError(f"L'anno di censimento scelto non è supportato. Puo scegliere tra {census}.")


def remove_files(files_path: list) -> None:
    # Remove xls
    for file_path in files_path:
        os.remove(file_path)
