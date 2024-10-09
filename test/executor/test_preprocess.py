from pathlib import Path

from istatcelldata.executor.preprocess import preprocess_census

main_folder = Path("/home/max/Desktop/census/preprocessing")

def test_preprocess_census(tmp_path: Path):
    print("test_preprocess_census")
    data = preprocess_census(
        processed_data_dir=main_folder,
        years=[2001],
        regions=True,
        provinces=True,
        municipalities=True,
        output_data_folder=tmp_path
    )
    print(data)
    assert isinstance(data, Path)