from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import xarray as xr

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class ECMWFSigWaveHeightDataLoader(ScalarDataLoader):  # type: ignore[misc]
    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Reads in data from a ECMWF GRIB2 file, or folder of files.
        Extracts Significant wave height

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            xr.Dataset:
                ECMWF SWH dataset within limits of bounds.
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        """

        def extract_base_date(filename: str) -> datetime:
            filename = os.path.basename(filename)
            base_date = filename.split("-")[0]
            return datetime.strptime(base_date, "%Y%m%d%H0000")

        def calculate_timestamp(filename: str) -> datetime:
            """
            Get date from filename in format:
                YYYYMMDDHH0000-wave-fc.grib2
            """
            # Get filename independant of directory
            filename = os.path.basename(filename)
            # Get date of file and forecast timedelta
            base_date_str, forecast_len_str, _, _ = filename.split("-")
            # Turn forecast len into number of hours
            forecast_len_hours = int(forecast_len_str[:-1])
            # Calculate
            return datetime.strptime(base_date_str, "%Y%m%d%H0000") + timedelta(
                hours=forecast_len_hours
            )

        def retrieve_data(filename: str, timestamp: datetime) -> xr.Dataset:
            """
            Read in data as xr.Dataset, create time coordinate
            """
            data = xr.open_dataset(filename)
            # Add date to data
            return data.assign_coords(time=timestamp)

        # Date limits
        start_time = datetime.strptime(bounds.get_time_min(), "%Y-%m-%d")
        end_time = datetime.strptime(bounds.get_time_max(), "%Y-%m-%d")

        # Go through reverse alphabetical list until date < start_date found
        if self.files is None:
            raise ValueError("files parameter is required for ECMWFSigWaveHeightDataLoader")
        sorted_files: list[str] = sorted(self.files, reverse=True)
        for file in sorted_files:
            base_date = extract_base_date(file)
            if base_date < start_time:
                closest_date = base_date
                break
        # If none found, raise error
        else:
            raise FileNotFoundError("No file found prior to start time")
        # Limit files to be read in
        filtered_files: list[str] = [
            file for file in sorted_files if extract_base_date(file) == closest_date
        ]

        data_array: list[xr.Dataset] = []
        relevant_files: list[str] = []
        # Limit data to forecasts that cover time boundary
        for file in filtered_files:
            timestamp = calculate_timestamp(file)
            print(start_time, timestamp, end_time)
            if start_time <= timestamp <= end_time:
                data_array.append(retrieve_data(file, timestamp))
                relevant_files += [file]
        # Concat all valid files
        if len(data_array) == 0:
            logging.error(
                "\tNo files found for date range "
                + f"[ {bounds.get_time_min()} : {bounds.get_time_max()} ]"
            )
            raise FileNotFoundError("No ECMWF Wave files found within specified time range!")
        data = xr.concat(data_array, "time")

        # Extract just SWH
        data = data["swh"].to_dataset()
        data = data.rename({"latitude": "lat", "longitude": "long"})

        data = data.reindex(lat=data.lat[::-1])
        data = data.reset_coords(drop=True)
        # Limit self.files to only those actually used
        self.files: list[str] = relevant_files

        return data
