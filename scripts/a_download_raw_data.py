from pathlib import Path
from istatcelldata.processes import download_raw_data

main_path = Path("/home/max/Desktop")

if __name__ == '__main__':
    download_raw_data(
        output_data_folder=main_path,
        year_list=[2001],
        region_list=[15]
    )
