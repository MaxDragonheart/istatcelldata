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
    """Determina la codifica di un file leggendo un campione iniziale.

    La funzione apre il file in modalità binaria, legge i primi 100.000 byte
    e utilizza la libreria `chardet` per stimare la codifica del testo.
    Nel caso in cui `chardet` identifichi la codifica come `'ascii'`, questa viene
    convertita in `'latin1'` per garantire maggiore compatibilità, poiché molti file
    amministrativi e geografici possono contenere caratteri estesi pur essendo
    formalmente interpretati come ASCII.

    Args:
        data (Path):
            Percorso del file di cui si vuole determinare la codifica.

    Returns:
        str:
            La codifica rilevata.
            Se viene restituito `'ascii'`, viene automaticamente sostituito con `'latin1'`.

    Notes:
        - `chardet` fornisce una stima heuristica della codifica; non è infallibile.
        - La lettura è limitata ai primi 100.000 byte per migliorare le prestazioni.
        - `'latin1'` è una scelta sicura per evitare errori su file con caratteri
          accentati o codifiche ambigue tipiche dei dataset amministrativi ISTAT.
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
    """Converte un file Excel (.xls) in formato CSV.

    La funzione legge un file Excel in formato legacy (.xls) tramite `xlrd` e
    converte il contenuto di un foglio in un file CSV. Se `metadata=True`, viene
    convertito il foglio chiamato **"Metadati"**; in caso contrario, viene
    convertito il primo foglio disponibile escludendo `"Metadati"` se presente.

    La conversione mantiene l'ordine delle righe e scrive tutti i campi con
    `csv.QUOTE_ALL` per garantire compatibilità e preservare delimitatori,
    stringhe con spazi o caratteri speciali.

    Args:
        data (Path):
            Percorso del file Excel da convertire.
        output_path (Path):
            Percorso del file CSV prodotto.
        metadata (bool, optional):
            Se True converte il foglio `"Metadati"`.
            Se False converte il primo foglio utile escludendo `"Metadati"`
            (default: False).

    Returns:
        Path:
            Percorso del file CSV generato.

    Raises:
        FileNotFoundError:
            Se il file Excel indicato non esiste.
        xlrd.XLRDError:
            Se il file non può essere letto o il foglio richiesto non esiste.
        Exception:
            Per eventuali altri errori durante la conversione o la scrittura.

    Notes:
        - La conversione utilizza `xlrd`, pertanto il file deve essere in formato
          `.xls` (Excel legacy). I file `.xlsx` non sono supportati da xlrd.
        - Il CSV viene salvato in UTF-8.
        - La funzione utilizza `tqdm` per mostrare una barra di avanzamento.
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
    """Crea (se necessario) la cartella dedicata ai dati del censimento per un anno specifico.

    La funzione genera una directory denominata `census_<anno>` all’interno della
    cartella `output_data_folder` e la crea se non esiste già. Questa cartella
    rappresenta la radice dei dati scaricati ed elaborati per un determinato
    censimento, mantenendo una struttura ordinata e coerente tra anni diversi.

    Args:
        output_data_folder (Path):
            Cartella principale sotto cui creare la directory del censimento.
        year (int):
            Anno del censimento da organizzare (es. 1991, 2001, 2011, 2021).

    Returns:
        Path:
            Il percorso completo della cartella del censimento creata o già esistente.

    Raises:
        Exception:
            Se la cartella non può essere creata per motivi di permessi o percorsi non validi.
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

    La funzione apre un archivio ZIP e ne estrae l’intero contenuto nella cartella
    indicata. Se la cartella di output non esiste, viene creata automaticamente.
    Funziona come componente interno del workflow di download dei dati ISTAT.

    Args:
        input_data (Path):
            Percorso del file ZIP da decomprimere.
        output_folder (Path):
            Cartella in cui estrarre il contenuto dell’archivio.

    Returns:
        Path:
            Il percorso della cartella contenente i file estratti.

    Raises:
        FileNotFoundError:
            Se il file ZIP non esiste.
        zipfile.BadZipFile:
            Se il file fornito non è un ZIP valido.
        Exception:
            Per qualsiasi errore durante la decompressione.
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
    """Restituisce la lista delle regioni da utilizzare per il download dei geodati.

    Se non viene fornita una lista, restituisce l’elenco completo delle 20 regioni
    italiane (codici 1–20). In caso contrario, restituisce la lista fornita.

    Args:
        region_list (List[int], optional):
            Lista dei codici delle regioni da utilizzare.
            Se vuota → restituisce tutte le regioni (1–20).

    Returns:
        List[int]:
            Lista dei codici regione da processare.
    """
    if len(region_list) == 0:
        regions = list(range(1, 21, 1))
    else:
        regions = region_list

    return regions


def get_census_dictionary(census_year: int, region_list: List[int] = []) -> dict:
    """Genera i link ufficiali ISTAT per dati censuari, geodati e confini amministrativi.

    La funzione costruisce dinamicamente i percorsi di download in base all’anno
    di censimento e alla lista delle regioni desiderate. Gestisce le differenze
    strutturali fra censimenti precedenti (1991–2011) e quello del 2021.

    Args:
        census_year (int):
            Anno del censimento (1991, 2001, 2011 o 2021).
        region_list (List[int], optional):
            Lista delle regioni per cui generare i link dei geodati.
            Se vuota → regioni 1–20.

    Returns:
        dict:
            Dizionario contenente i link:
            - `data_url` per i dati del censimento
            - `geodata_urls` per le basi territoriali
            - `admin_boundaries_url` per i confini amministrativi
            - `census_code` codice primario per join e identificativi

    Raises:
        ValueError:
            Se l’anno fornito non è supportato.
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
            data_url = "https://esploradati.istat.it/databrowser/DWL/PERMPOP/SUBCOM/Dati_regionali_2021.zip"
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
    """Rimuove una lista di file dal filesystem.

    Args:
        files_path (list):
            Lista di oggetti Path da eliminare.

    Notes:
        - Le eccezioni non vengono catturate: se un file non può essere eliminato,
          l’errore emerge esplicitamente (comportamento desiderabile nel workflow ETL).
    """
    # Remove xls
    for file_path in files_path:
        os.remove(file_path)
