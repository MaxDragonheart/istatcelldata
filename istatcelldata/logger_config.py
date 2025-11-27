import datetime
import logging
import sys
import tempfile
from pathlib import Path


def get_log_filename(
        log_dir: Path = None,
        log_name: str = None,
) -> Path:
    """Genera un percorso completo per un file di log includendo timestamp e nome opzionale.

    La funzione crea automaticamente una cartella `logs` all’interno della directory
    specificata, genera un nome di file univoco basato sul timestamp (fino ai millisecondi)
    e restituisce il percorso completo del file. Se non viene fornita alcuna directory,
    viene utilizzata la cartella temporanea del sistema.

    Args:
        log_dir (Path, optional):
            Directory in cui salvare il file di log.
            Se None, viene utilizzata la directory temporanea (`tempfile.gettempdir()`).
        log_name (str, optional):
            Nome base del file di log.
            Se None, il nome generato sarà del tipo `log_<timestamp>.log`.
            Se fornito, il file sarà del tipo `<log_name>_<timestamp>.log`.

    Returns:
        Path:
            Percorso completo del file di log generato.

    Notes:
        - Il timestamp è nel formato `YYYYMMDDTHHMMSS.mmm`.
        - La cartella `logs` viene creata automaticamente se non esiste.
        - Il nome del file è sempre univoco grazie al timestamp a millisecondi.
    """
    # Use the system's temp directory if log_dir is not provided
    if log_dir is None:
        log_dir = Path(tempfile.gettempdir())

    # Ensure the directory exists
    log_directory = log_dir.joinpath('logs')
    log_directory.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.datetime.now().strftime('%Y%m%dT%H%M%S.%f')[:-3]  # Include milliseconds

    if log_name is None:
        filename = f'log_{timestamp}.log'
    else:
        filename = f'{log_name}_{timestamp}.log'

    return log_directory.joinpath(filename)


def configure_logging(
        log_dir: Path = None,
        log_name: str = None,
):
    """Configura il sistema di logging per scrivere sia su console che su file.

    La funzione inizializza il logger principale dell'applicazione, imposta il livello
    di logging a `INFO` e registra due handler:

    - **Console handler** → stampa i messaggi su `stdout`.
    - **File handler** → salva i log in un file il cui nome è generato dinamicamente
      tramite `get_log_filename()`, utilizzando timestamp e nome opzionale.

    Args:
        log_dir (Path, optional):
            Directory in cui salvare il file di log. Se None, viene utilizzata la
            directory temporanea del sistema.
        log_name (str, optional):
            Nome base del file di log. Se None, viene generato automaticamente un nome
            del tipo `log_<timestamp>.log`.

    Notes:
        - La funzione utilizza il logger globale (`logging.getLogger()`).
        - Ogni chiamata aggiunge nuovi handler: per evitare duplicazioni in caso
          di chiamate multiple, può essere utile svuotare gli handler prima di
          configurarli (se lo desideri posso aggiungerlo).
        - Il formato dei log include: livello, PID, timestamp, nome del logger e messaggio.
    """
    # Configure logger
    global logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Define log format
    log_format = '%(levelname)s | %(process)d | %(asctime)s | %(name)s | %(message)s'
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_path = get_log_filename(
        log_dir=log_dir,
        log_name=log_name
    )  # Use dynamic log file name
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
