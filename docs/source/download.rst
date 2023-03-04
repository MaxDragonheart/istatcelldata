Download dei dati
============================

.. autofunction:: census_istat.download.download_census_data(output_data_folder: Union[Path, PosixPath], year: int = 2011) -> Union[Path, PosixPath]
.. autofunction:: census_istat.download.download_census_geodata(output_data_folder: Union[Path, PosixPath], year: int = 2011) -> Union[Path, PosixPath]
.. autofunction:: census_istat.download.download_administrative_boundaries(output_data_folder: Union[Path, PosixPath], year: int = 2011) -> Union[Path, PosixPath]
.. autofunction:: census_istat.download.download_all_census_data(output_data_folder: Union[Path, PosixPath], year: int = 2011) -> None
.. autofunction:: census_istat.download._download_data(data_link: str, data_file_path_destination: Union[Path, PosixPath], data_folder: Union[Path, PosixPath], destination_folder: Union[Path, PosixPath]) -> Union[Path, PosixPath]
