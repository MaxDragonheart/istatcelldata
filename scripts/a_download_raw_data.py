from pathlib import Path
from istatcelldata.processes import download_raw_data

main_path = Path("/home/max/Desktop")
list_year = [1991]
list_region = [15, 17]

if __name__ == '__main__':
    download_raw_data(
        output_data_folder=main_path,
        year_list=list_year,
        region_list=list_region
    )
