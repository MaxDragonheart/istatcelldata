import logging
from pathlib import Path

from istatcelldata.executor.preprocess import preprocess_census
from istatcelldata.logger_config import configure_logging

main_path = Path("/home/max/Desktop/census/preprocessing")

# Configure logging at the start of the script
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="preprocess_census",
    )

# Define the logger as a global variable
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    setup_logging(log_dir=main_path.parent)

    preprocess_census(
        processed_data_folder=main_path,
        years=[1991, 2001, 2011, 2021],
        # regions=True,
        # provinces=True,
        # municipalities=True,
        delete_download_folder=False
    )
