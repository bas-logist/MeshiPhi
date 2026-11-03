from __future__ import annotations

from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class BalticSeaIceDataLoader(ScalarDataLoader):
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from a Baltic Sea Ice NetCDF file.
        Renames coordinates to 'lat' and 'long', and renames variable to 'SIC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                Baltic Sea Ice dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        """
        # Open Dataset
        if self.files is None:
            raise ValueError("files parameter is required for BalticSeaIceDataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Change column names
        data = data.rename({"ice_concentration": "SIC", "lon": "long"})
        # Limit to just SIC data
        data = data["SIC"].to_dataset()
        # Reverse order of lat as array goes from max to min
        data = data.reindex(lat=data.lat[::-1])
        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=data)
