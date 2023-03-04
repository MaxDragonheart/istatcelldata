Modulo Dati
============================

I dati censuari risultano essere differenti tra anno ed anno non solo per il loro contenuto ma anche per la struttura dati con cui sono stati condivisi.
In particolare gli anni 1991 e 2001 risultano avere una struttura dati uguale, mentre nel 2011 si ha una struttura totalmente differente.
Si è scelto dunque di normalizzare i dati 1991-2001 secondo la struttura dati del 2011 perchè per questo anno abbiamo i dati censuari pubblicati come `csv`,
formato_ file più adatto alla condivisione dei dati rispetto a `xls`.

Anni 1991-2001
----------------------------
.. autofunction:: census_istat.data.census_1991_2001.read_xls(file_path: Union[Path, PosixPath], census_code: str = 'sez1991', output_path: Union[Path, PosixPath] = None, metadata: bool = False) -> Union[DataFrame, Path, PosixPath]
.. autofunction:: census_istat.data.census_1991_2001.census_trace(file_path: Union[Path, PosixPath], year: int, output_path: Union[Path, PosixPath], ) -> Union[Path, PosixPath]
.. autofunction:: census_istat.data.census_1991_2001.remove_xls(folder_path: Union[Path, PosixPath], census_code: str, output_path: Union[Path, PosixPath]) -> None
.. autofunction:: census_istat.data.census_1991_2001.compare_dataframe(data: list) -> DataFrame
.. autofunction:: census_istat.data.census_1991_2001.preprocess_csv_1991_2001(census_year: int, output_path: Union[Path, PosixPath], census_data_folder: Union[Path, PosixPath]) -> Union[Path, PosixPath]
.. autofunction:: census_istat.data.census_1991_2001.merge_data_1991_2001(csv_path: Union[Path, PosixPath], year: int, separator: str = ';', output_path: Union[Path, PosixPath] = None) -> Union[Path, PosixPath, DataFrame]
.. autofunction:: census_istat.data.census_1991_2001._merge_administrative_data(data_path: Union[Path, PosixPath], year: int) -> DataFrame

Anno 2011
----------------------------
.. autofunction:: census_istat.data.manage_data.read_csv(csv_path: Union[Path, PosixPath], separator: str = ';') -> DataFrame
.. autofunction:: census_istat.data.manage_data.merge_data(csv_path: Union[Path, PosixPath], year: int, separator: str = ';', output_path: Union[Path, PosixPath] = None) -> Union[Path, PosixPath, DataFrame]
.. autofunction:: census_istat.data.manage_data.list_shared_columns() -> list


.. _formato: https://en.wikipedia.org/wiki/Comma-separated_values#Data_exchange