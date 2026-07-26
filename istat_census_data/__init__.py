"""ISTAT Census Data - Italian census cell data processing library.

ISTAT Census Data provides easy access to Italian National Institute of Statistics
(ISTAT) census data, including census grid cell datasets from complete population
censuses.

This library allows you to download and process census data from 1991 to 2021,
including demographic data and geographic information (shapefiles, administrative
boundaries) for census sections across Italy.
"""

__version__ = "2.2.0"
__author__ = "Massimiliano Moraca"
__email__ = "gis.massimilianomoraca@gmail.com"

# Expose main modules for convenient imports
from istat_census_data import census1991, census2001, census2011, census2021, executor
from istat_census_data.catalog import (
    get_census_index_catalog,
    get_comparable_indexes,
    list_census_indexes,
)
from istat_census_data.config import DOWNLOAD_RAW_DATA, census_data
from istat_census_data.data import preprocess_data
from istat_census_data.download import download_base
from istat_census_data.executor.process import finalize_census_data
from istat_census_data.geodata import (
    preprocess_geodata,
    read_administrative_boundaries,
    read_census,
)
from istat_census_data.h3_estimation import (
    REQUIRED_H3_RESOLUTION,
    estimate_h3_census_indexes,
    generate_h3_grid,
)
from istat_census_data.h3_workflow import (
    H3CensusWorkflowResult,
    run_h3_census_workflow,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Submodules
    "census1991",
    "census2001",
    "census2011",
    "census2021",
    "executor",
    "get_census_index_catalog",
    "get_comparable_indexes",
    "list_census_indexes",
    # Configuration
    "census_data",
    "DOWNLOAD_RAW_DATA",
    # Main functions
    "download_base",
    "preprocess_data",
    "read_administrative_boundaries",
    "read_census",
    "preprocess_geodata",
    "finalize_census_data",
    "REQUIRED_H3_RESOLUTION",
    "generate_h3_grid",
    "estimate_h3_census_indexes",
    "H3CensusWorkflowResult",
    "run_h3_census_workflow",
]
