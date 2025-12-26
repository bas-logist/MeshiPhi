from meshiphi.dataloaders.lut.abstract_lut import LutDataLoader
from meshiphi.mesh_generation.boundary import Boundary

import pandas as pd
from shapely.ops import unary_union
from shapely import wkt
import numpy as np


class LutCSV(LutDataLoader):
    def import_data(self, bounds):
        """
        Import a list of .csv files, assign regions a value specified in
        config params, regions outside this are numpy nan values.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            exclusion_df (pd.DataFrame):
                Dataframe of polygons with value specified in config.
                DataFrame has columns 'geometry' and
                data_name (read from CSV by default)
        """
        # Read in all files and create dataframe from them
        df_list = [pd.read_csv(file, index_col=False) for file in self.files]
        csv_df = pd.concat(df_list, ignore_index=True)

        # Make sure .csv is well formed
        if "geometry" not in csv_df.columns:
            raise KeyError("'geometry' column required in CSV file")
        if not csv_df.geometry.str.contains("POLYGON").all():
            raise ValueError("Only 'Polygon' or 'MultiPolygon' geometry allowed")
        if len(csv_df.columns) != 2:
            raise ValueError(
                "Dataloader only accepts .csv with 2 columns, 'geometry' and {data_name}"
            )

        # Set data name to column in CSV
        self.data_name = list(set(csv_df.columns.values) - set(["geometry"]))[0]
        # Convert strings to shapely geometries
        csv_df["geometry"] = csv_df["geometry"].apply(wkt.loads)
        # Create boundary denoting the world
        world_polygon = Boundary([-90, 90], [-180, 180]).to_polygon()
        # Subtract out all regions with defined values
        defined_polygon = unary_union(csv_df.geometry)
        undefined_polygon = world_polygon - defined_polygon
        # Set remainder to have value np.nan
        csv_df.loc[len(csv_df.index)] = [undefined_polygon, np.nan]
        # Limit to boundary
        csv_df = self.trim_datapoints(bounds, data=csv_df)

        return csv_df
