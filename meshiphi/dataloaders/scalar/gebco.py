from __future__ import annotations

from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class GEBCODataLoader(ScalarDataLoader):
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from GEBCO NetCDF files. Renames coordinates to
        'lat' and 'long'.

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                GEBCO dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'elevation'
        """
        # Import data from files defined in config
        if self.files is None:
            raise ValueError("files parameter is required for GEBCODataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Rename columns to standard format
        data = data.rename({"lon": "long"})

        # Only use the elevation column
        data = data["elevation"].to_dataset()

        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=data)
