"""Preferred import facade for geographic census data helpers."""

from istatcelldata.geodata import (
    preprocess_geodata,
    read_administrative_boundaries,
    read_census,
)

__all__ = [
    "preprocess_geodata",
    "read_administrative_boundaries",
    "read_census",
]
