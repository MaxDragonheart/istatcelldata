import logging
from pathlib import Path

from istatcelldata.executor.download import download_census
from istatcelldata.logger_config import configure_logging


main_path = Path("/home/max/Desktop/census")
list_year = []
list_region = []


# Configure logging at the start of the script
def setup_logging(log_dir: Path):
    configure_logging(
        log_dir=log_dir,
        log_name="download_census",
    )

# Define the logger as a global variable
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    setup_logging(log_dir=main_path)

    download_census(
        years=list_year,
        output_data_folder=main_path,
        region_list=list_region,
    )
