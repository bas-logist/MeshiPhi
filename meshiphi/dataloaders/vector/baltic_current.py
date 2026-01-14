from __future__ import annotations

from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class BalticCurrentDataLoader(VectorDataLoader):  # type: ignore[misc]
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in current data from a copernicus baltic sea physics reanalysis NetCDF file.
        Renames coordinates to 'lat' and 'long', and renames variable to
        'uC, vC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                Baltic currents dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'uC', 'vC'
        """
        # Open Dataset
        if self.files is None:
            raise ValueError("files parameter is required for BalticCurrentDataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)

        # Reduce and drop unused depth dimension
        data = data.isel(depth=0)
        data = data.reset_coords(names="depth", drop=True)
        # Change column names
        data = data.rename({"latitude": "lat", "longitude": "long", "uo": "uC", "vo": "vC"})

        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)

        # Reduce along time dimension
        return data.mean(dim="time")
