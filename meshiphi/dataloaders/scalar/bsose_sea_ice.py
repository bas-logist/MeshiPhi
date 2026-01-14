from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class BSOSESeaIceDataLoader(ScalarDataLoader):  # type: ignore[misc]
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from a BSOSE Sea Ice NetCDF file.
        Renames coordinates to 'lat' and 'long', and renames variable to
        'SIC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                BSOSE Sea Ice dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'SIC'

        Raises:
            ValueError:
                If units specified in config,
                and value not 'fraction' or 'percentage'
        """
        # Open Dataset
        if self.files is None:
            raise ValueError("files parameter is required for BSOSESeaIceDataLoader")
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files)
        # Change column names
        data = data.rename({"SIarea": "SIC", "YC": "lat", "XC": "long"})

        # Change domain of dataset from [0:360) to [-180:180)
        data = data.assign_coords(long=((data.long + 180) % 360) - 180)
        # Sort the 'long' axis so that sel() will work
        data = data.sortby("long")
        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)

        if hasattr(self, "units"):
            logging.info(f"- Changing units of data to {self.units}")
            # Convert to percentage form if requested in params
            if self.units == "percentage":
                data = data.assign(SIC=data["SIC"] * 100)
            elif self.units == "fraction":
                pass  # BSOSE data already in fraction form
            else:
                raise ValueError(
                    "Parameter 'units' not understood."
                    "Expected 'percentage' or 'fraction',"
                    f"but received {self.units}"
                )
        else:
            # Convert to percentage form by default (as expected by the vessel performance models)
            return data.assign(SIC=data["SIC"] * 100)

        return data
