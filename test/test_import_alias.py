import importlib
import importlib.util
import warnings

import istat_census_data


def test_canonical_import_path_exposes_metadata():
    """The canonical package exposes the expected 2.4.1 metadata."""
    assert istat_census_data.__version__ == "2.4.1"
    assert istat_census_data.__author__ == "Massimiliano Moraca"
    assert istat_census_data.__email__ == "gis.massimilianomoraca@gmail.com"
    assert "download_base" in istat_census_data.__all__


def test_canonical_import_path_emits_no_warning_on_import():
    """Importing the canonical package should be quiet."""
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        importlib.reload(istat_census_data)

    assert captured_warnings == []


def test_legacy_import_path_is_removed():
    """The legacy package name is no longer importable in 2.0.0."""
    assert importlib.util.find_spec("istatcelldata") is None


def test_canonical_submodule_imports_expose_public_api():
    """Submodule imports through the canonical package expose the public API."""
    submodules = {
        "config": [
            "BOUNDARIES_DATA_FOLDER",
            "CENSUS_DATA_FOLDER",
            "DATA_FOLDER",
            "DEMO_DATA_FOLDER",
            "DOWNLOAD_RAW_DATA",
            "GEODATA_FOLDER",
            "GEOMETRY_COLUMN_NAME",
            "GLOBAL_ENCODING",
            "PREPROCESSING_FOLDER",
            "YEAR_GEODATA_NAME",
            "census_data",
        ],
        "data": ["preprocess_data"],
        "catalog": [
            "get_census_index_catalog",
            "get_comparable_indexes",
            "list_census_indexes",
        ],
        "download": ["download_base"],
        "geodata": [
            "preprocess_geodata",
            "read_administrative_boundaries",
            "read_census",
        ],
        "h3_estimation": [
            "DEFAULT_BOUNDARY_RING_SIZE",
            "DEFAULT_INTERMEDIATE_STORAGE",
            "REQUIRED_H3_RESOLUTION",
            "estimate_h3_census_indexes",
            "generate_h3_grid",
        ],
        "h3_workflow": [
            "H3CensusWorkflowResult",
            "run_h3_census_workflow",
        ],
        "logger_config": ["configure_logging", "get_log_filename"],
        "utils": [
            "census_folder",
            "check_encoding",
            "csv_from_excel",
            "get_census_dictionary",
            "get_region",
            "remove_files",
            "unzip_data",
        ],
        "census1991": [],
        "census1991.download": ["download_all_census_data_1991", "download_data"],
        "census1991.process": ["add_administrative_info"],
        "census1991.utils": ["census_trace", "read_xls"],
        "census2001": [],
        "census2001.download": ["download_all_census_data_2001"],
        "census2011": [],
        "census2011.download": [
            "download_administrative_boundaries",
            "download_all_census_data_2011",
            "download_data",
            "download_geodata",
        ],
        "census2021": [],
        "census2021.download": ["download_all_census_data_2021", "download_data"],
        "census2021.utils": ["read_xlsx"],
        "executor": [],
        "executor.download": ["download_census"],
        "executor.preprocess": ["preprocess_census"],
        "executor.process": ["finalize_census_data"],
    }

    for submodule_name, public_names in submodules.items():
        canonical_module = importlib.import_module(f"istat_census_data.{submodule_name}")

        assert canonical_module.__name__ == f"istat_census_data.{submodule_name}"

        for public_name in public_names:
            assert hasattr(canonical_module, public_name)
