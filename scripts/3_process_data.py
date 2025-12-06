import logging
from pathlib import Path

from istatcelldata.executor.process import finalize_census_data
from istatcelldata.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census")


# Configure logging at the start of the script
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="finalize_census",
    )


# Define the logger as a global variable
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    finalize_census_data(
        census_data_path=main_path, years=[1991, 2001, 2011, 2021], delete_preprocessed_data=True
    )
