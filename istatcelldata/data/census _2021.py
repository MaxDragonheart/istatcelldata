from pathlib import Path
from typing import Union

from pandas import DataFrame


def read_xlsx(
        file_path: Path,
        output_path: Path = None,
) -> Union[DataFrame, Path]:
    #data = pd.read_excel(file_path, sheet_name=None)