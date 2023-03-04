Processi generici
==============

.. autofunction:: census_istat.generic.check_encoding(data: Union[Path, PosixPath]) -> str
.. autofunction:: census_istat.generic.csv_from_excel(data: Union[Path, PosixPath], output_path: Union[Path, PosixPath], metadata: bool = False) -> Union[Path, PosixPath]
.. autofunction:: census_istat.generic.census_folder(output_data_folder: Union[Path, PosixPath], year: int = 2011) -> Union[Path, PosixPath]
.. autofunction:: census_istat.generic.census_geodata_folder(output_data_folder: Union[Path, PosixPath], year: int) -> Union[Path, PosixPath]
.. autofunction:: census_istat.generic.unzip_data(input_data: Union[Path, PosixPath], output_folder: Union[Path, PosixPath]) -> Union[Path, PosixPath]
.. autofunction:: census_istat.generic.get_metadata(input_path: Union[Path, PosixPath], output_path: Union[Path, PosixPath]) -> list