from istatcelldata.config import GEOMETRY_COLUMN_NAME, GEODATA_FOLDER, BOUNDARIES_DATA_FOLDER

YEAR = 2021

REGIONS_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"Reg{YEAR}", f"Reg{YEAR}.shp"
REGIONS_COLUMN = ['COD_REG', 'DEN_REG']

PROVINCES_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"ProvCM{YEAR}", f"ProvCM{YEAR}.shp"
PROVINCES_COLUMN = ['COD_PROV', 'DEN_UTS', 'SIGLA', 'TIPO_UTS']
PROVINCES_COLUMN_REMAPPING = {'DEN_UTS': 'DEN_PROV'}

MUNICIPALITIES_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"Com{YEAR}", f"Com{YEAR}.shp"
MUNICIPALITIES_COLUMN = ['PRO_COM', 'COMUNE', 'COD_REG']

CENSUS_SHP_ROOT = f"census_{YEAR}", GEODATA_FOLDER
CENSUS_SHP_COLUMN = ['SEZ21_ID', 'TIPO_LOC', GEOMETRY_COLUMN_NAME]
CENSUS_SHP_COLUMN_REMAPPING = {'SEZ21_ID': f'SEZ{YEAR}'}
TIPO_LOC_MAPPING = {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'località produttiva',
        4: 'case sparse'
    }
