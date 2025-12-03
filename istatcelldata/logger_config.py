import datetime
import logging
import sys
import tempfile
from pathlib import Path


def get_log_filename(
    log_dir: Path | None = None,
    log_name: str | None = None,
) -> Path:
    """Generate a complete log file path including timestamp and optional name.

    This function automatically creates a `logs` folder within the specified directory,
    generates a unique filename based on timestamp (down to milliseconds), and returns
    the complete file path. If no directory is provided, the system's temporary directory
    is used.

    Args:
        log_dir: Directory where the log file will be saved. If None, the system's
            temporary directory is used (`tempfile.gettempdir()`).
        log_name: Base name for the log file. If None, the generated filename will be
            `log_<timestamp>.log`. If provided, the file will be `<log_name>_<timestamp>.log`.

    Returns:
        Complete path to the generated log file.

    Note:
        - Timestamp format is `YYYYMMDDTHHMMSS.mmm` (millisecond precision).
        - The `logs` folder is created automatically if it doesn't exist.
        - Filename is always unique due to millisecond-precision timestamp.
    """
    # Use the system's temp directory if log_dir is not provided
    if log_dir is None:
        log_dir = Path(tempfile.gettempdir())

    # Ensure the directory exists
    log_directory = log_dir.joinpath("logs")
    log_directory.mkdir(exist_ok=True, parents=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f")[:-3]  # Include milliseconds

    if log_name is None:
        filename = f"log_{timestamp}.log"
    else:
        filename = f"{log_name}_{timestamp}.log"

    return log_directory.joinpath(filename)


def configure_logging(
    log_dir: Path | None = None,
    log_name: str | None = None,
):
    """Configure the logging system to write to both console and file.

    This function initializes the application's main logger, sets the logging level
    to INFO, and registers two handlers:

    - **Console handler** → prints messages to stdout.
    - **File handler** → saves logs to a file with a dynamically generated name
      via `get_log_filename()`, using timestamp and optional name.

    Args:
        log_dir: Directory where the log file will be saved. If None, the system's
            temporary directory is used.
        log_name: Base name for the log file. If None, an automatic name of the form
            `log_<timestamp>.log` is generated.

    Note:
        - This function uses the global logger (`logging.getLogger()`).
        - Each call adds new handlers: to avoid duplicates in case of multiple calls,
          it may be useful to clear handlers before configuring them.
        - Log format includes: level, PID, timestamp, logger name, and message.
    """
    # Configure logger
    global logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Define log format
    log_format = "%(levelname)s | %(process)d | %(asctime)s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_path = get_log_filename(
        log_dir=log_dir, log_name=log_name
    )  # Use dynamic log file name
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
