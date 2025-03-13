from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

import logging
import xarray as xr
from datetime import datetime

class AMSRHourlyDataLoader(ScalarDataLoader):
    def import_data(self, bounds):
        '''
        Reads in data from a AMSR NetCDF file, or folder of files. 
        Drops unnecessary column 'polar_stereographic', and renames variable
        'z' to 'SIC'
        
        Args:
            bounds (Boundary): Initial boundary to limit the dataset to
            
        Returns:
            xr.Dataset: 
                AMSR SIC dataset within limits of bounds. 
                Dataset has coordinates 'lat', 'long', and variable 'SIC'
        '''
        def retrieve_date(filename):
            '''
            Get date from filename in format:
                asi-AMSR2-s6250-<year><month><day>-v.5.4_H{hour}.nc
            '''
            date = filename.split('-')[-2]
            hour = filename.split('-')[-1].split('_')[-1].split('.')[0]
            hour = int(hour[1:])

            date_str = f'{date[:4]}-{date[4:6]}-{date[6:]}T{hour:02d}'
            return date_str
        
        def retrieve_data(filename, date):
            '''
            Read in data as xr.Dataset, create time coordinate
            '''
            data = xr.open_dataset(filename)
            # Add date to data
            # data = data.assign_coords(time=date)
            data = data.assign_coords(time=datetime.strptime(date, '%Y-%m-%dT%H'))
            return data

        data_array = []
        relevant_files = []
        # For each file found from config
        logging.info(self.files)
        for file in self.files:
            logging.info(file)
            # If date within boundary
            date = retrieve_date(file)
            logging.info(date)
            # If file data from within time boundary, append to list
            # Doing now to avoid ingesting too much data initially
            if datetime.strptime(bounds.get_time_min(), '%Y-%m-%d') <= \
                datetime.strptime(date, '%Y-%m-%dT%H') <= \
                datetime.strptime(bounds.get_time_max(), '%Y-%m-%d'):
                data_array.append(retrieve_data(file, date))
                relevant_files += [file]
        # Concat all valid files
        if len(data_array) == 0:
            logging.error('\tNo files found for date range '+\
                         f'[ {bounds.get_time_min()} : {bounds.get_time_max()} ]')
            raise FileNotFoundError('No AMSR files found within specified time range!')
        data = xr.concat(data_array,'time').sortby('time')

        data = data.rename({'z': 'SIC'})

        # Rename columns to standard format
        data = data.rename({'lon':'long'})
        # Trim to initial datapoints
        data = self.trim_datapoints(bounds, data=data)
        
        # Limit self.files to only those actually used
        self.files = relevant_files
        
        return data
