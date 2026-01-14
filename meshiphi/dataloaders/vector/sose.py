from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd  # noqa: TC002
import xarray as xr

from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class SOSEDataLoader(VectorDataLoader):
    def import_data(self, bounds: Boundary) -> pd.DataFrame:
        """
        Reads in data from a SOSE Currents NetCDF file.
        Renames coordinates to 'lat' and 'long', and renames variable to
        'uC, vC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                SOSE currents dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'uC', 'vC'
        """

        # Open dataset and cast to pandas df
        if self.files is None:
            raise ValueError("files parameter is required for SOSEDataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Cast to dataframe to modify lon coordinate
        df = data.to_dataframe().reset_index()

        # Change long coordinate to be in [-180,180) domain rather than [0,360)
        df["long"] = df["lon"].apply(lambda x: x - 360 if x > 180 else x)
        # Extract relevant columns
        df = df[["lat", "long", "uC", "vC"]]
        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=df)
