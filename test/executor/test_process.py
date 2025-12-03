from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from istatcelldata.executor.process import finalize_census_data

main_folder = Path("/home/max/Desktop/census")


@pytest.fixture
def mock_census_gpkg(tmp_path):
    """Create a mock GeoPackage file with census and data layers for testing."""
    gpkg_path = tmp_path / "census.gpkg"

    # Create mock geodata (census layer) with geometry
    geodata_1991 = gpd.GeoDataFrame({
        'SEZ1991': ['001', '002', '003'],
        'PRO_COM': ['001001', '001001', '001002'],
        'COD_ISTAT': ['A', 'B', 'C'],
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2)]
    }, crs="EPSG:4326")

    geodata_2021 = gpd.GeoDataFrame({
        'SEZ2021': ['101', '102', '103'],
        'PRO_COM': ['001001', '001001', '001002'],
        'COD_REG': ['01', '01', '02'],
        'geometry': [Point(10, 10), Point(11, 11), Point(12, 12)]
    }, crs="EPSG:4326")

    # Create mock tabular data (data layer)
    data_1991 = pd.DataFrame({
        'SEZ1991': ['001', '002', '003'],
        'SEZ': ['001', '002', '003'],
        'ISOLATO': ['A', 'B', 'C'],
        'COMUNE': ['Rome', 'Milan', 'Naples'],
        'CODREG': ['12', '03', '15'],
        'CODPRO': ['058', '015', '063'],
        'PROVINCIA': ['Roma', 'Milano', 'Napoli'],
        'SIGLA': ['RM', 'MI', 'NA'],
        'REGIONE': ['Lazio', 'Lombardia', 'Campania'],
        'CODCOM': ['058091', '015146', '063049'],
        'SEZIONE': ['001', '002', '003'],
        'POP_TOT': [100, 200, 150],
        'FAM_TOT': [30, 60, 45]
    })

    data_2021 = pd.DataFrame({
        'SEZ2021': ['101', '102', '103'],
        'PRO_COM': ['001001', '001001', '001002'],
        'COMUNE': ['Rome', 'Milan', 'Naples'],
        'CODREG': ['12', '03', '15'],
        'CODPRO': ['058', '015', '063'],
        'PROVINCIA': ['Roma', 'Milano', 'Napoli'],
        'REGIONE': ['Lazio', 'Lombardia', 'Campania'],
        'COM_ASC1': ['A1', 'A2', 'A3'],
        'COM_ASC2': ['B1', 'B2', 'B3'],
        'COM_ASC3': ['C1', 'C2', 'C3'],
        'CODCOM': ['058091', '015146', '063049'],
        'PROCOM': ['RM', 'MI', 'NA'],
        'POP_TOT': [500, 600, 700],
        'FAM_TOT': [150, 180, 210]
    })

    # Save layers to GeoPackage
    geodata_1991.to_file(gpkg_path, driver='GPKG', layer='census1991')
    geodata_2021.to_file(gpkg_path, driver='GPKG', layer='census2021')

    # Convert data to GeoDataFrame to save to GPKG
    data_1991_gdf = gpd.GeoDataFrame(data_1991)
    data_2021_gdf = gpd.GeoDataFrame(data_2021)

    data_1991_gdf.to_file(gpkg_path, driver='GPKG', layer='data1991')
    data_2021_gdf.to_file(gpkg_path, driver='GPKG', layer='data2021')

    return tmp_path, gpkg_path


def test_finalize_census_data_success(mock_census_gpkg, tmp_path):
    """Test successful execution of finalize_census_data."""
    census_path, gpkg_file = mock_census_gpkg
    output_folder = tmp_path / "output"
    output_folder.mkdir()

    # Run finalize_census_data
    finalize_census_data(
        census_data_path=census_path,
        years=[1991],
        output_data_folder=output_folder,
        delete_preprocessed_data=False,
    )

    # Verify output file was created
    output_file = output_folder / "census_data.gpkg"
    assert output_file.exists()

    # Verify layer was created
    result_gdf = gpd.read_file(output_file, layer='census1991')
    assert len(result_gdf) == 3
    assert 'SEZ1991' in result_gdf.columns
    assert 'POP_TOT' in result_gdf.columns
    assert 'geometry' in result_gdf.columns


def test_finalize_census_data_multiple_years(mock_census_gpkg, tmp_path):
    """Test processing multiple years."""
    census_path, gpkg_file = mock_census_gpkg
    output_folder = tmp_path / "output"
    output_folder.mkdir()

    finalize_census_data(
        census_data_path=census_path,
        years=[1991, 2021],
        output_data_folder=output_folder,
        delete_preprocessed_data=False,
    )

    # Verify both layers were created
    output_file = output_folder / "census_data.gpkg"
    assert output_file.exists()

    result_1991 = gpd.read_file(output_file, layer='census1991')
    result_2021 = gpd.read_file(output_file, layer='census2021')

    assert len(result_1991) == 3
    assert len(result_2021) == 3


def test_finalize_census_data_default_output_folder(mock_census_gpkg):
    """Test using default output folder (same as input)."""
    census_path, gpkg_file = mock_census_gpkg

    finalize_census_data(
        census_data_path=census_path,
        years=[1991],
        output_data_folder=None,
        delete_preprocessed_data=False,
    )

    # Output should be in the same folder as input
    output_file = census_path / "census_data.gpkg"
    assert output_file.exists()


def test_finalize_census_data_delete_preprocessed(mock_census_gpkg, tmp_path):
    """Test deletion of preprocessed data."""
    census_path, gpkg_file = mock_census_gpkg
    output_folder = tmp_path / "output"
    output_folder.mkdir()

    # Verify census.gpkg exists before
    assert gpkg_file.exists()

    finalize_census_data(
        census_data_path=census_path,
        years=[1991],
        output_data_folder=output_folder,
        delete_preprocessed_data=True,
    )

    # Verify census.gpkg was deleted
    assert not gpkg_file.exists()

    # Verify output was still created
    output_file = output_folder / "census_data.gpkg"
    assert output_file.exists()


def test_finalize_census_data_missing_gpkg(tmp_path):
    """Test FileNotFoundError when census.gpkg doesn't exist."""
    with pytest.raises(FileNotFoundError, match="Main GeoPackage file not found"):
        finalize_census_data(
            census_data_path=tmp_path,
            years=[1991],
            output_data_folder=tmp_path,
            delete_preprocessed_data=False,
        )


def test_finalize_census_data_missing_join_column(tmp_path):
    """Test KeyError when join column is missing from data."""
    gpkg_path = tmp_path / "census.gpkg"

    # Create geodata without the join column
    geodata = gpd.GeoDataFrame({
        'WRONG_COLUMN': ['001', '002'],
        'geometry': [Point(0, 0), Point(1, 1)]
    }, crs="EPSG:4326")

    # Data has all required columns for removal but missing join column
    data = pd.DataFrame({
        'WRONG_DATA_COLUMN': ['001', '002'],
        'SEZ': ['001', '002'],
        'ISOLATO': ['A', 'B'],
        'COMUNE': ['Rome', 'Milan'],
        'CODREG': ['12', '03'],
        'CODPRO': ['058', '015'],
        'PROVINCIA': ['Roma', 'Milano'],
        'SIGLA': ['RM', 'MI'],
        'REGIONE': ['Lazio', 'Lombardia'],
        'CODCOM': ['058091', '015146'],
        'SEZIONE': ['001', '002'],
        'POP_TOT': [100, 200]
    })

    geodata.to_file(gpkg_path, driver='GPKG', layer='census1991')
    gpd.GeoDataFrame(data).to_file(gpkg_path, driver='GPKG', layer='data1991')

    with pytest.raises(KeyError, match="Join column.*not found"):
        finalize_census_data(
            census_data_path=tmp_path,
            years=[1991],
            output_data_folder=tmp_path,
            delete_preprocessed_data=False,
        )


def test_finalize_census_data_removes_index_column(mock_census_gpkg, tmp_path):
    """Test that 'index' column is removed if present."""
    census_path, gpkg_file = mock_census_gpkg
    output_folder = tmp_path / "output"
    output_folder.mkdir()

    # Add an 'index' column to the geodata
    geodata = gpd.read_file(gpkg_file, layer='census1991')
    geodata['index'] = [0, 1, 2]
    geodata.to_file(gpkg_file, driver='GPKG', layer='census1991')

    finalize_census_data(
        census_data_path=census_path,
        years=[1991],
        output_data_folder=output_folder,
        delete_preprocessed_data=False,
    )

    # Verify index column was removed
    result = gpd.read_file(output_folder / "census_data.gpkg", layer='census1991')
    assert 'index' not in result.columns


@pytest.mark.skipif(
    not main_folder.joinpath("census.gpkg").exists(),
    reason="External data file not available"
)
def test_finalize_census_data_with_real_data(tmp_path: Path):
    """Integration test with real data (skipped if not available)."""
    print("test_finalize_census_data_with_real_data")
    finalize_census_data(
        census_data_path=main_folder,
        years=[2021],
        output_data_folder=tmp_path,
        delete_preprocessed_data=False,
    )
