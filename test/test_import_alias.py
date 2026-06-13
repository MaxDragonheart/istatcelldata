import importlib
import warnings

import istat_census_data
import istatcelldata


def test_preferred_and_legacy_import_paths_share_metadata():
    """The new import facade and legacy package expose the same package metadata."""
    assert istat_census_data.__version__ == "1.5.0"
    assert istat_census_data.__version__ == istatcelldata.__version__
    assert istat_census_data.__author__ == istatcelldata.__author__
    assert istat_census_data.__email__ == istatcelldata.__email__
    assert istat_census_data.__all__ == istatcelldata.__all__


def test_preferred_import_path_emits_no_warning_on_import():
    """Importing the preferred facade should be quiet during the coexistence phase."""
    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        importlib.reload(istat_census_data)

    assert captured_warnings == []


def test_preferred_import_path_reuses_public_objects():
    """Public top-level objects stay identical across both import paths."""
    public_names = [
        "census_data",
        "DOWNLOAD_RAW_DATA",
        "download_base",
        "preprocess_data",
        "read_administrative_boundaries",
        "read_census",
        "preprocess_geodata",
        "finalize_census_data",
    ]

    for public_name in public_names:
        assert getattr(istat_census_data, public_name) is getattr(istatcelldata, public_name)


def test_preferred_submodule_imports_reexport_legacy_public_api():
    """Submodule imports through the new facade expose the existing implementation."""
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
        "download": ["download_base"],
        "geodata": [
            "preprocess_geodata",
            "read_administrative_boundaries",
            "read_census",
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
        preferred_module = importlib.import_module(f"istat_census_data.{submodule_name}")
        legacy_module = importlib.import_module(f"istatcelldata.{submodule_name}")

        assert preferred_module.__name__ == f"istat_census_data.{submodule_name}"

        for public_name in public_names:
            assert getattr(preferred_module, public_name) is getattr(legacy_module, public_name)
