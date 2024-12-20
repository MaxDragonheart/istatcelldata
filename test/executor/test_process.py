from pathlib import Path

from istatcelldata.executor.process import finalize_census_data

main_folder = Path("/home/max/Desktop/census")

def test_finalize_census_data(tmp_path: Path):
    print("test_finalize_census_data")
    finalize_census_data(
        census_data_path=main_folder,
        years=[2021],
        output_data_folder=tmp_path,
        delete_preprocessed_data=False,
    )