from istatcelldata.processes import process_data
from scripts.a_download_raw_data import main_path

if __name__ == '__main__':
    process_data(
        output_data_folder=main_path,
        only_shared=False,
        delete_process_folder=False
    )
