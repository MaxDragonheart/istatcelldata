from pathlib import Path

from mkdocs.utils.cache import download_url

from istatcelldata.download import download


def test_download(tmp_path: Path):
    print("test_download")
    download_folder = tmp_path.joinpath("download")
    download_folder.mkdir(parents=True, exist_ok=True)

    extract_folder = tmp_path.joinpath("extract")
    extract_folder.mkdir(parents=True, exist_ok=True)

    destination_folder = tmp_path.joinpath("destination")
    destination_folder.mkdir(parents=True, exist_ok=True)

    download_url = "https://www.istat.it/storage/cartografia/basi_territoriali/WGS_84_UTM/1991/R15_91_WGS84.zip"
    data_file_name = Path(download_url).stem + Path(download_url).suffix
    print(data_file_name)

    data = download(
        data_link=download_url,
        data_file_path_destination=download_folder.joinpath(data_file_name),
        data_folder=extract_folder,
        destination_folder=destination_folder
    )
    print(data)
    assert isinstance(data, Path)
