import logging
import os
from pathlib import Path

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = '%(asctime)s | %(process)d - %(message)s'
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(console_handler)

MAIN_DATA_PATH = os.getenv("DATA_PATH")
main_path = Path(MAIN_DATA_PATH)


if __name__ == '__main__':
    print(MAIN_DATA_PATH)
    print(type(MAIN_DATA_PATH))

    print(main_path)
    print(type(main_path))