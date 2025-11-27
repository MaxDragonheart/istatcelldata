import logging
from pathlib import Path
from typing import Union

import pandas as pd
import xlrd
from tqdm import tqdm


def read_xls(
        file_path: Path,
        census_code: str,
        output_path: Path = None,
) -> Union[pd.DataFrame, Path]:
    """Legge un file Excel (.xls) e restituisce un DataFrame oppure salva i dati in CSV.

    La funzione apre un file Excel in formato `.xls`, seleziona automaticamente
    il primo foglio utile (escludendo eventuali fogli denominati "Metadati"),
    estrae le righe del foglio, costruisce un DataFrame pandas e imposta come
    indice la colonna corrispondente al codice censuario fornito.

    Se viene indicato un percorso di output, il DataFrame viene salvato in
    formato CSV; altrimenti, viene restituito direttamente.

    Args:
        file_path (Path):
            Percorso del file Excel da leggere.
        census_code (str):
            Nome della colonna da utilizzare come indice del DataFrame
            (es. codice ISTAT del comune).
        output_path (Path, optional):
            Percorso della cartella in cui salvare il CSV risultante.
            Se None, il DataFrame viene restituito senza salvare nulla.

    Returns:
        Union[pd.DataFrame, Path]:
            - Un DataFrame contenente i dati letti dal file Excel, se
              `output_path` è None.
            - Il percorso del file CSV salvato, se viene specificato
              `output_path`.

    Raises:
        FileNotFoundError:
            Se il file indicato non esiste.
        xlrd.XLRDError:
            Se si verifica un errore durante la lettura del file Excel.
        Exception:
            Per qualsiasi errore non previsto durante il parsing o il salvataggio.
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
        df.set_index(census_code, inplace=True)
        df.sort_index(inplace=True)

        # Se non viene fornito un percorso di output, restituisce il DataFrame
        if output_path is None:
            return df
        else:
            file_name = file_path.stem.split('\\')[1]
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


def census_trace(
        file_path: Path,
        year: int,
        output_path: Path = None
) -> Path:
    """Estrae il tracciato dei metadati dal foglio “Metadati” di un file Excel.

    La funzione accede al foglio denominato **"Metadati"** di un file Excel
    relativo ai dati censuari, ne estrae le colonne fondamentali (nome del campo
    e descrizione) e costruisce un DataFrame pandas con indice basato sul nome
    del campo. Se viene fornito un percorso di output, il tracciato viene
    salvato anche in formato CSV.

    Args:
        file_path (Path):
            Percorso del file Excel da cui estrarre i metadati.
        year (int):
            Anno di riferimento del censimento, utilizzato per generare il nome
            del file di output.
        output_path (Path, optional):
            Percorso della cartella in cui salvare il CSV del tracciato.
            Se None, viene restituito direttamente un DataFrame.

    Returns:
        Path | pd.DataFrame:
            - Il percorso del file CSV generato, se `output_path` è fornito.
            - Un DataFrame pandas contenente il tracciato dei metadati,
              se `output_path` è None.

    Raises:
        FileNotFoundError:
            Se il file Excel specificato non esiste.
        xlrd.XLRDError:
            Se si verifica un errore durante l’apertura o la lettura del file Excel.
        Exception:
            Per eventuali errori non previsti durante il parsing o il salvataggio.
    """
    try:
        logging.info(f"Lettura dei dati da {file_path}")
        read_data = xlrd.open_workbook(file_path)

        get_sheet = read_data.sheet_by_name('Metadati')

        dataset = []
        for row_id in range(get_sheet.nrows):
            dataset.append(get_sheet.row_values(row_id)[:2])
        dataset = dataset[7:]  # Ignora le prime 7 righe

        # Crea le colonne del DataFrame
        df_columns = [column_name for column_name in dataset[0]]

        # Crea i dati del DataFrame
        df_data = dataset[1:]
        df = pd.DataFrame(data=df_data, columns=df_columns)
        df.set_index('NOME CAMPO', inplace=True)

        logging.info("Dati letti con successo.")

        if output_path is None:
            return df
        else:
            file_name = f'tracciato_{year}_sezioni.csv'
            logging.info(f"Salvataggio dei dati in {output_path.joinpath(file_name)}")
            df.to_csv(path_or_buf=output_path.joinpath(file_name), sep=';')
            return output_path.joinpath(file_name)  # Restituisce il percorso del file CSV salvato

    except FileNotFoundError as e:
        logging.error(f"File Excel non trovato: {file_path}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Errore nella lettura del file Excel: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Errore durante la lettura del file Excel o il salvataggio dei dati: {str(e)}")
        raise e
