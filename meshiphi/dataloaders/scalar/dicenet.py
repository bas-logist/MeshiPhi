from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

import logging
from datetime import datetime

import xarray as xr
import pandas as pd
import numpy as np


class DIceNetDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
        '''
        Reads in data from a dIceNet NetCDF file. 
        Renames coordinates to 'lat' and 'long', and renames variable to 
        'SIC'.
        
        Args:
            bounds (Boundary): Initial boundary to limit the dataset to
            
        Returns:
            pd.DataFrame: 
                DiceNet dataset within limits of bounds. 
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        '''
        # Convert temporal boundary to datetime objects for comparison
        max_time = datetime.strptime(bounds.get_time_max(), '%Y-%m-%d')
        min_time = datetime.strptime(bounds.get_time_min(), '%Y-%m-%d')
        
        # For now, use the first file (in future could select based on init_time in file)
        # The temporal filtering will be done based on the time coordinate in the file
        filename = self.files[0]
        logging.info(f"- Opening dIceNet file: {filename}")
        ds = xr.open_dataset(filename)
        
        # Cast coordinates/variables to those understood by mesh
        # dIceNet uses 'latitude'/'longitude' which need to be renamed to 'lat'/'long'
        ds = ds.rename({'latitude': 'lat',
                        'longitude': 'long',
                        'sic_mean': 'SIC'})
        
        # Get the initialization time and available forecast times
        init_time = pd.to_datetime(ds.init_time.values)
        time_coords = pd.to_datetime(ds.time.values)
        max_leadtime = len(time_coords)
        
        logging.info(f"- dIceNet initialization time: {init_time}")
        logging.info(f"- Available forecast times: {time_coords[0]} to {time_coords[-1]}")
        logging.info(f"- Available leadtimes: {max_leadtime} days")
        
        # Convert time boundaries to pandas datetime for easier comparison
        min_time_pd = pd.to_datetime(min_time)
        max_time_pd = pd.to_datetime(max_time)
        
        # Find the time indices that fall within our boundary
        valid_times = (time_coords >= min_time_pd) & (time_coords <= max_time_pd)
        
        if not valid_times.any():
            raise ValueError(f'No forecast times available within boundary {min_time} to {max_time}')
        
        # Select only the time indices we need
        time_indices = np.where(valid_times)[0]
        logging.info(f"- Selecting {len(time_indices)} time steps from indices {time_indices[0]} to {time_indices[-1]}")
        
        ds = ds.isel(time=time_indices)
        
        # Convert to DataFrame
        df = ds.to_dataframe().reset_index()
        
        # Time coordinate is already in proper datetime format, no conversion needed
        
        # Drop unwanted columns if they exist
        columns_to_drop = ['Y', 'X', 'bounds', 'ensemble_member', 'init_time', 
                          'mask', 'latitude_bounds', 'longitude_bounds', 'sic', 'sic_std']
        existing_columns = [col for col in columns_to_drop if col in df.columns]
        if existing_columns:
            df = df.drop(columns=existing_columns)
            
        # Ensure we only keep the required columns
        required_columns = ['time', 'lat', 'long', 'SIC']
        df = df[required_columns]
        
        # Trim to initial datapoints
        df = self.trim_datapoints(bounds, data=df)
        
        # Turn SIC into a percentage if it's in fraction form (0-1)
        # Check if values are in 0-1 range (fraction) or 0-100 range (percentage)
        sic_max = df.SIC.max()
        if sic_max <= 1.0:
            df.SIC = df.SIC.apply(lambda x: x * 100)
            
        logging.info(f"- dIceNet data loaded with SIC range: {df.SIC.min():.2f}% to {df.SIC.max():.2f}%")
        
        # Return extracted data
        return df