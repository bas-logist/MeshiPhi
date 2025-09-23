from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader
import logging
from datetime import datetime, timedelta
import xarray as xr
from pandas import to_timedelta
from numpy import datetime64
import pyproj
from pyproj import Transformer
import pandas as pd
import numpy as np


class IceNetDiffusionDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
        '''
        Reads in data from a IceNet Diffusion Model  NetCDF file. 
        Projects the dataset from Lambert Conformal 
            -> pyproj.Proj(proj='aea', lat_1=77.5, lat_2=77.5, lat_0=77.5, lon_0=-25.0, x_0=0, y_0=0, ellps='GRS80', datum='NAD83', units='m', no_defs=True), 
        and renames variable to creates a pd.DataFrame with columns 'lat', 'long', and 'SIC' (Sea Ice Concentration).
        
        Args:
            bounds (Boundary): Initial boundary to limit the dataset to
            
        Returns:
            pd.DataFrame: 
                IceNet dataset within limits of bounds. 
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        '''
        # def filename_to_datetime(filename):
        #     '''
        #     Converts icenet filenames to datetime objects
        #     Assumes file names are in the format 
        #     <hemisphere>_daily_forecast.<YYYY-MM-DD>.nc
        #     '''
        #     return datetime.strptime(filename.split('.')[1], '%Y-%m-%d')
        
        # # Convert temporal boundary to datetime objects for comparison
        # max_time = datetime.strptime(bounds.get_time_max(), '%Y-%m-%d')
        # min_time = datetime.strptime(bounds.get_time_min(), '%Y-%m-%d')
        # time_range = max_time - min_time
        # # Retrieve list of dates from filenames
        # file_dates = {filename_to_datetime(file): file 
        #               for file in self.files 
        #               if filename_to_datetime(file) < min_time}
        # # Find closest date prior to min_time
        # closest_date = max(k for k, v in file_dates.items())

        # Open Dataset
        ds = xr.load_dataset(self.files[0],decode_times=False)
        X,Y = np.meshgrid(ds.X,ds.Y)

        input_crs = pyproj.Proj(proj='aea', lat_1=77.5, lat_2=77.5, lat_0=77.5, lon_0=-25.0, x_0=0, y_0=0, ellps='GRS80', datum='NAD83', units='m', no_defs=True)
        transformer = Transformer.from_crs(input_crs.crs, 'EPSG:4326', always_xy=True)
        lon, lat = transformer.transform(X, Y)

        print(self.leadtime)


        df = pd.DataFrame({'long': lon.flatten(),
                            'lat': lat.flatten(),
                            'SIC': ds.sic[0,int(self.sample),int(self.leadtime),:,:].values.flatten()})

        # Turning SIC into percentage
        df['SIC'] = df['SIC'].astype('float32')*100.0
        print(df['SIC'].mean())
        
        # Return extracted data
        return df