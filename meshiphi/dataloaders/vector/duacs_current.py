from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader


import xarray as xr

from datetime import datetime
from os.path import basename


class DuacsCurrentDataLoader(VectorDataLoader):
    def import_data(self, bounds):
        """
        Reads in data from a DUACS altimeter derived current NetCDF file.
        Renames coordinates to 'lat' and 'long', and renames variable to
        'uC, vC'

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                Near real-time current dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'uC', 'vC'
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
        data = data.rename(
            {"latitude": "lat", "longitude": "long", "ugos": "uC", "vgos": "vC"}
        )

        # Drop unnecessary variable, if present
        if "crs" in data.keys():
            data = data.drop_vars("crs")

        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)

        return data
