from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader


import xarray as xr

from datetime import datetime
from os.path import basename


class ERA5WindDataLoader(VectorDataLoader):
    def import_data(self, bounds):
        """
        Reads in wind data from a ERA5 NetCDF file.
        Renames coordinates to 'lat' and 'long'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                ERA5 wind dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variables 'u10', 'v10'
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

        # Set min time to start of month to ensure we include data as we only have a
        # monthly cadence. Assuming time is in str format
        time_min = datetime.strptime(bounds.get_time_min(), "%Y-%m-%d")
        time_min = datetime.strftime(time_min, "%Y-%m-01")

        # Reverse order of lat as array goes from max to min
        data = data.reindex(lat=data.lat[::-1])

        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)

        return data
