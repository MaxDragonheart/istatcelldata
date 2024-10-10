import datetime
import logging
import sys
import tempfile
from pathlib import Path


def get_log_filename(
        log_dir: Path = None,
        log_name: str = None,
) -> Path:
    """
    Generate a log file name with process ID and timestamp.

    Args:
        log_dir: Directory where the log file should be saved.
        log_name: Name of log file, if None the name is generated automatically.

    Returns:
        Path: The full path of the log file.
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
    """
    Configure the logging system to output to both console and file.

    Args:
        log_dir: Directory where the log file should be saved.
        log_name: Name of log file, if None the name is generated automatically.
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
