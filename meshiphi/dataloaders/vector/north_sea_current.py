from __future__ import annotations

from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class NorthSeaCurrentDataLoader(VectorDataLoader):
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from a BSOSE Depth NetCDF file.
        Renames coordinates to 'lat', 'long', 'time', and renames variable to
        'uC, vC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                North Sea currents dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'uC', 'vC'
        """
        # Open Dataset
        if self.files is None:
            raise ValueError("files parameter is required for NorthSeaCurrentDataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Change column names
        data = data.rename({"lon": "long", "times": "time", "U": "uC", "V": "vC"})
        # Limit to just these coords and variables
        data = data[["uC", "vC"]]

        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=data)
