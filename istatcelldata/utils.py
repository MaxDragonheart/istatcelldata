import csv
import logging
import ssl
import zipfile
from pathlib import Path

import chardet
import requests
import urllib3
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


class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    """Adattatore HTTP personalizzato che consente l'uso di un contesto SSL custom.

    Questa classe permette di utilizzare un contesto SSL personalizzato durante
    la gestione delle connessioni HTTP. Estende l'adattatore predefinito di `requests`.
    Soluzione adottata grazie a https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled/73519818#73519818

    Args:
        ssl_context (ssl.SSLContext, optional): Un contesto SSL personalizzato da utilizzare.
        **kwargs: Altri parametri passati alla classe madre `HTTPAdapter`.
    """

    def __init__(self, ssl_context=None, **kwargs):
        """Inizializza l'adattatore HTTP con un contesto SSL personalizzato."""
        self.ssl_context = ssl_context
        logging.info("Inizializzazione di CustomHttpAdapter con un contesto SSL personalizzato.")
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        """Inizializza il gestore della connessione con un contesto SSL personalizzato.

        Args:
            connections (int): Numero di connessioni nel pool.
            maxsize (int): Numero massimo di connessioni nel pool.
            block (bool, optional): Se bloccare quando il pool è pieno.
            **pool_kwargs: Altri parametri passati al PoolManager.
        """
        logging.info("Inizializzazione del PoolManager con contesto SSL personalizzato.")
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
            **pool_kwargs
        )


def get_legacy_session():
    """Crea una sessione HTTP compatibile con server legacy.

    La funzione crea un contesto SSL personalizzato che abilita il supporto per
    la connessione a server legacy tramite l'opzione `OP_LEGACY_SERVER_CONNECT`.
    La sessione utilizza un adattatore personalizzato `CustomHttpAdapter` con il contesto SSL.
    Soluzione adottata grazie a https://stackoverflow.com/questions/71603314/ssl-error-unsafe-legacy-renegotiation-disabled/73519818#73519818

    Returns:
        requests.Session: Una sessione HTTP con un contesto SSL configurato per server legacy.
    """
    try:
        logging.info("Creazione di un contesto SSL con supporto per server legacy.")

        # Crea il contesto SSL con l'opzione legacy
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

        # Crea una sessione HTTP e monta l'adattatore con il contesto SSL personalizzato
        session = requests.session()
        session.mount('https://', CustomHttpAdapter(ctx))

        logging.info("Sessione creata con adattatore SSL legacy.")
        return session

    except Exception as e:
        logging.error(f"Errore nella creazione della sessione legacy: {str(e)}")
        raise e
