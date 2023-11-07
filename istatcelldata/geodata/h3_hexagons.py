import h3
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from shapely import Polygon

from istatcelldata.geodata.manage_geodata import polygon_bbox


def get_h3_hexagons(
        vector: GeoDataFrame,
        hex_lvl: int,
        geo_json_conformant: bool = True
) -> GeoDataFrame:
    """Get H3 hexagon from geometry and selected level.

    Args:
        vector: GeoDataFrame
        hex_lvl: int
        geo_json_conformant: bool

    Returns:
        GeoDataFrame
    """
    # Because H3 library use EPSG:4326 geometry must be
    # reprojected if his crs isn't the same.
    h3_epsg = 4326
    if vector.crs != h3_epsg:
        main_geometry = vector.to_crs(h3_epsg)
    else:
        main_geometry = vector

    # Get boundary
    coordinates = main_geometry.total_bounds

    # Make boundary GeoJSON
    bbox_polygon = polygon_bbox(coordinates)
    bbox_df = pd.DataFrame([bbox_polygon], columns=['geometry'])
    bbox_gdf = gpd.GeoDataFrame(bbox_df, geometry='geometry', crs=h3_epsg).buffer(0.15)
    bbox_geojson = bbox_gdf.geometry[0].__geo_interface__

    # Get hexagons' id
    hexagons_id = h3.polyfill(bbox_geojson, res=hex_lvl, geo_json_conformant=geo_json_conformant)

    # Join hexagon's id to his polygon
    object_list = []
    for hexagon_id in hexagons_id:
        hexagon = Polygon(h3.h3_to_geo_boundary(hexagon_id, geo_json=True))
        object_list.append([hexagon_id, hexagon])

    hexagons_df = pd.DataFrame(data=object_list, columns=['h3_index', 'geometry'])
    hexagons_gdf = gpd.GeoDataFrame(hexagons_df, crs=h3_epsg)

    if hexagons_gdf.crs != vector.crs:
        hexagons_gdf = hexagons_gdf.to_crs(vector.crs)

    return hexagons_gdf
