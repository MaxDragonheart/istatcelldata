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
        'codice': 'P17'
    },
    'pop_20_24_anni': {
        'descrizione': 'Popolazione residente - età 20 - 24 anni',
        'codice': 'P18'
    },
    'pop_25_29_anni': {
        'descrizione': 'Popolazione residente - età 25 - 29 anni',
        'codice': 'P19'
    },
    'pop_30_34_anni': {
        'descrizione': 'Popolazione residente - età 30 - 34 anni',
        'codice': 'P20'
    },
    'pop_35_39_anni': {
        'descrizione': 'Popolazione residente - età 35 - 39 anni',
        'codice': 'P21'
    },
    'pop_40_44_anni': {
        'descrizione': 'Popolazione residente - età 40 - 44 anni',
        'codice': 'P22'
    },
    'pop_45_49_anni': {
        'descrizione': 'Popolazione residente - età 15 - 19 anni',
        'codice': 'P23'
    },
    'pop_50_54_anni': {
        'descrizione': 'Popolazione residente - età 20 - 24 anni',
        'codice': 'P24'
    },
    'pop_55_59_anni': {
        'descrizione': 'Popolazione residente - età 25 - 29 anni',
        'codice': 'P25'
    },
    'pop_60_64_anni': {
        'descrizione': 'Popolazione residente - età 30 - 34 anni',
        'codice': 'P26'
    },
    'pop_65_69_anni': {
        'descrizione': 'Popolazione residente - età 35 - 39 anni',
        'codice': 'P27'
    },
    'pop_70_74_anni': {
        'descrizione': 'Popolazione residente - età 40 - 44 anni',
        'codice': 'P28'
    },
    'pop_maggiore_74_anni': {
        'descrizione': 'Popolazione residente - età > 74 anni',
        'codice': 'P29'
    },
    'pop_meno_5_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età < 5 anni',
        'codice': 'P30'
    },
    'pop_5_9_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 5 - 9 anni',
        'codice': 'P31'
    },
    'pop_10_14_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 10 - 14 anni',
        'codice': 'P32'
    },
    'pop_15_19_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 15 - 19 anni',
        'codice': 'P33'
    },
    'pop_20_24_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 20 - 24 anni',
        'codice': 'P34'
    },
    'pop_25_29_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 25 - 29 anni',
        'codice': 'P35'
    },
    'pop_30_34_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 30 - 34 anni',
        'codice': 'P36'
    },
    'pop_35_39_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 35 - 39 anni',
        'codice': 'P37'
    },
    'pop_40_44_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 40 - 44 anni',
        'codice': 'P38'
    },
    'pop_45_49_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 15 - 19 anni',
        'codice': 'P39'
    },
    'pop_50_54_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 20 - 24 anni',
        'codice': 'P40'
    },
    'pop_55_59_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 25 - 29 anni',
        'codice': 'P41'
    },
    'pop_60_64_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 30 - 34 anni',
        'codice': 'P42'
    },
    'pop_65_69_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 35 - 39 anni',
        'codice': 'P43'
    },
    'pop_70_74_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età 40 - 44 anni',
        'codice': 'P44'
    },
    'pop_maggiore_74_anni_m': {
        'descrizione': 'Popolazione residente - Maschi - età > 74 anni',
        'codice': 'P45'
    },
    'lavoratori_tot': {
        'descrizione': 'Forze lavoro - TOTALE',
        'codice': 'P60'
    },
    'lavoratori_occupati': {
        'descrizione': 'Forze lavoro - Occupati',
        'codice': 'P61'
    },
    'lavoratori_disoccupati': {
        'descrizione': 'Forze lavoro - Disoccupati e altre persone in cerca di occupazione',
        'codice': 'P62'
    },
    'famiglie_tot': {
        'descrizione': 'Famiglie totale',
        'codice': 'PF1'
    },
    'famiglie_componenti_tot': {
        'descrizione': 'Totale componenti delle famiglie',
        'codice': 'PF2'
    },
    'famiglie_1_componente': {
        'descrizione': 'Famiglie 1 componente',
        'codice': 'PF3'
    },
    'famiglie_2_componenti': {
        'descrizione': 'Famiglie 2 componenti',
        'codice': 'PF4'
    },
    'famiglie_3_componenti': {
        'descrizione': 'Famiglie 3 componenti',
        'codice': 'PF5'
    },
    'famiglie_4_componenti': {
        'descrizione': 'Famiglie 4 componenti',
        'codice': 'PF6'
    },
    'famiglie_5_componenti': {
        'descrizione': 'Famiglie 5 componenti',
        'codice': 'PF7'
    },
    'famiglie_6_componenti_e_oltre': {
        'descrizione': 'Famiglie 6 e oltre componenti',
        'codice': 'PF8'
    },
    'famiglie_residenti_oltre_6_componenti': {
        'descrizione': 'Componenti delle famiglie residenti di 6 e oltre componenti',
        'codice': 'PF9'
    },
}
