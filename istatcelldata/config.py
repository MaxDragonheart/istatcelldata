from pathlib import Path

DEMO_DATA_FOLDER = Path(__file__).parent.parent.joinpath('demo_data')

GEOMETRY_COLUMN_NAME = 'geometry'
GLOBAL_ENCODING = 'utf-8'

# TEST FOLDERS
DOWNLOAD_RAW_DATA = DEMO_DATA_FOLDER.joinpath('download')


# PROJECT FOLDERS
DATA_FOLDER = 'data'
GEODATA_FOLDER = 'geodata'
PREPROCESSING_FOLDER = 'preprocessing'
CENSUS_DATA_FOLDER = 'Sezioni di Censimento'
BOUNDARIES_DATA_FOLDER = 'administrative_boundaries'
YEAR_GEODATA_NAME = "census"


census_data = {
    1991: {
        'data_root': ("census_1991", DATA_FOLDER, CENSUS_DATA_FOLDER),
        'regions_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Reg1991", "Reg1991_WGS84.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Prov1991", "Prov1991_WGS84.shp"),
        'provinces_column': ['COD_PROV', 'DEN_PROV', 'SIGLA'],
        'municipalities_root': ("census_1991", BOUNDARIES_DATA_FOLDER, "Limiti1991", "Com1991", "Com1991_WGS84.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PROV'],
        'census_shp_root': ("census_1991", GEODATA_FOLDER),
        'census_shp_column': [
            'COD_ISTAT', 'PRO_COM', 'SEZ1991', 'SEZ', 'ISOLATO',
            'COD_IS_AMM', 'COD_ZONA_C', 'COD_AREA', 'LOC1991', 'COD_LOC',
            'TIPO_LOC', GEOMETRY_COLUMN_NAME
        ],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'case sparse'
        },
        'add_administrative_informations': True
    },
    2001: {
        'data_root': ("census_2001", DATA_FOLDER, CENSUS_DATA_FOLDER),
        'regions_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Reg2001", "Reg2001_WGS84.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Prov2001", "Prov2001_WGS84.shp"),
        'provinces_column': ['COD_PROV', 'DEN_PROV', 'SIGLA'],
        'municipalities_root': ("census_2001", BOUNDARIES_DATA_FOLDER, "Limiti2001", "Limiti2001", "Com2001", "Com2001_WGS84.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG', 'COD_PROV'],
        'census_shp_root': ("census_2001", GEODATA_FOLDER),
        'census_shp_column': [
            'COD_ISTAT', 'PRO_COM', 'SEZ2001', 'SEZ', 'COD_TIPO', 'COD_STAGNO', 'COD_FIUME', 'COD_LAGO', 'COD_LAGUNA',
            'COD_VAL_P', 'COD_ZONA_C', 'COD_IS_AMM', 'COD_IS_LAC', 'COD_IS_MAR', 'COD_AREA_S', 'COD_MONT_D', 'LOC2001',
            'COD_LOC', 'TIPO_LOC', GEOMETRY_COLUMN_NAME
        ],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        },
        'add_administrative_informations': True
    },
    2011: {
        'data_root': ("census_2011", DATA_FOLDER, CENSUS_DATA_FOLDER),
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
        'census_shp_column': [
            'COD_REG', 'COD_ISTAT', 'PRO_COM', 'SEZ2011', 'SEZ', 'COD_STAGNO', 'COD_FIUME', 'COD_LAGO', 'COD_LAGUNA',
            'COD_VAL_P', 'COD_ZONA_C', 'COD_IS_AMM', 'COD_IS_LAC', 'COD_IS_MAR', 'COD_AREA_S', 'COD_MONT_D', 'LOC2011',
            'COD_LOC', 'TIPO_LOC', 'COM_ASC', 'COD_ASC', 'ACE', GEOMETRY_COLUMN_NAME
        ],
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        }
    },
    2021: {
        'data_root': ("census_2021", DATA_FOLDER, CENSUS_DATA_FOLDER),
        'regions_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "Reg2021", "Reg2021.shp"),
        'regions_column': ['COD_REG', 'DEN_REG'],
        'provinces_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "ProvCM2021", "ProvCM2021.shp"),
        'provinces_column': ['COD_PROV', 'DEN_UTS', 'SIGLA', 'TIPO_UTS'],
        'provinces_column_remapping': {'DEN_UTS': 'DEN_PROV'},
        'municipalities_root': ("census_2021", BOUNDARIES_DATA_FOLDER, "Limiti2021", "Com2021", "Com2021.shp"),
        'municipalities_column': ['PRO_COM', 'COMUNE', 'COD_REG'],
        'census_shp_root': ("census_2021", GEODATA_FOLDER),
        'census_shp_column': [
            'COD_REG', 'COD_UTS', 'PRO_COM', 'SEZ21', 'SEZ21_ID', 'COD_TIPO_S', 'TIPO_LOC', 'LOC21_ID', 'COD_ZIC',
            'COD_ISAM', 'COD_ACQUE', 'COD_ISOLE', 'COD_MONT_D', 'COD_AREA_S', 'COM_ASC1', 'COM_ASC2', 'COM_ASC3',
            GEOMETRY_COLUMN_NAME
        ],
        'census_shp_column_remapping': {'SEZ21_ID': 'SEZ2021'},
        'tipo_loc_mapping': {
            1: 'centro abitato',
            2: 'nucleo abitato',
            3: 'località produttiva',
            4: 'case sparse'
        }
    }
}
