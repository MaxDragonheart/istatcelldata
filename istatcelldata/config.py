from pathlib import Path

DEMO_DATA_FOLDER = Path(__file__).parent.parent.joinpath('demo_data')

GEOMETRY_COLUMN_NAME = 'geometry'
GLOBAL_ENCODING = 'utf-8'

# PROJECT FOLDERS
DATA_FOLDER = 'data'
GEODATA_FOLDER = 'geodata'
PREPROCESSING_FOLDER = 'preprocessing'
CENSUS_DATA_FOLDER = 'Sezioni di Censimento'
BOUNDARIES_DATA_FOLDER = 'administrative_boundaries'
YEAR_GEODATA_NAME = "census"


census_data = {
    1991: {
        'regions_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Reg1991", "Reg1991_WGS84.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Prov1991", "Prov1991_WGS84.shp"),
        'provinces_column': ['COD_PROV', 'DEN_PROV', 'SIGLA'],
        'municipalities_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Com1991", "Com1991_WGS84.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PROV'],
        'census_shp_root': ("census_1991", GEODATA_FOLDER),
        'census_shp_column': ['SEZ1991', 'TIPO_LOC', GEOMETRY_COLUMN_NAME],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'case sparse'
        }
    },
    2001: {
        'regions_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Reg2001", "Reg2001_WGS84.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Prov2001", "Prov2001_WGS84.shp"),
        'provinces_column': ['COD_PROV', 'DEN_PROV', 'SIGLA'],
        'municipalities_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Com2001", "Com2001_WGS84.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PROV'],
        'census_shp_root': ("census_2001", GEODATA_FOLDER),
        'census_shp_column': ['SEZ2001', 'TIPO_LOC', GEOMETRY_COLUMN_NAME],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        }
    },
    2011: {
        'regions_root': ("census_2011", BOUNDARIES_DATA_FOLDER, "Limiti_2011_WGS84", "Reg2011_WGS84", "Reg2011_WGS84.shp"),
        'regions_column': ['COD_REG', 'REGIONE'],
        'regions_column_remapping': {'REGIONE': 'DEN_REG'},
        'provinces_root': ("census_2011", BOUNDARIES_DATA_FOLDER, "Limiti_2011_WGS84", "Prov2011_WGS84", "Prov2011_WGS84.shp"),
        'provinces_column': ['COD_PRO', 'PROVINCIA', 'SIGLA'],
        'provinces_column_remapping': {'PROVINCIA': 'DEN_PROV'},
        'municipalities_root': ("census_2011", BOUNDARIES_DATA_FOLDER, "Limiti_2011_WGS84", "Com2011_WGS84", "Com2011_WGS84.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PRO'],
        'municipalities_column_remapping': {'COD_PRO': 'COD_PROV'},
        'census_shp_root': ("census_2011", GEODATA_FOLDER),
        'census_shp_column': ['SEZ2011', 'TIPO_LOC', GEOMETRY_COLUMN_NAME],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        }
    },
    2021: {
        'regions_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "Reg2021", "Reg2021.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "ProvCM2021", "ProvCM2021.shp"),
        'provinces_column': ['COD_PROV', 'DEN_UTS', 'SIGLA', 'TIPO_UTS'],
        'provinces_column_remapping': {'DEN_UTS': 'DEN_PROV'},
        'municipalities_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "Com2021", "Com2021.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG'],
        'census_shp_root': ("census_2021", GEODATA_FOLDER),
        'census_shp_column': ['SEZ21_ID', 'TIPO_LOC', GEOMETRY_COLUMN_NAME],
        'census_shp_column_remapping': {'SEZ21_ID': 'SEZ2021'},
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        }
    }
}
