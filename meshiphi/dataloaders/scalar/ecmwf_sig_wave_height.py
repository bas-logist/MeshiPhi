from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader
from datetime import datetime, timedelta
import logging
import os
import xarray as xr

class ECMWFSigWaveHeightDataLoader(ScalarDataLoader):

    def import_data(self, bounds):
        '''
        Reads in data from a ECMWF GRIB2 file, or folder of files. 
        Extracts Significant wave height
        
        Args:
            bounds (Boundary): Initial boundary to limit the dataset to
            
        Returns:
            xr.Dataset: 
                ECMWF SWH dataset within limits of bounds. 
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        '''
        def extract_base_date(filename):
            filename = os.path.basename(filename)
            base_date = filename.split('-')[0]
            base_date = datetime.strptime(base_date, '%Y%m%d%H0000')
            return base_date
            
        def calculate_timestamp(filename):
            '''
            Get date from filename in format:
                YYYYMMDDHH0000-wave-fc.grib2
            '''
            # Get filename independant of directory
            filename = os.path.basename(filename)
            # Get date of file and forecast timedelta
            base_date, forecast_len, _, _ = filename.split('-')
            # Turn forecast len into number of hours
            forecast_len = int(forecast_len[:-1])
            # Calculate 
            date = datetime.strptime(base_date, '%Y%m%d%H0000') + \
                   timedelta(hours=forecast_len)
            return date
        
        def retrieve_data(filename, timestamp):
            '''
            Read in data as xr.Dataset, create time coordinate
            '''
            data = xr.open_dataset(filename)
            # Add date to data
            data = data.assign_coords(time=timestamp)
            return data
        
        # Date limits
        start_time = datetime.strptime(bounds.get_time_min(), '%Y-%m-%d')
        end_time   = datetime.strptime(bounds.get_time_max(), '%Y-%m-%d')
        
        # Go through reverse alphabetical list until date < start_date found 
        self.files = sorted(self.files, reverse=True)
        for file in self.files:
            base_date = extract_base_date(file)
            if  base_date < start_time:
                closest_date = base_date
                break
        # If none found, raise error
        else:
            raise FileNotFoundError('No file found prior to start time')
        # Limit files to be read in
        self.files = [file for file in self.files 
                      if extract_base_date(file) == closest_date]
        
        data_array = []
        relevant_files = []
        # Limit data to forecasts that cover time boundary
        for file in self.files:
            timestamp = calculate_timestamp(file)
            print(start_time, timestamp, end_time)
            if start_time <= timestamp <= end_time:
                data_array.append(retrieve_data(file, timestamp))
                relevant_files += [file]
        # Concat all valid files
        if len(data_array) == 0:
            logger.error('\tNo files found for date range '+\
                         f'[ {bounds.get_time_min()} : {bounds.get_time_max()} ]')
            raise FileNotFoundError('No ECMWF Wave files found within specified time range!')
        data = xr.concat(data_array,'time')
        
        # Extract just SWH
        data = data['swh'].to_dataset()
        data = data.rename({'latitude':'lat',
                            'longitude':'long'})
        
        data = data.reindex(lat=data.lat[::-1])
        data = data.reset_coords(drop=True)
        # Limit self.files to only those actually used
        self.files = relevant_files
        
        return data
