"""Preferred import facade for ISTAT Census Data.

The project is distributed on PyPI as ``istat-census-data``. Starting with version
1.5.0, users can import the package as ``istat_census_data`` while the existing
``istatcelldata`` import path remains available for compatibility.
"""

import istatcelldata as _legacy_package
from istat_census_data import (
    census1991 as census1991,
)
from istat_census_data import (
    census2001 as census2001,
)
from istat_census_data import (
    census2011 as census2011,
)
from istat_census_data import (
    census2021 as census2021,
)
from istat_census_data import (
    executor as executor,
)
from istatcelldata.config import DOWNLOAD_RAW_DATA as DOWNLOAD_RAW_DATA
from istatcelldata.config import census_data as census_data
from istatcelldata.data import preprocess_data as preprocess_data
from istatcelldata.download import download_base as download_base
from istatcelldata.executor.process import finalize_census_data as finalize_census_data
from istatcelldata.geodata import (
    preprocess_geodata as preprocess_geodata,
)
from istatcelldata.geodata import (
    read_administrative_boundaries as read_administrative_boundaries,
)
from istatcelldata.geodata import (
    read_census as read_census,
)

__version__ = _legacy_package.__version__
__author__ = _legacy_package.__author__
__email__ = _legacy_package.__email__
__all__ = list(_legacy_package.__all__)
