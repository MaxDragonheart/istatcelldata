Modulo GeoDati
==============

.. autofunction:: census_istat.geodata.manage_geodata.read_raw_geodata(data_path: Union[Path, PosixPath], year: int) -> GeoDataFrame
.. autofunction:: census_istat.geodata.manage_geodata.read_raw_census_geodata(data_path: Union[Path, PosixPath], year: int, output_path: Union[Path, PosixPath] = None) -> Union[Path, PosixPath, GeoDataFrame]
.. autofunction:: census_istat.geodata.manage_geodata.read_geodata(geodata_path: Union[Path, PosixPath]) -> GeoDataFrame
.. autofunction:: census_istat.geodata.manage_geodata.join_year_census(data_path: Union[Path, PosixPath], year: int, remove_processed: bool = False, only_shared: bool = True, output_path: Union[Path, PosixPath] = None) -> Union[Path, PosixPath, GeoDataFrame]
