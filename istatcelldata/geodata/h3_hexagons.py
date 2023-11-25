import logging
from pathlib import Path
from typing import Union

import h3
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely import Polygon

from istatcelldata.config import logger, console_handler
from istatcelldata.geodata.manage_geodata import polygon_bbox

logger.addHandler(console_handler)


def get_h3_hexagons(
        vector: GeoDataFrame,
        hex_lvl: int,
        geo_json_conformant: bool = True,
        output_path: Path = None,
) -> Union[GeoDataFrame, Path]:
    """Get H3 hexagon from geometry and selected level.

    Args:
        vector: GeoDataFrame
        hex_lvl: int
        geo_json_conformant: bool
        output_path: Path

    Returns:
        Union[GeoDataFrame, Path]
    """
    # Because H3 library use EPSG:4326 geometry must be
    # reprojected if his crs isn't the same.
    h3_epsg = 4326
    if vector.crs != h3_epsg:
        logging.info('Reproject data')
        main_geometry = vector.to_crs(h3_epsg)
    else:
        main_geometry = vector

    # Get boundary
    logging.info('Get boundary')
    coordinates = main_geometry.total_bounds

    # Make boundary GeoJSON
    logging.info('Make boundary GeoJSON')
    bbox_polygon = polygon_bbox(coordinates)
    bbox_df = pd.DataFrame([bbox_polygon], columns=['geometry'])
    bbox_gdf = gpd.GeoDataFrame(bbox_df, geometry='geometry', crs=h3_epsg)  # .buffer(0.005)
    bbox_geojson = bbox_gdf.geometry[0].__geo_interface__

    # Get hexagons' id
    logging.info('Get hexagons\' id')
    hexagons_id = h3.polyfill(bbox_geojson, res=hex_lvl, geo_json_conformant=geo_json_conformant)

    # Join hexagon's id to his polygon
    logging.info('Join hexagon\'s id to his polygon')
    object_list = []
    for hexagon_id in hexagons_id:
        hexagon = Polygon(h3.h3_to_geo_boundary(hexagon_id, geo_json=True))
        object_list.append([hexagon_id, hexagon])

    hexagons_df = pd.DataFrame(data=object_list, columns=['h3_index', 'geometry'])
    hexagons_gdf = gpd.GeoDataFrame(hexagons_df, crs=h3_epsg)

    if hexagons_gdf.crs != vector.crs:
        logging.info('Reproject data')
        hexagons_gdf = hexagons_gdf.to_crs(vector.crs)

    if output_path is None:
        return hexagons_gdf

    else:

        output_data = output_path.joinpath('h3_hexagons.gpkg')
        layer_name = f'lvl_{hex_lvl}'
        logging.info(f'Save data to {output_data}')
        hexagons_gdf.to_file(output_data, driver='GPKG', layer=layer_name)


def select_hexagons(
        aoi: GeoDataFrame,
        hex_lvl: int,
        geo_json_conformant: bool = True,
        output_path: Path = None,
) -> Union[GeoDataFrame, Path]:
    """Select hexagons based on Area Of Interest.

    Args:
        aoi: GeoDataFrame
        hex_lvl: int
        geo_json_conformant: bool
        output_path: Path

    Returns:
        Union[GeoDataFrame, Path]
    """
    # Create hexagons
    logging.info('Create hexagons')
    hexagons = get_h3_hexagons(
        vector=aoi,
        hex_lvl=hex_lvl,
        geo_json_conformant=geo_json_conformant,
    )

    # Select hexagons
    logging.info('Select hexagons')
    selected_hexagons = hexagons.sjoin(aoi, how='left')
    selected_hexagons = selected_hexagons[selected_hexagons['index_right'].notna()][['h3_index', 'geometry']]
    selected_hexagons['hexagon_area'] = round(selected_hexagons.geometry.area, 0)

    if output_path is None:
        return selected_hexagons

    else:

        output_data = output_path.joinpath('h3_hexagons.gpkg')
        layer_name = f'selected_hexagons_lvl_{hex_lvl}'
        logging.info(f'Save data to {output_data}')
        selected_hexagons.to_file(output_data, driver='GPKG', layer=layer_name)
