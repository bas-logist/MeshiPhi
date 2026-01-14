from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary

logger = logging.getLogger(__name__)


class MODISDataLoader(ScalarDataLoader):
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from a MODIS NetCDF file.
        Renames variable to 'SIC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                MODIS dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        """
        # Open Dataset
        if self.files is None:
            raise ValueError("files parameter is required for MODISDataLoader")
        logger.info(
            f"- Opening file {self.files[0] if len(self.files) == 1 else f'{len(self.files)} files'}"
        )
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Change column name
        data = data.rename({"iceArea": "SIC"})

        # Set areas obscured by cloud to NaN values
        data = data.where(data.cloud != 1, drop=True)
        # Trim to initial datapoints
        return self.trim_datapoints(bounds, data=data)
