from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

import xarray as xr
import numpy as np

from datetime import datetime
from os.path import basename


class ERA5WindDirDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
        """
        Reads in data from an ERA5 NetCDF file.
        Renames coordinates to 'lat' and 'long'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                ERA5 wave dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'wind_dir'
        """
        time_range = [
            datetime.strptime(time_str, "%Y-%m-%d")
            for time_str in bounds.get_time_range()
        ]
        # Reduce files to those within date range
        self.files = [
            file
            for file in self.files
            if time_range[0]
            <= datetime.strptime(basename(file)[10:-3], "%Y-%m-%d")
            <= time_range[1]
        ]
        # Open Dataset
        if len(self.files) == 1:
            data = xr.open_dataset(self.files[0])
        else:
            data = xr.open_mfdataset(self.files).compute()
        # Change column names
        data = data.rename({"latitude": "lat", "longitude": "long"})
        # Change domain of dataset from [0:360) to [-180:180)
        data = data.assign_coords(long=((data.long + 180) % 360) - 180)
        # Sort the 'long' axis so that sel() will work
        data = data.sortby("long")

        # Calculate direction in degrees between 0 and 360 from vector components
        data["wind_dir"] = np.mod(
            180 + (180 / np.pi) * np.arctan2(data["v10"], data["u10"]), 360
        )

        # Limit to just rnn variables
        data = data["wind_dir"].to_dataset()
        # Reverse order of lat as array goes from max to min
        data = data.reindex(lat=data.lat[::-1])
        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)

        return data
