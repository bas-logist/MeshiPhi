from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union

from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader
from meshiphi.mesh_generation.boundary import Boundary


class LutShapefile(LutDataLoader):  # type: ignore[misc]
    def add_default_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Set default values for LUT dataloader. Only unique addition over
        the regular abstracted add_default_params is the data_name

        Args:
            params (dict):
                Dictionary containing attributes that are required for the
                LUT being loaded.

        Returns:
            (dict):
                Dictionary of attributes the dataloader will require,
                completed with default values if not provided in config.
        """
        # Add default scalar params
        params = super().add_default_params(params)

        # Name of data being read in from GeoJSONs
        if "data_name" not in params:
            params["data_name"] = "dummy_data"

        return params

    def import_data(self, bounds: Boundary) -> pd.DataFrame:
        """
        Import a list of .shp files, assign regions a value specified in
        config params, regions outside this are numpy nan values.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            exclusion_df (pd.DataFrame):
                Dataframe of polygons with value specified in config.
                DataFrame has columns 'geometry' and
                data_name ('dummy_data' by default)
        """
        # Read in all files specified and extract geometry of shapes
        if self.files is None:
            raise ValueError("files parameter is required for LutShapefile")
        gdf_list = [gpd.read_file(file) for file in self.files]
        shape_df = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))
        # Give shapes a value defined in config
        shape_df[self.data_name] = self.value
        shape_df = pd.DataFrame(shape_df[["geometry", self.data_name]])

        # Create boundary denoting the world
        world_polygon = Boundary([-90, 90], [-180, 180]).to_polygon()
        # Subtract out all regions with defined values
        defined_polygon = unary_union(shape_df.geometry)
        undefined_polygon = world_polygon - defined_polygon
        # Set remainder to have value np.nan (or opposing bool value)
        alt_val: Any
        if self.value is True:
            alt_val = False
        elif self.value is False:
            alt_val = True
        else:
            alt_val = np.nan
        shape_df.loc[len(shape_df.index)] = [undefined_polygon, alt_val]
        # Limit to boundary
        return self.trim_datapoints(bounds, data=shape_df)
