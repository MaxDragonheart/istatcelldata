import csv
import logging
import os
import zipfile
from pathlib import Path

import chardet
import xlrd
from tqdm import tqdm

from istatcelldata.logger_config import configure_logging

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def check_encoding(data: Path) -> str:
    """Determine file encoding by reading an initial sample.

    This function opens the file in binary mode, reads the first 100,000 bytes,
    and uses the `chardet` library to estimate the text encoding. If `chardet`
    identifies the encoding as `'ascii'`, it is converted to `'latin1'` to ensure
    greater compatibility, since many administrative and geographic files may contain
    extended characters while being formally interpreted as ASCII.

    Args:
        data: Path to the file whose encoding should be determined.

    Returns:
        The detected encoding. If `'ascii'` is detected, it is automatically
        replaced with `'latin1'`.

    Note:
        `chardet` provides a heuristic estimate of encoding and is not infallible.
        Reading is limited to the first 100,000 bytes to improve performance.
        `'latin1'` is a safe choice to avoid errors on files with accented
        characters or ambiguous encodings typical of ISTAT administrative datasets.
    """
    # Open file in binary mode and read first 100,000 bytes for
    # encoding detection.
    with open(data, "rb") as rawdata:
        # Use chardet to detect encoding
        result = chardet.detect(rawdata.read(100000))

        # If detected encoding is 'ascii', change it to 'latin1' for better compatibility
        if result["encoding"] == "ascii":
            result["encoding"] = "latin1"

    # Return detected encoding, default to 'latin1' if None
    return result["encoding"] or "latin1"


def csv_from_excel(data: Path, output_path: Path, metadata: bool = False) -> Path:
    """Convert an Excel file (.xls) to CSV format.

    This function reads a legacy Excel file (.xls) using `xlrd` and converts
    the content of a sheet to a CSV file. If `metadata=True`, the sheet named
    **"Metadati"** is converted; otherwise, the first available sheet is converted,
    excluding "Metadati" if present.

    The conversion preserves row order and writes all fields using `csv.QUOTE_ALL`
    to ensure compatibility and preserve delimiters, strings with spaces, or
    special characters.

    Args:
        data: Path to the Excel file to convert.
        output_path: Path where the output CSV file will be saved.
        metadata: If True, converts the "Metadati" sheet. If False, converts
            the first available sheet excluding "Metadati". Defaults to False.

    Returns:
        Path to the generated CSV file.

    Raises:
        FileNotFoundError: If the specified Excel file does not exist.
        xlrd.XLRDError: If the file cannot be read or the requested sheet does
            not exist.
        Exception: For any other errors during conversion or writing.

    Note:
        The conversion uses `xlrd`, so the file must be in `.xls` format
        (Excel legacy). `.xlsx` files are not supported by xlrd.
        The CSV is saved in UTF-8 encoding.
        The function uses `tqdm` to display a progress bar.
    """
    try:
        logging.info(f"Reading Excel file from {data}")

        # Read Excel file
        read_data = xlrd.open_workbook(data)

        # If metadata reading is requested
        if metadata:
            sheet_name = "Metadati"
            logging.info("Converting 'Metadati' sheet.")
        else:
            # Get list of sheets, excluding 'Metadati' if present
            sheet_list = read_data.sheet_names()
            if "Metadati" in sheet_list:
                sheet_list.remove("Metadati")
            sheet_name = sheet_list[0]  # First available sheet
            logging.info(f"Converting sheet: {sheet_name}")

        # Extract sheet to convert
        get_sheet = read_data.sheet_by_name(sheet_name)

        # Create and write to CSV file
        with open(output_path, "w", newline="", encoding="utf-8") as output_data:
            write_csv = csv.writer(output_data, quoting=csv.QUOTE_ALL)

            logging.info(f"Converting sheet '{sheet_name}' to CSV.")
            for row_id in tqdm(range(get_sheet.nrows), desc="Conversion"):
                write_csv.writerow(get_sheet.row_values(row_id))

        logging.info(f"Converted data saved to {output_path}.")
        return output_path

    except FileNotFoundError as e:
        logging.error(f"Excel file not found: {data}")
        raise e
    except xlrd.XLRDError as e:
        logging.error(f"Error reading Excel file: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"Error during Excel to CSV conversion: {str(e)}")
        raise e


def census_folder(output_data_folder: Path, year: int) -> Path:
    """Create (if necessary) the folder dedicated to census data for a specific year.

    This function generates a directory named `census_<year>` within the
    `output_data_folder` and creates it if it doesn't already exist. This folder
    represents the root of downloaded and processed data for a specific census,
    maintaining an organized and consistent structure across different years.

    Args:
        output_data_folder: Main folder under which to create the census directory.
        year: Census year to organize (e.g., 1991, 2001, 2011, 2021).

    Returns:
        Complete path to the created or existing census folder.

    Raises:
        Exception: If the folder cannot be created due to permissions or invalid paths.
    """
    try:
        # Log process start
        logging.info(f"Creating folder for census data {year}.")

        # Folder name based on census year
        download_folder_name = f"census_{year}"

        # Complete folder path
        destination_folder = output_data_folder.joinpath(download_folder_name)

        # Create folder (if it doesn't already exist)
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Log success
        logging.info(f"Folder created or already exists: {destination_folder}")

        return destination_folder

    except Exception as e:
        # Log errors
        logging.error(f"Error creating folder for census {year}: {str(e)}")
        raise e


def unzip_data(input_data: Path, output_folder: Path) -> Path:
    """Decompress a ZIP file into the specified destination folder.

    This function opens a ZIP archive and extracts its entire content into the
    specified folder. If the output folder does not exist, it is created automatically.
    Functions as an internal component of the ISTAT data download workflow.

    Args:
        input_data: Path to the ZIP file to decompress.
        output_folder: Folder where the archive content will be extracted.

    Returns:
        Path to the folder containing the extracted files.

    Raises:
        FileNotFoundError: If the ZIP file does not exist.
        zipfile.BadZipFile: If the provided file is not a valid ZIP archive.
        Exception: For any error during decompression.
    """
    try:
        logging.info(f"Decompressing file {input_data} to folder {output_folder}.")

        # Check if output folder exists, otherwise create it
        output_folder.mkdir(parents=True, exist_ok=True)

        # Decompress ZIP file
        with zipfile.ZipFile(input_data, "r") as zf:
            zf.extractall(output_folder)

        logging.info(f"Decompression completed. Files extracted to {output_folder}.")
        return output_folder

    except FileNotFoundError as e:
        logging.error(f"ZIP file not found: {input_data}")
        raise e
    except zipfile.BadZipFile as e:
        logging.error(f"The provided file is not a valid ZIP file: {input_data}")
        raise e
    except Exception as e:
        logging.error(f"Error during decompression: {str(e)}")
        raise e


def get_region(region_list: list[int] = []) -> list[int]:
    """Return the list of regions to use for geodata download.

    If no list is provided, returns the complete list of 20 Italian regions
    (codes 1–20). Otherwise, returns the provided list.

    Args:
        region_list: Optional list of region codes to use.
            If empty, returns all regions (1–20).

    Returns:
        List of region codes to process.
    """
    if len(region_list) == 0:
        regions = list(range(1, 21, 1))
    else:
        regions = region_list

    return regions


def get_census_dictionary(census_year: int, region_list: list[int] = []) -> dict:
    """Generate official ISTAT URLs for census data, geodata, and administrative boundaries.

    This function dynamically constructs download paths based on the census year
    and the list of desired regions. It handles structural differences between
    previous censuses (1991–2011) and the 2021 census.

    Args:
        census_year: Census year (1991, 2001, 2011, or 2021).
        region_list: Optional list of regions for which to generate geodata URLs.
            If empty, uses regions 1–20.

    Returns:
        Dictionary containing the URLs:
            - `data_url`: URL for census data
            - `geodata_urls`: URLs for territorial bases
            - `admin_boundaries_url`: URL for administrative boundaries
            - `census_code`: Primary code for joins and identifiers

    Raises:
        ValueError: If the provided year is not supported.
    """
    main_link = "https://www.istat.it/storage/cartografia"
    census = [1991, 2001, 2011, 2021]
    if census_year in census:
        year_code = str(census_year)[2:]

        regions = get_region(region_list=region_list)

        geodata_urls = []

        for region in regions:
            region_str = str(region).zfill(2)

            if census_year in [1991, 2001, 2011]:
                geodata_file = f"R{region_str}_{year_code}_WGS84.zip"
                geodata_url = (
                    f"{main_link}/basi_territoriali/WGS_84_UTM/{census_year}/{geodata_file}"
                )
            else:
                geodata_file = f"R{region_str}_{year_code}.zip"
                geodata_url = f"{main_link}/basi_territoriali/{census_year}/{geodata_file}"
            geodata_urls.append(geodata_url)

        if census_year in [1991, 2001, 2011]:
            data_url = f"{main_link}/variabili-censuarie/dati-cpa_{census_year}.zip"
            census_code = f"sez{census_year}"

        else:
            data_url = "https://esploradati.istat.it/databrowser/DWL/PERMPOP/SUBCOM/Dati_regionali_2021.zip"
            census_code = "sez21_id"

        if census_year == 2011:
            boundaries_folder = f"{census_year}/Limiti_{census_year}_WGS84.zip"
        else:
            boundaries_folder = f"Limiti{census_year}.zip"

        admin_boundaries_url = (
            f"{main_link}/confini_amministrativi/non_generalizzati/{boundaries_folder}"
        )
        links_dict = {
            f"census{census_year}": {
                "data_url": data_url,
                "geodata_urls": geodata_urls,
                "admin_boundaries_url": admin_boundaries_url,
                "census_code": census_code,
            }
        }

        return links_dict

    else:
        raise ValueError(
            f"The selected census year is not supported. You can choose from {census}."
        )


def remove_files(files_path: list) -> None:
    """Remove a list of files from the filesystem.

    Args:
        files_path: List of Path objects to delete.

    Note:
        Exceptions are not caught: if a file cannot be deleted, the error
        emerges explicitly (desirable behavior in ETL workflows).
    """
    # Remove files
    for file_path in files_path:
        os.remove(file_path)
