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
MAIN_PATH = Path("/home/max/Desktop/census_istat/")
OUTPUT_FOLDER = MAIN_PATH.joinpath('output')

SHARED_DATA = {
    'pop_tot': {
        'descrizione': 'Popolazione residente - TOTALE',
        'codice': 'P1'
    },
    'pop_tot_m': {
        'descrizione': 'Popolazione residente - Maschi',
        'codice': 'P2'
    },
    'pop_tot_f': {
        'descrizione': 'Popolazione residente - Femmine',
        'codice': 'P3'
    },
    'pop_meno_5_anni': {
        'descrizione': 'Popolazione residente - età < 5 anni',
        'codice': 'P14'
    },
    'pop_5_9_anni': {
        'descrizione': 'Popolazione residente - età 5 - 9 anni',
        'codice': 'P15'
    },
    'pop_10_14_anni': {
        'descrizione': 'Popolazione residente - età 10 - 14 anni',
        'codice': 'P16'
    },
    'pop_15_19_anni': {
        'descrizione': 'Popolazione residente - età 15 - 19 anni',
        'codice': 'P1'
    },
    'pop_20_24_anni': {
        'descrizione': 'Popolazione residente - età 20 - 24 anni',
        'codice': 'P2'
    },
    'pop_25_29_anni': {
        'descrizione': 'Popolazione residente - età 25 - 29 anni',
        'codice': 'P3'
    },
    'pop_30_34_anni': {
        'descrizione': 'Popolazione residente - età 30 - 34 anni',
        'codice': 'P14'
    },
    'pop_35_39_anni': {
        'descrizione': 'Popolazione residente - età 35 - 39 anni',
        'codice': 'P15'
    },
    'pop_40_44_anni': {
        'descrizione': 'Popolazione residente - età 40 - 44 anni',
        'codice': 'P16'
    },
}
