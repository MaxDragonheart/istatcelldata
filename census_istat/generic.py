import csv
import logging

import chardet
import xlrd
from tqdm import tqdm


def check_encoding(data: str):
    """Check file encoding

    Args:
        data: str

    Returns:
        str
    """
    # Look at the first ten thousand bytes to guess the character encoding
    with open(data, 'rb') as rawdata:
        result = chardet.detect(rawdata.read(100000))

        if result['encoding'] == 'ascii':
            result['encoding'] = 'latin1'

    return result['encoding']


def csv_from_excel(data: str, output_path: str) -> str:
    """Convert xls to csv

    Args:
        data: str
        output_path: str

    Returns:
        str
    """
    sheet_name = data.stem.split('\\')[1][:-5]

    logging.info(f'Read data from {sheet_name}')
    read_data = xlrd.open_workbook(data)
    get_sheet = read_data.sheet_by_name(sheet_name)
    output_data = open(output_path, 'w')
    write_csv = csv.writer(output_data, quoting=csv.QUOTE_ALL)

    logging.info('Convert xls to csv')
    for row_id in tqdm(range(get_sheet.nrows)):
        write_csv.writerow(get_sheet.row_values(row_id))

    output_data.close()

    return output_path
