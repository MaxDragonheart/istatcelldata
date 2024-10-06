from istatcelldata.config import GEOMETRY_COLUMN_NAME, GEODATA_FOLDER, BOUNDARIES_DATA_FOLDER

YEAR = 2001

REGIONS_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"Limiti{YEAR}", f"Reg{YEAR}", f"Reg{YEAR}_WGS84.shp"
REGIONS_COLUMN = ['COD_REG', 'DEN_REG']

PROVINCES_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"Limiti{YEAR}", f"Prov{YEAR}", f"Prov{YEAR}_WGS84.shp"
PROVINCES_COLUMN = ['COD_PROV', 'DEN_PROV', 'SIGLA']

MUNICIPALITIES_ROOT = f"census_{YEAR}", BOUNDARIES_DATA_FOLDER, f"Limiti{YEAR}", f"Limiti{YEAR}", f"Com{YEAR}", f"Com{YEAR}_WGS84.shp"
MUNICIPALITIES_COLUMN = ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PROV']

CENSUS_SHP_ROOT = f"census_{YEAR}", GEODATA_FOLDER
CENSUS_SHP_COLUMN = [f'SEZ{YEAR}', 'TIPO_LOC', GEOMETRY_COLUMN_NAME]
TIPO_LOC_MAPPING = {
        1: 'centro abitato',
        2: 'nucleo abitato',
        3: 'località produttiva',
        4: 'case sparse'
    }
