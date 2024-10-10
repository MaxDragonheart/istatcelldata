import logging
import tempfile
from pathlib import Path

from istatcelldata.logger_config import get_log_filename, configure_logging


def test_get_log_filename_default_temp_dir():
    print("test_get_log_filename_default_temp_dir")
    log_path = get_log_filename()
    print(log_path)
    assert log_path.parent == Path(tempfile.gettempdir()).joinpath('logs')
    assert log_path.suffix == '.log'
    assert 'log_' in log_path.name or 'custom_' in log_path.name


def test_get_log_filename_custom_dir(tmp_path):
    print("test_get_log_filename_custom_dir")
    custom_dir = tmp_path / "custom_logs"
    log_path = get_log_filename(log_dir=custom_dir)
    print(log_path)
    assert log_path.parent == custom_dir.joinpath('logs')
    assert log_path.suffix == '.log'
    assert 'log_' in log_path.name or 'custom_' in log_path.name


def test_configure_logging_default_temp_dir():
    print("test_configure_logging_default_temp_dir")
    configure_logging()
    logger = logging.getLogger()
    log_file_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            log_file_handler = handler
            break

    assert log_file_handler is not None
    log_path = Path(log_file_handler.baseFilename)
    assert log_path.parent == Path(tempfile.gettempdir()).joinpath('logs')
    assert log_path.suffix == '.log'


def test_configure_logging_custom_dir(tmp_path):
    print("test_configure_logging_custom_dir")
    custom_dir = tmp_path / "custom_logs"
    configure_logging(log_directory=custom_dir)
    logger = logging.getLogger()
    log_file_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            log_file_handler = handler
            break

    assert log_file_handler is not None
    log_path = Path(log_file_handler.baseFilename)
    assert log_path.parent == custom_dir.joinpath('logs')
    assert log_path.suffix == '.log'