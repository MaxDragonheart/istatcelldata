"""ISTAT Cell Data - Italian census cell data processing library.

ISTAT Cell Data provides easy access to Italian National Institute of Statistics
(ISTAT) census data, including census grid cell datasets from complete population
censuses.

This library allows you to download and process census data from 1991 to 2021,
including demographic data and geographic information (shapefiles, administrative
boundaries) for census sections across Italy.
"""

__version__ = "1.3.0"
__author__ = "Massimiliano Moraca"
__email__ = "gis.massimilianomoraca@gmail.com"

# Expose main modules for convenient imports
from istatcelldata import census1991, census2001, census2011, census2021, executor
from istatcelldata.config import DOWNLOAD_RAW_DATA, census_data
from istatcelldata.data import preprocess_data
from istatcelldata.download import download_base
from istatcelldata.executor.process import finalize_census_data
from istatcelldata.geodata import (
    preprocess_geodata,
    read_administrative_boundaries,
    read_census,
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
]
