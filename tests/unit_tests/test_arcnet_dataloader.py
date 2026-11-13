import pytest
import geopandas as gpd
from shapely.geometry import Polygon

from meshiphi.dataloaders.lut.lut_shapefile_arcnet import LutShapefileArcNet


def test_arcnet_normalizes_antimeridian_geometry():
    poly = Polygon([(170, 60), (190, 60), (190, 70), (170, 70), (170, 60)])
    gdf = gpd.GeoDataFrame({"geometry": [poly]}, crs="EPSG:4326")

    normalized = LutShapefileArcNet.normalize_geometries(gdf)

    assert not normalized.empty
    longitudes = [coord for geom in normalized.geometry for coord in geom.exterior.coords.xy[0]]
    assert all(-180 <= lon <= 180 for lon in longitudes)
    assert len(normalized.geometry) >= 2

    # The geometry should be split into valid pieces around the dateline.
    assert all(geom.is_valid for geom in normalized.geometry)


def test_arcnet_rejects_world_spanning_polygon_that_cannot_be_split():
    poly = Polygon([(-180, 70), (-180, 72), (179.9, 72), (179.9, 70), (-180, 70)])
    gdf = gpd.GeoDataFrame({"geometry": [poly]}, crs="EPSG:4326")

    normalized = LutShapefileArcNet.normalize_geometries(gdf)

    assert normalized.empty
    assert all((geom.bounds[2] - geom.bounds[0]) <= 180 for geom in normalized.geometry)


def _build_mesh_with_small_polygon(tmp_path, fill_types):
    from shapely.geometry import box

    from meshiphi.mesh_generation.mesh_builder import MeshBuilder

    shp = tmp_path / "pac.shp"
    gpd.GeoDataFrame({"PAC_ID": [1]}, geometry=[box(5, 62, 7, 63)], crs="EPSG:4326").to_file(shp)
    params = {
        "data_name": "protected_area_speed_limit",
        "value": 15.0,
        "aggregate_type": "MIN",
        "files": [str(shp)],
        "splitting_conditions": [
            {"protected_area_speed_limit": {"boundary": True, "split_lock": False}}
        ],
    }
    if fill_types is not None:
        params["value_fill_types"] = fill_types
    config = {
        "region": {
            "lat_min": 60,
            "lat_max": 70,
            "long_min": 0,
            "long_max": 20,
            "start_time": "2026-08-31",
            "end_time": "2026-09-03",
            "cell_width": 10,
            "cell_height": 5,
        },
        "data_sources": [{"loader": "lut_shapefile_arcnet", "params": params}],
        "splitting": {"split_depth": 5, "minimum_datapoints": 5},
    }
    return MeshBuilder(config).build_environmental_mesh().to_json()["cellboxes"]


def test_arcnet_default_fill_is_not_parent():
    loader = object.__new__(LutShapefileArcNet)
    assert loader.add_default_params({})["value_fill_types"] == "Nan"
    # An explicit "parent" would spread the value to non-overlapping sub-cells
    assert loader.add_default_params({"value_fill_types": "parent"})["value_fill_types"] == "Nan"
    # Other fills are left to the user
    assert loader.add_default_params({"value_fill_types": 0.0})["value_fill_types"] == 0.0


@pytest.mark.parametrize("fill_types", [None, "parent", "Nan"])
def test_arcnet_value_only_in_cells_touching_polygon(tmp_path, fill_types):
    from shapely.geometry import box

    cells = _build_mesh_with_small_polygon(tmp_path, fill_types)
    polygon = box(5, 62, 7, 63)

    flagged = [c for c in cells if c["protected_area_speed_limit"] is not None]
    assert flagged, "cells overlapping the polygon should carry the limit"
    for c in cells:
        cell = box(c["cx"] - c["dcx"], c["cy"] - c["dcy"], c["cx"] + c["dcx"], c["cy"] + c["dcy"])
        if cell.intersects(polygon):
            assert c["protected_area_speed_limit"] == 15.0
        else:
            # a real null, not a fill copied from a parent cell and not the string "Nan"
            assert c["protected_area_speed_limit"] is None
