import logging
from pathlib import Path
from dask.distributed import Client
from multiprocessing import cpu_count

logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_format = '%(asctime)s | %(process)d - %(message)s'
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(console_handler)

# N_CORES = cpu_count()
# client = Client(n_workers=1, threads_per_worker=N_CORES, processes=True)

# PROJECT
MAIN_LINK = "https://www.istat.it/storage/cartografia"
GLOBAL_CRS = 32632
main_path = Path("/home/max/Desktop/census_istat/")
