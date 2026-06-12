import importlib
import logging
import tempfile
from pathlib import Path

import pytest

import istatcelldata.download
from istatcelldata.logger_config import configure_logging, get_log_filename


def test_get_log_filename_default_temp_dir():
    print("test_get_log_filename_default_temp_dir")
    log_path = get_log_filename()
    print(log_path)
    assert log_path.parent == Path(tempfile.gettempdir()).joinpath("logs")
    assert log_path.suffix == ".log"
    assert "log_" in log_path.name or "custom_" in log_path.name


def test_get_log_filename_custom_dir(tmp_path):
    print("test_get_log_filename_custom_dir")
    custom_dir = tmp_path / "custom_logs"
    log_path = get_log_filename(log_dir=custom_dir)
    print(log_path)
    assert log_path.parent == custom_dir.joinpath("logs")
    assert log_path.suffix == ".log"
    assert "log_" in log_path.name or "custom_" in log_path.name


def test_configure_logging_default_temp_dir():
    print("test_configure_logging_default_temp_dir")
    configure_logging()
    logger = logging.getLogger()
    log_file_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(
            handler, "_istatcelldata_handler", False
        ):
            log_file_handler = handler
            break

    assert log_file_handler is not None
    log_path = Path(log_file_handler.baseFilename)
    assert log_path.parent == Path(tempfile.gettempdir()).joinpath("logs")
    assert log_path.suffix == ".log"


def test_configure_logging_replaces_istatcelldata_handlers(tmp_path):
    """Test repeated explicit configuration does not duplicate package handlers."""
    logger = logging.getLogger()

    configure_logging(log_dir=tmp_path, log_name="first")
    first_handlers = [
        handler for handler in logger.handlers if getattr(handler, "_istatcelldata_handler", False)
    ]

    configure_logging(log_dir=tmp_path, log_name="second")
    second_handlers = [
        handler for handler in logger.handlers if getattr(handler, "_istatcelldata_handler", False)
    ]

    assert len(first_handlers) == 2
    assert len(second_handlers) == 2
    assert first_handlers != second_handlers


def test_importing_package_module_does_not_configure_logging():
    """Test package module import has no logging handler side effects."""
    logger = logging.getLogger()
    handler_count = len(logger.handlers)

    importlib.reload(istatcelldata.download)

    assert len(logger.handlers) == handler_count


def test_configure_logging_custom_dir(tmp_path):
    pytest.skip("Global logging state pollution from other tests - needs test isolation")
    print("test_configure_logging_custom_dir")
    custom_dir = tmp_path / "custom_logs"
    configure_logging(log_dir=custom_dir)
    logger = logging.getLogger()
    log_file_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            log_file_handler = handler
            break

    assert log_file_handler is not None
    log_path = Path(log_file_handler.baseFilename)
    assert log_path.parent == custom_dir.joinpath("logs")
    assert log_path.suffix == ".log"
