import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union

from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader
from meshiphi.mesh_generation.boundary import Boundary


class ScotlandNCMPA(LutDataLoader):
    def import_data(self, bounds):
        """
        Creates a simulated dataset of sea ice thickness based on
        scientific literature.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            exclusion_df (pd.DataFrame):
                Dataframe of exclusion zones around scotland.
                DataFrame has coordinates 'date', 'shape',
                and variable 'thickness'
        """
        # Read in all files specified and extract geometry of exclusion zones
        if self.files is None:
            raise ValueError("files parameter is required for ScotlandNCMPA")
        gdf_list = [gpd.read_file(file) for file in self.files]
        exclusion_df = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))
        # Denote all geometries as exclusion zones
        exclusion_df["exclusion_zone"] = True
        exclusion_df = pd.DataFrame(exclusion_df[["geometry", "exclusion_zone"]])

        # Create boundary denoting the world
        world_polygon = Boundary([-90, 90], [-180, 180]).to_polygon()
        # Subtract out all exclusion zones
        exclusion_polygon = unary_union(exclusion_df.geometry)
        inclusion_polygon = world_polygon - exclusion_polygon
        # Add line
        exclusion_df.loc[len(exclusion_df.index)] = [inclusion_polygon, False]
        # Limit to boundary
        return self.trim_datapoints(bounds, data=exclusion_df)
