import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid
from tqdm import tqdm

from istatcelldata.config import GEOMETRY_COLUMN_NAME, GLOBAL_ENCODING, YEAR_GEODATA_NAME
from istatcelldata.logger_config import configure_logging
from istatcelldata.utils import check_encoding

# Configure logging at the start of the script
configure_logging()
# Define the logger as a global variable
logger = logging.getLogger(__name__)


def read_administrative_boundaries(
    file_path: Path,
    target_columns: list,
    index_column: str,
    column_remapping: dict | None = None,
    output_folder: Path | None = None,
    layer_name: str | None = None,
) -> pd.DataFrame | Path:
    """Read administrative boundaries and return a DataFrame or GeoPackage.

    This function reads an administrative boundary file (typically a shapefile),
    selects a subset of columns, and sets a column as the index. Depending on
    the provided parameters, it can:

    - Return a DataFrame without geometry, sorted and indexed; or
    - Save the data as a layer in a GeoPackage, preserving the geometry.

    The encoding is derived from the .dbf file associated with the shapefile to
    avoid issues with accented characters or special symbols.

    Args:
        file_path: Path to the vector file (e.g., shapefile) containing administrative
            boundaries.
        target_columns: List of columns to select from the source dataset. The
            geometry column is added automatically.
        index_column: Name of the column to use as the DataFrame index (e.g.,
            ISTAT code).
        column_remapping: Optional dictionary to rename columns (e.g.,
            `{"DEN_REG": "REGIONE"}`). If None, original names are kept.
        output_folder: Optional output folder where the GeoPackage will be saved.
            If None, the function returns a DataFrame (without geometry) instead
            of writing to disk.
        layer_name: Optional name of the layer to use within the GeoPackage. Must
            be specified if `output_folder` is provided, to properly distinguish
            layers.

    Returns:
        Either an indexed and sorted DataFrame without geometry column if
        `output_folder` is None, or the path to the created GeoPackage if
        `output_folder` is provided.

    Note:
        The geometry column is automatically added to `target_columns` via the
        `GEOMETRY_COLUMN_NAME` constant. The GeoPackage is saved with a name
        based on the `YEAR_GEODATA_NAME` constant and contains the layer
        specified by `layer_name`.
    """
    logging.info(f"Reading administrative boundaries from {file_path}")

    # Determine encoding of the associated .dbf file
    data_db = file_path.parent.joinpath(f"{file_path.stem}.dbf")
    encoding = check_encoding(data=data_db)
    logging.info(f"Detected encoding: {encoding}")

    # Read shapefile with appropriate encoding
    data = gpd.read_file(filename=file_path, encoding=encoding)
    logging.info(f"File {file_path} read successfully")

    # Select target columns
    target_columns.extend([GEOMETRY_COLUMN_NAME])
    data_target = data[target_columns]
    logging.info(f"Selected columns: {target_columns}")

    # Rename columns if specified
    if column_remapping is not None:
        data_target.rename(columns=column_remapping, inplace=True)
        logging.info(f"Columns renamed according to mapping: {column_remapping}")

    # Set index column and sort data
    data_target.set_index(index_column, inplace=True)
    logging.info(f"Index column set: {index_column}")
    data_target.sort_index(inplace=True)
    logging.info(f"Data sorted by column {index_column}")

    if output_folder is None:
        data_target.drop(columns=[GEOMETRY_COLUMN_NAME], inplace=True)
        data_target = pd.DataFrame(data_target)

        return data_target

    else:
        # Handle with geometry
        gdf = gpd.GeoDataFrame(data=data_target, crs=data.crs)

        geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
        gdf.to_file(
            filename=str(geopackage_path), driver="GPKG", layer=layer_name, encoding=GLOBAL_ENCODING
        )
        logging.info(f"GeoPackage saved to {geopackage_path} with layer {layer_name}")
        return geopackage_path


def read_census(
    shp_folder: Path,
    target_columns: list,
    tipo_loc_mapping: dict,
    column_remapping: dict | None = None,
    output_folder: Path | None = None,
    layer_name: str | None = None,
) -> gpd.GeoDataFrame | Path:
    """Read census data from shapefiles and return a GeoDataFrame or GeoPackage.

    This function recursively searches for all shapefiles in a folder, reads their
    data, selects a subset of columns, corrects invalid geometries, adds the
    locality type description (derived from `tipo_loc_mapping`), and builds a
    unified GeoDataFrame with all census sections.

    Depending on the parameters, it can:

    - Return the resulting GeoDataFrame directly; or
    - Save the data as a layer in a GeoPackage (`YEAR_GEODATA_NAME.gpkg`) and
      return the path to the created file.

    Args:
        shp_folder: Path to the folder containing census shapefiles (recursive
            reading via `rglob("*.shp")`).
        target_columns: List of columns to select from each shapefile (must include
            or be compatible with the geometry column).
        tipo_loc_mapping: Mapping of locality codes for the `TIPO_LOC` field
            (e.g., `{1: "Centro abitato", 2: "Nucleo", ...}`), used to create
            the descriptive column `DEN_LOC`.
        column_remapping: Optional dictionary to rename selected columns
            (e.g., `{"PRO_COM": "PRO_COMUNE"}`). If None, original names are kept.
        output_folder: Optional folder where the resulting GeoPackage will be saved.
            If None, the function does not write to disk and returns the
            GeoDataFrame directly.
        layer_name: Optional name of the layer to use within the GeoPackage.
            Must be specified if `output_folder` is provided.

    Returns:
        Either a `GeoDataFrame` with census data and corrected geometries if
        `output_folder` is None, or the path to the created GeoPackage if
        `output_folder` is provided.

    Raises:
        ValueError: If no shapefile is found in the specified folder.

    Note:
        Geometries are validated with `make_valid()` to reduce issues caused
        by invalid polygons. An `area_mq` column containing the area in square
        meters is calculated. The GeoDataFrame index is set to the first column
        in `df_columns` (typically the census section code).
    """
    logging.info(f"Reading shapefile from folder {shp_folder}")

    # List of shapefile files in folder
    shp_list = list(shp_folder.rglob("*.shp"))
    if not shp_list:
        raise ValueError(f"No shapefile found in folder {shp_folder}")

    census_cells = []
    columns_list = []
    crs_list = []

    # Iterate through found shapefiles
    for shp in shp_list:
        data_db = shp.parent.joinpath(f"{shp.stem}.dbf")
        encoding = check_encoding(data=data_db)  # Determine encoding of associated .dbf file
        logging.info(f"Reading shapefile {shp} with encoding {encoding}")

        # Read shapefile
        data = gpd.read_file(filename=shp, encoding=encoding)
        crs_list.append(data.crs)  # Save coordinate reference system (CRS)
        census_data = data[target_columns]
        logging.info(f"Selected columns: {target_columns}")

        # Rename columns if specified
        if column_remapping is not None:
            census_data.rename(columns=column_remapping, inplace=True)
            logging.info(f"Columns renamed according to mapping: {column_remapping}")

        columns_list.append(list(census_data.columns))

        # Iterate through DataFrame rows to build census cells
        for index, row in tqdm(census_data.iterrows(), total=census_data.shape[0]):
            census_geometry = row[GEOMETRY_COLUMN_NAME]

            # Check if geometry is present
            if census_geometry is not None:
                validated_geometry = make_valid(
                    census_geometry
                )  # Correct geometry if necessary
                row[GEOMETRY_COLUMN_NAME] = validated_geometry
                census_row = row.to_list()
                tipo_loc = tipo_loc_mapping.get(
                    row["TIPO_LOC"], None
                )  # Map locality code
                census_row.extend([tipo_loc])
                census_cells.append(census_row)
            else:
                logging.warning(
                    f"For section {row[0]} the geometry is `None` or irreparably corrupted."
                )
                pass

    df_columns = columns_list[0]  # Retrieve column names
    df_columns.extend(["DEN_LOC"])  # Add 'DEN_LOC' as column
    logging.info(f"Final columns: {df_columns}")

    # Create DataFrame and GeoDataFrame
    df = pd.DataFrame(data=census_cells, columns=df_columns)
    gdf = gpd.GeoDataFrame(df, crs=crs_list[0])
    gdf["area_mq"] = round(gdf["geometry"].area, 2)
    gdf.set_index(df_columns[0], inplace=True)
    logging.info(f"GeoDataFrame created with CRS: {crs_list[0]}")

    # If output path is provided, save GeoDataFrame to GeoPackage
    if output_folder is not None:
        geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
        gdf.to_file(
            filename=str(geopackage_path), driver="GPKG", encoding=GLOBAL_ENCODING, layer=layer_name
        )
        logging.info(f"GeoPackage saved to {geopackage_path}")
        return geopackage_path

    # If no output path is provided, return GeoDataFrame
    else:
        return gdf


def preprocess_geodata(
    census_shp_folder: Path,
    census_target_columns: list,
    census_tipo_loc_mapping: dict,
    output_folder: Path,
    census_layer_name: str,
    census_column_remapping: dict | None = None,
    regions_file_path: Path | None = None,
    regions_target_columns: list | None = None,
    regions_index_column: str | None = None,
    regions_column_remapping: dict | None = None,
    provinces_file_path: Path | None = None,
    provinces_target_columns: list | None = None,
    provinces_index_column: str | None = None,
    provinces_column_remapping: dict | None = None,
    municipalities_file_path: Path | None = None,
    municipalities_target_columns: list | None = None,
    municipalities_index_column: str | None = None,
    municipalities_column_remapping: dict | None = None,
    municipalities_code: list[int] = [],
) -> Path:
    """Preprocess census geodata and administrative boundaries and save to GeoPackage.

    This function executes the complete workflow for preparing geographic data
    for a census year, combining:

    1. Reading and normalizing administrative boundaries (regions, provinces, municipalities).
    2. Optionally correcting missing fields (e.g., `COD_PROV` for 2021).
    3. Reading and preparing census data (sections) from shapefiles.
    4. Joining sections with municipalities, provinces, and regions.
    5. Optionally filtering for a subset of municipalities (`municipalities_code`).
    6. Saving the final result to a GeoPackage.

    Args:
        census_shp_folder: Folder containing census shapefiles (sections).
        census_target_columns: Columns to select from census data (sections).
        census_tipo_loc_mapping: Mapping for the `TIPO_LOC` field to derive the
            locality type description.
        output_folder: Folder where the resulting GeoPackage will be saved.
        census_layer_name: Name of the census layer (e.g., `census2011`), also
            used to derive the year from the suffix.
        census_column_remapping: Optional mapping to rename census data columns.
        regions_file_path: Optional path to the regional boundaries vector file.
        regions_target_columns: Optional columns to select from regional data.
        regions_index_column: Optional column to use as index for regional data.
        regions_column_remapping: Optional mapping to rename regional data columns.
        provinces_file_path: Optional path to the provincial boundaries vector file.
        provinces_target_columns: Optional columns to select from provincial data.
        provinces_index_column: Optional column to use as index for provincial data.
        provinces_column_remapping: Optional mapping to rename provincial data columns.
        municipalities_file_path: Optional path to the municipal boundaries vector file.
        municipalities_target_columns: Optional columns to select from municipal data.
        municipalities_index_column: Optional column to use as index for municipal data.
        municipalities_column_remapping: Optional mapping to rename municipal data columns.
        municipalities_code: Optional list of ISTAT municipality codes (`PRO_COM` field)
            to extract. If empty, all municipalities are kept.

    Returns:
        Path to the generated GeoPackage containing the census layer enriched
        with administrative information.

    Note:
        The census year is derived from the layer name `census_layer_name[6:]`
        (e.g., `census2011` → `2011`). For 2021, the `COD_PROV` column is manually
        reconstructed from `PRO_COM_T` (see repository issue #47). The GeoPackage
        is saved as `{YEAR_GEODATA_NAME}.gpkg` and the layer as
        `{YEAR_GEODATA_NAME}{census_year}`.
    """
    census_year = census_layer_name[6:]
    logging.info(f"Detected census year: {census_year}")

    # Read and save regional boundaries
    logging.info("Starting processing of regional boundaries")
    region = read_administrative_boundaries(
        file_path=regions_file_path,
        target_columns=regions_target_columns,
        index_column=regions_index_column,
        column_remapping=regions_column_remapping,
    )

    # Read and save provincial boundaries
    logging.info("Starting processing of provincial boundaries")
    province = read_administrative_boundaries(
        file_path=provinces_file_path,
        target_columns=provinces_target_columns,
        index_column=provinces_index_column,
        column_remapping=provinces_column_remapping,
    )

    # Read and save municipal boundaries
    logging.info("Starting processing of municipal boundaries")
    municipality = read_administrative_boundaries(
        file_path=municipalities_file_path,
        target_columns=municipalities_target_columns,
        index_column=municipalities_index_column,
        column_remapping=municipalities_column_remapping,
    )
    municipality.reset_index(inplace=True)
    # Since 2021 municipal boundaries don't have 'COD_PROV' column, add it manually.
    # TODO https://github.com/MaxDragonheart/istatcelldata/issues/47
    logging.info(
        "Since 2021 municipal boundaries don't have 'COD_PROV' column, adding it manually. https://github.com/MaxDragonheart/istatcelldata/issues/47"
    )
    if census_year == "2021":
        municipality["COD_PROV"] = municipality["PRO_COM_T"].str[:3]
        municipality["COD_PROV"] = municipality["COD_PROV"].astype(int)
        municipality.drop(columns=["PRO_COM_T"], inplace=True)

    # Add provincial details to municipalities
    mun_prov = pd.merge(left=municipality, right=province, how="left", on="COD_PROV")

    # Add regional details to municipalities
    mun_reg = pd.merge(left=mun_prov, right=region, how="left", on="COD_REG")

    logging.info(
        f"Starting preprocessing of census data from folder {census_shp_folder}"
    )
    # Read and save census data
    census_geodata = read_census(
        shp_folder=census_shp_folder,
        target_columns=census_target_columns,
        tipo_loc_mapping=census_tipo_loc_mapping,
        column_remapping=census_column_remapping,
    )
    if len(municipalities_code) > 0:
        logging.info(f"Municipalities to extract: {municipalities_code}")
        mun_reg = mun_reg[mun_reg["PRO_COM"].isin(municipalities_code)]
        census_geodata = census_geodata[census_geodata["PRO_COM"].isin(municipalities_code)]
    census_geodata_full = pd.merge(left=census_geodata, right=mun_reg, how="left", on="PRO_COM")

    gdf = gpd.GeoDataFrame(
        data=census_geodata_full, geometry=GEOMETRY_COLUMN_NAME, crs=census_geodata.crs
    )
    geopackage_path = output_folder.joinpath(f"{YEAR_GEODATA_NAME}.gpkg")
    gdf.to_file(
        filename=str(geopackage_path),
        driver="GPKG",
        encoding=GLOBAL_ENCODING,
        layer=f"{YEAR_GEODATA_NAME}{census_year}",
    )
    logging.info(f"Saving census GeoPackage to {geopackage_path}")
    return geopackage_path
