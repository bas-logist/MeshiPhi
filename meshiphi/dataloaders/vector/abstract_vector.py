from meshiphi.dataloaders.dataloader_interface import DataLoaderInterface
from abc import abstractmethod

from pyproj import Transformer, CRS

import logging
import numpy as np
import xarray as xr
import pandas as pd
from rasterio.enums import Resampling

from meshiphi.mesh_generation.boundary import Boundary


class VectorDataLoader(DataLoaderInterface):
    '''
    Abstract class for all vector Datasets.
    '''
    def __init__(self, bounds, params):
        '''
        This is where large-scale operations are performed, 
        such as importing data, downsampling, reprojecting, and renaming 
        variables
        
        Args:
            bounds (Boundary): 
                Initial mesh boundary to limit scope of data ingest
            params (dict): 
                Values needed by dataloader to initialise. Unique to each
                dataloader

        Attributes:
            self.data (pd.DataFrame or xr.Dataset): 
                Data stored by dataloader to use when called upon by the mesh.
                Must be saved in mercator projection (EPSG:4326), with 
                coordinates names 'lat', 'long', and 'time' (if applicable).
            self.data_name (str): 
                Name of scalar variable. Must be the column name if self.data
                is pd.DataFrame. Must be variable if self.data is xr.Dataset
        '''
        # Translates parameters from config input to desired inputs
        params = self.add_default_params(params)
        logger.info(f"Initialising {params['dataloader_name']} dataloader")
        # Creates a class attribute for all keys in params
        for key, val in params.items():
            setattr(self, key, val)
            
        self.data = self.import_data(bounds)
        # Read in and manipulate data to standard form
        if 'files' in params:
            logger.info('\tFiles read:')
            for file in self.files:
                logger.info(f'\t\t{file}')
        # If need to downsample data
        self.data = self.downsample()
        # If need to reproject data
        if self.in_proj != self.out_proj:
            self.data = self.reproject(
                                in_proj  = self.in_proj,
                                out_proj = self.out_proj,
                                x_col    = self.x_col,
                                y_col    = self.y_col
                                )

        # Get data name from column name if not set in params
        if self.data_name is None:
            logger.debug('\tSetting self.data_name from column name')
            self.data_name = self.get_data_col_name()
        # or if set in params, set col name to data name
        else:
            logger.debug(f'\tSetting data column name to {self.data_name}')
            self.data = self.set_data_col_name(self.data_name.split(','))
        # Store data names in a list for easier access in future
        self.data_name_list = self.data_name.split(',')
        
        # Add magnitude and direction to dataset
        self.data = self.add_mag_dir()
        
        # Calculate fraction of boundary that data covers
        data_coverage = self.calculate_coverage(bounds)
        logger.info("\tMercator data range (roughly) covers "+\
                    f"{np.round(data_coverage*100,0).astype(int)}% "+\
                     "of initial boundary")
        # If there's 0 datapoints in the initial boundary, raise ValueError
        if data_coverage == 0:
            logger.warning('\tDataloader has no data in initial region!')
            # raise ValueError(f"Dataloader {params['dataloader_name']}"+\
                            #   " contains no data within initial region!")
        else:
            # Cut dataset down to initial boundary
            logger.info(
                "\tTrimming data to initial boundary: {min} to {max}".format(
                    min=(bounds.get_lat_min(), bounds.get_long_min()),
                    max=(bounds.get_lat_max(), bounds.get_long_max())
                ))
            
            self.data = self.trim_datapoints(bounds)

    @abstractmethod
    def import_data(self, bounds):
        '''
        User defined method for importing data from files, or even generating 
        data from scratch
                
        Returns:
            xr.Dataset or pd.DataFrame:
                Coordinates and data being imported from file \n
                if xr.Dataset, 
                    - Must have coordinates 'lat' and 'long'
                    - Should have multiple data variables
                    
                if pd.DataFrame, 
                    - Must have columns 'lat' and 'long'
                    - Should have multiple data columns
                    
                Downsampling and reprojecting happen in __init__() method
        '''
        pass
    
    def add_default_params(self, params):
        '''
        Set default values for all scalar dataloaders. This function should be
        overloaded to include any extra params for a specific dataloader
        
        Args:
            params (dict): 
                Dictionary containing attributes that are required for each 
                dataloader. 
            
        Returns:
            (dict): 
                Dictionary of attributes the dataloader will require, 
                completed with default values if not provided in config.
        '''
        # This should only pop up if using dataloader not in the factory
        if 'dataloader_name' not in params:
            params['dataloader_name'] = self.__class__.__name__
        
        if 'data_name' not in params:
            params['data_name'] = None

        if 'downsample_factors' not in params:
            params['downsample_factors'] = [1,1]

        if 'aggregate_type' not in params: 
            params['aggregate_type']  = 'MEAN'
            
        if 'min_dp' not in params:
            params['min_dp'] = 5
            
        if 'in_proj' not in params:
            params['in_proj'] = 'EPSG:4326'
            
        if 'out_proj' not in params:
            params['out_proj'] = 'EPSG:4326'
            
        if 'x_col' not in params:
            params['x_col'] = 'lat'

        if 'y_col' not in params:
            params['y_col'] = 'long'

        if 'fast_reprojection' not in params:
            params['fast_reprojection'] = False
            
        return params
    
    def add_mag_dir(self, data=None, data_names=None):
        '''
        Adds magnitude and direction variables/columns to data for easier
        retrieval of value 
        
        Args:
            data (pd.DataFrame or xr.Dataset):
                Data with 'lat' and 'long' columns/dimensions. Assumes that the
                existing data is in cartesian form (x and y components). 
                If None, will use self.data
            data_names (list):
                List of data columns/variables to use in calculation
                If None, will use self.data_name_list
                
        Returns:
            data (pd.DataFrame or xr.Dataset):
                Original dataset with two new columns/variables called 
                '_magnitude' and '_direction', containing the corresponding
                values for each.
        '''
        
        def add_mag_dir_to_df(data, names):
            '''
            Adds magnitude and direction columns to pd.DataFrame
            
            Args:
                Same as parent method
                
            Returns:
                Same as parent method
            '''
            x, y = names
            data['_magnitude'] = np.linalg.norm([data[x], data[y]], axis=0)
            data['_direction'] = np.arctan2(data[y], data[x])
            return data
        
        def add_mag_dir_to_xr(data, names):
            '''
            Adds magnitude and direction columns to xr.Dataset
            
            Args:
                Same as parent method
                
            Returns:
                Same as parent method
            '''
            x, y = names
            data['_magnitude'] = (data.dims, 
                                  np.linalg.norm([data[x].data, data[y].data], 
                                                 axis=0))
            data['_direction'] = (data.dims, 
                                  np.arctan2(data[y].data, data[x].data))
            return data
        
        # Set defaults if not passed to method
        if data is None:        data = self.data
        if data_names is None:  names = self.data_name_list
        
        # Perform operation on appropriate datatype
        if type(data) == pd.core.frame.DataFrame:
            return add_mag_dir_to_df(data, names)
        elif type(data) == xr.core.dataset.Dataset:
            return add_mag_dir_to_xr(data, names)

    def calculate_coverage(self, bounds, data=None):
        """
        Calculates percentage of boundary covered by dataset

        Args:
            bounds (Boundary): 
                Boundary being compared against
            data (pd.DataFrame or xr.Dataset): 
                Dataset with 'lat' and 'long' coordinates. 
                Extent calculated from min/max of these coordinates. 
                Defaults to objects internal dataset.
        
        Returns:
            float:
                Decimal fraction of boundary covered by the dataset
        """
        def calculate_coverage_from_df(bounds, data):
            data = data.dropna().reset_index()
            # If empty dataframe, 0% coverage
            if data.empty:
                return 0
            # If no valid coordinates within data range, 0% coverage
            elif data.lat.size == 0 or data.long.size == 0:
                return 0
            # Otherwise, calculate coverage, assuming rectangular region 
            # in mercator projection
            else:
                # Create a polygon to calculate overlap region from
                data_boundary = Boundary([data.lat.min(), data.lat.max()],
                                         [data.long.min(), data.long.max()])
                data_polygon = data_boundary.to_polygon()
                bounds_polygon = bounds.to_polygon()

                # Get fraction of bounds covered by data
                overlap_area = data_polygon.intersection(bounds_polygon).area
                total_area = bounds_polygon.area

                return overlap_area / total_area
                
                
        def calculate_coverage_from_xr(bounds, data):
            # Remove all NaN columns/rows
            data = data.dropna(dim="lat", how="all")
            data = data.dropna(dim="long", how="all")
            
            # If no valid coordinates within data range, 0% coverage
            if data.lat.size == 0 or data.long.size == 0:
                return 0
            # Otherwise, calculate coverage, assuming rectangular region 
            # in mercator projection
            else:
                # Create a polygon to calculate overlap region from
                data_boundary = Boundary([data.lat.min().item(), data.lat.max().item()],
                                         [data.long.min().item(), data.long.max().item()])
                data_polygon = data_boundary.to_polygon()
                bounds_polygon = bounds.to_polygon()

                # Get fraction of bounds covered by data
                overlap_area = data_polygon.intersection(bounds_polygon).area
                total_area = bounds_polygon.area

                return overlap_area / total_area
            
        # Use self.data if not no explicit dataset specified
        if data is None:
            data = self.data
        # Calculate data coverage fraction
        if type(self.data) == pd.core.frame.DataFrame:
            return calculate_coverage_from_df(bounds, data)
        elif type(self.data) == xr.core.dataset.Dataset:
            return calculate_coverage_from_xr(bounds, data)

    def trim_datapoints(self, bounds, data=None):
        '''
        Trims datapoints from self.data within boundary defined by 'bounds'.
        self.data can be pd.DataFrame or xr.Dataset
        
        Args:
            bounds (Boundary): Limits of lat/long/time to select data from

        Returns:
            pd.DataFrame or xr.Dataset: 
                Trimmed dataset in same format as self.data
        '''
        def trim_datapoints_from_df(data, bounds):
            '''
            Extracts data from a pd.DataFrame
            '''
            # Mask off any positions not within spatial bounds
            # If not going through antimeridian
            if bounds.get_long_min() < bounds.get_long_max():
                mask = (data['lat']  > bounds.get_lat_min())  & \
                    (data['lat']  <= bounds.get_lat_max())  & \
                    (data['long'] > bounds.get_long_min()) & \
                    (data['long'] <= bounds.get_long_max())
            else:
                mask = (data['lat']  > bounds.get_lat_min())  & \
                    (data['lat']  <= bounds.get_lat_max())  & \
                    (data['long'] <= bounds.get_long_min()) & \
                    (data['long'] > bounds.get_long_max())
            # Mask with time if time column exists
            if 'time' in data.columns:
                mask &= (data['time'] >= bounds.get_time_min()) & \
                        (data['time'] <= bounds.get_time_max())
                        
            # Return column of data from within bounds
            return data.loc[mask]

        def trim_datapoints_from_xr(data, bounds):
            '''
            Extracts data from a xr.Dataset using optimized spatial indexing
            '''
            # Integer-based indexing
            try:
                # Get coordinate values as numpy arrays
                lat_vals = data.lat.values
                long_vals = data.long.values
                
                lat_min_idx = np.searchsorted(lat_vals, bounds.get_lat_min(), side='right')
                lat_max_idx = np.searchsorted(lat_vals, bounds.get_lat_max(), side='right')
                
                if bounds.get_long_min() < bounds.get_long_max():
                    long_min_idx = np.searchsorted(long_vals, bounds.get_long_min(), side='right')
                    long_max_idx = np.searchsorted(long_vals, bounds.get_long_max(), side='right')
                    
                    # Use integer-based indexing (faster than coordinate-based)
                    data = data.isel(lat=slice(lat_min_idx, lat_max_idx),
                                    long=slice(long_min_idx, long_max_idx))
                else:
                    # Fallback to coordinate-based selection
                    data = data.sel(lat=slice(bounds.get_lat_min(), bounds.get_lat_max()))
                    data_lhs = data.sel(long=slice(-180, bounds.get_long_max()))
                    data_rhs = data.sel(long=slice(bounds.get_long_min(), 180))
                    data = xr.concat([data_lhs, data_rhs], 'long')
                    
            except (ValueError, KeyError, AttributeError):
                # Fallback to standard coordinate-based selection if optimisation fails
                data = data.sel(lat=slice(bounds.get_lat_min(), bounds.get_lat_max()))
                if bounds.get_long_min() < bounds.get_long_max():
                    data = data.sel(long=slice(bounds.get_long_min(), bounds.get_long_max()))
                else:
                    data_lhs = data.sel(long=slice(-180, bounds.get_long_max()))
                    data_rhs = data.sel(long=slice(bounds.get_long_min(), 180))
                    data = xr.concat([data_lhs, data_rhs], 'long')
            
            # Select data region within temporal bounds if time exists as a coordinate
            if 'time' in data.coords.keys():
                data = data.sel(time=slice(bounds.get_time_min(),  bounds.get_time_max()))

            # Trim off any data on the min boundary to be consistent with df
            if len(data.lat) > 0 and bounds.get_lat_min() in data.lat.values:
                data = data.where(data.lat  != bounds.get_lat_min(), drop=True)
            if len(data.long) > 0 and bounds.get_long_min() in data.long.values:
                data = data.where(data.long != bounds.get_long_min(), drop=True)
            
            # Return column of data from within bounds
            return data
        
        # If no specific data passed in, default to entire dataset
        if data is None:
            data = self.data
        
        if type(data) == pd.core.frame.DataFrame:
            return trim_datapoints_from_df(data, bounds)
        elif type(data) == xr.core.dataset.Dataset:
            return trim_datapoints_from_xr(data, bounds)
    
    def get_value(self, bounds, agg_type=None, skipna=True, data=None):
        '''
        Retrieve aggregated value from within bounds
        
        Args:
            aggregation_type (str): Method of aggregation of datapoints within
                bounds. Can be upper or lower case. 
                Accepts 'MIN', 'MAX', 'MEAN', 'MEDIAN', 'STD', 'COUNT'
            bounds (Boundary): Boundary object with limits of lat/long
            skipna (bool): Defines whether to propogate NaN's or not
                Default = True (ignore's NaN's)

        Returns:
            dict: 
                {variable (str): aggregated_value (float)}
                Aggregated value within bounds following aggregation_type
                
        Raises:
            ValueError: aggregation type not in list of available methods
        '''
        def get_value_from_df(dps, variable_names, bounds, agg_type, skipna):
            '''
            Aggregates a value from a pd.Series.
            
            Args:
                dps (pd.Series): Datapoints within boundary
                bounds (Boundary): 
                    Boundary dps was trimmed to. Not used for any calculations,
                    just the logger.debug message.
                agg_type (str):
                    Method of aggregation for the value, 
                    e.g. agg_type = 'MIN' => min(dps) returned 
                skipna (bool): 
                    Flag for whether NaN's should be included in aggregation. 
            
            Returns:
                np.float64: Aggregated value
            '''
            data_count = len(dps)
            logger.debug(f"\t{data_count} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'")
            # If no data
            if data_count == 0:
                values = [np.nan, np.nan]
            # If want the number of datapoints
            elif agg_type =='COUNT':
                values = [data_count, data_count]
            elif agg_type == 'MIN':
                index = dps['_magnitude'].idxmin(skipna=skipna)
                if ~np.isnan(index):
                    values = [dps[name][index] for name in variable_names]
                else:
                    values = [np.nan for name in variable_names]
            elif agg_type == 'MAX':
                index = dps['_magnitude'].idxmax(skipna=skipna)
                if ~np.isnan(index):
                    values = [dps[name][index] for name in variable_names]
                else:
                    values = [np.nan for name in variable_names]
            elif agg_type == 'MEAN':
                values = [dps[name].mean(skipna=skipna) for name in variable_names]
            elif agg_type == 'STD':
                values = [dps[name].std(skipna=skipna) for name in variable_names]
            elif agg_type == 'MEDIAN':
                raise ValueError('Aggregation type "MEDIAN" is non-sensical for vector dataset!')
            else:
                raise ValueError(f'Unknown aggregation type {agg_type}')
            
            return values

        
        def get_value_from_xr(dps, variable_names, bounds, agg_type, skipna):
            '''
            Aggregates a value from a xr.DataArray.
            
            Args:
                dps (xr.DataArray): Datapoints within boundary
                bounds (Boundary): 
                    Boundary dps was trimmed to. Not used for any calculations,
                    just the logger.debug message.
                agg_type (str):
                    Method of aggregation for the value, 
                    e.g. agg_type = 'MIN' => min(dps) returned 
                skipna (bool): 
                    Flag for whether NaN's should be included in aggregation. 
            
            Returns:
                dict:
                    {variable_name: np.float64}: Aggregated value in a dictionary
            '''
            # Info on size of array
            data_count = dps._magnitude.size 
            logger.debug(f"\t{data_count} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'")
            # If no data, return np.nan for each variable
            if data_count == 0:
                values = [np.nan for _ in variable_names]
            elif np.isnan(dps._magnitude).all():
                values = [np.nan for _ in variable_names]
            # If want count
            elif agg_type == 'COUNT':
                # If including nan's, just want size
                if skipna:  
                    values = [data_count for _ in variable_names]
                # Otherwise count non-nan values
                else:       
                    values = [dps[name].count().item() for name in variable_names]
            elif agg_type == 'MIN':
                # Get 2D index of minimum magnitude point
                index = np.unravel_index(
                            dps._magnitude.argmin(skipna=skipna), 
                            dps._magnitude.shape)
                # Get cartesian vector from index
                values = [dps[name][index].item() for name in variable_names]
            elif agg_type == 'MAX':
                # Get 2D index of minimum magnitude point
                index = np.unravel_index(
                            dps._magnitude.argmax(skipna=skipna), 
                            dps._magnitude.shape)
                # Get cartesian vector from index
                values = [dps[name][index].item() for name in variable_names]
            # And the rest self explanatory
            elif agg_type == 'MEAN':
                values = [dps[name].mean(skipna=skipna).item() for name in variable_names]
            elif agg_type == 'STD':
                values = [dps[name].std(skipna=skipna).item() for name in variable_names]
            elif agg_type == 'MEDIAN':
                raise ValueError('Aggregation type "MEDIAN" is non-sensical for vector dataset!')
            else:
                raise ValueError(f'Unknown aggregation type {agg_type}')
            
            return values
    

        # Set to params if no specific aggregate type specified
        if agg_type is None:
            agg_type = self.aggregate_type
            
        # Limit data to boundary
        if data is None:
            dps = self.trim_datapoints(bounds, data=data)
        else:
            dps = data
        # Get list of values
        if type(self.data) == pd.core.frame.DataFrame:
            values = get_value_from_df(dps, self.data_name_list, bounds, agg_type, skipna)
        elif type(self.data) == xr.core.dataset.Dataset:
            values = get_value_from_xr(dps, self.data_name_list, bounds, agg_type, skipna)
            
        # Put in dict to map variable to values
        return {self.data_name_list[i]: values[i] for i in range(len(self.data_name_list))}

    def get_hom_condition(self, bounds, splitting_conds, agg_type='MEAN', data=None):
        '''
        Retrieves homogeneity condition of data within boundary. 
         
        Args: 
            bounds (Boundary): Boundary object with limits of datarange to analyse
            splitting_conds (dict): Containing the following keys: \n
                'threshold':  
                    `(float)` The threshold at which data points of 
                    type 'value' within this CellBox are checked to be either 
                    above or below

        Returns:
            str:
                The homogeniety condtion returned is of the form: \n
                'MIN' = the cellbox contains less than a minimum number of 
                data points \n
                'HET' = Threshold values defined in config are exceeded \n
                'CLR' = None of the HET conditions were triggered \n
        '''
        if data is None:
            data = self.trim_datapoints(bounds)

        # Get length of dataset in bounds  
        if type(self.data) == pd.core.frame.DataFrame:
            num_dp = len(self.trim_datapoints(bounds))
        elif type(self.data) == xr.core.dataset.Dataset:
            num_dp = min(self.trim_datapoints(bounds).count().values())

        # Set default homogeneity 
        hom_type = 'CLR'

        # Check to see if it's above the minimum threshold
        if num_dp < self.min_dp:
            logger.debug(f"\t{num_dp} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'")
            hom_type = 'CLR'
        else:
            # To allow multiple modes of splitting, chuck them in the splitting conditions
            # Split if magnitude of curl(data) is larger than threshold 
            if 'curl' in splitting_conds:
                flow = self.calc_curl(bounds, collapse=False)
                sc = splitting_conds['curl']
            # Split if max magnitude(any_vector - ave_vector) is larger than threshold
            elif 'dmag' in splitting_conds:
                flow = self.calc_dmag(bounds, collapse=False)
                sc = splitting_conds['dmag']

            if 'split_lock' not in sc:
                sc['split_lock'] = False

            if isinstance(flow, type(np.nan)) and np.isnan(flow):
                return "CLR"
            num_over_threshold = (flow > sc['threshold']).sum()
            
            num_non_nan = np.count_nonzero(~np.isnan(flow))
            if num_non_nan > 0:
                frac_over_threshold = num_over_threshold/num_non_nan
            else:
                frac_over_threshold = 0


            if   frac_over_threshold <= sc['lower_bound']: 
                hom_type = "CLR"
            elif frac_over_threshold >= sc['upper_bound']:
                if sc['split_lock'] == True:
                    hom_type = "HOM"
                else: 
                    hom_type = "CLR"
            else: hom_type = "HET"
                

        logger.debug(f"\thom_condition for attribute: '{self.data_name}' in bounds:'{bounds}' returned '{hom_type}'")
        
        return hom_type

    def reproject(self, in_proj='EPSG:4326', out_proj='EPSG:4326', 
                        x_col='lat', y_col='long'):
        '''
        Reprojects data using pyProj.Transformer
        self.data can be pd.DataFrame or xr.Dataset
        
        Args:
            in_proj (str): 
                Projection that the imported dataset is in
                Must be allowed by PyProj.CRS (Coordinate Reference System)
            out_proj (str): 
                Projection required for final data output
                Must be allowed by PyProj.CRS (Coordinate Reference System)
                Shouldn't change from default value (EPSG:4326)
            x_col (str): Name of coordinate column 1
            y_col (str): Name of coordinate column 2
                x_col and y_col will be cast into lat and long by the 
                reprojection 
            
        Returns:
            pd.DataFrame: 
                Reprojected data with 'lat', 'long' columns 
                replacing 'x_col' and 'y_col'
        '''
        def reproject_df(data, in_proj, out_proj, x_col, y_col):
            '''
            Reprojects a pandas dataframe
            
            Args:
                data (pd.DataFrame):
                    Data to reproject, with coordinates x_col, y_col
                in_proj (str): 
                    Projection the original dataset is in, as a string 
                    understandable by PyProj (e.g. 'EPSG:3031')
                out_proj (str):
                    Projection desired as output format. Should be always be
                    Mercator, but doesn't have to be if you desire
                    (e.g. 'EPSG:4326)
                x_col (str): 
                    Coordinate that original dataset includes that will be 
                    projected. Will be replaced with longitude values
                y_col (str):
                    Coordinate that original dataset includes that will be 
                    projected. Will be replaces with latitude values
                
            Returns:
                pd.DataFrame:
                    Reprojected dataset, with columns 'lat', 'long', 
                    ('time' if in original dataset), and data_name
            '''
            # Do the reprojection
            x, y = Transformer\
                    .from_crs(CRS(in_proj), CRS(out_proj), always_xy=True)\
                    .transform(data[x_col].to_numpy(), data[y_col].to_numpy())
            # Replace columns with reprojected columns called 'lat'/'long'
            if x_col != 'long':  data = data.drop(x_col, axis=1)
            if y_col != 'lat': data = data.drop(y_col, axis=1)
            data['lat']  = y
            data['long'] = x
            
            return data
            
        def reproject_xr(data, in_proj, out_proj, x_col, y_col, fast=False):
            '''
            Reprojects a xr.Dataset
            
            Args:
                data (xr.Dataset):
                    Data to reproject, with coordinates x_col, y_col
                in_proj (str): 
                    Projection the original dataset is in, as a string 
                    understandable by rioxarray (e.g. 'EPSG:3031')
                out_proj (str):
                    Projection desired as output format. Should be always be
                    Mercator, but doesn't have to be if you desire
                    (e.g. 'EPSG:4326)
                x_col (str): 
                    Coordinate that original dataset includes that will be 
                    projected. Will be replaced with longitude values
                y_col (str):
                    Coordinate that original dataset includes that will be 
                    projected. Will be replaces with latitude values
                
            Returns:
                pd.DataFrame:
                    Reprojected dataset, with columns 'lat', 'long', 
                    ('time' if in original dataset), and data_name
            '''
            if fast:
            # If want fast results (uses interpolation)
                max_size = sum(data.sizes.values())
                # Set data CRS
                data = data.rio.write_crs(in_proj)
                # Reproject
                data = data.rio.reproject(out_proj, resampling=Resampling.bilinear,
                                                    shape=((max_size,max_size)), 
                                                    nodata=np.nan)
                # Rename coordinates
                data = data.rename({x_col: 'long', y_col: 'lat'})
                # Reorder coords in case they are wrong
                data = data.sortby('lat', ascending=True)
                data = data.sortby('long', ascending=True)
                return data
            # If want accurate results
            else:
                df = data.to_dataframe().reset_index().dropna()
                return reproject_df(df, in_proj, out_proj, x_col, y_col)

        # If no reprojection to do
        if in_proj == out_proj:
            logger.debug("\tself.reproject() called but don't need to")
            return self.data
        else:
            logger.info(f"\tReprojecting data from {in_proj} to {out_proj}")
        # Choose appropriate method of reprojection based on data type
        if type(self.data) == pd.core.frame.DataFrame:
            return reproject_df(self.data, in_proj, out_proj, x_col, y_col)
        elif type(self.data) == xr.core.dataset.Dataset:
            return reproject_xr(self.data, in_proj, out_proj, x_col, y_col,
                                fast=self.fast_reprojection)
    
    def downsample(self, agg_type=None):
        '''
        Downsamples imported data to be more easily manipulated. Data size 
        should be reduced by a factor of m*n, where (m,n) are the 
        downsample_factors defined in the params.        
        self.data can be pd.DataFrame or xr.Dataset
        
        Args:
            agg_type (str): 
                Method of aggregation to bin data by to downsample. Default is
                same method used for homogeneity condition.            

        Returns:
            xr.Dataset or pd.DataFrame: 
                Downsampled data
        '''
        def downsample_xr(data, ds, agg_type):
            '''
            Downsample xarray dataset according to aggregation type
            
            Args:
                data (xr.Dataset):
                    Dataset containing data to be downsampled. Must have 
                    coordinates 'lat' and 'long'
                ds (int, int):
                    Downsampling factors. 
                    ds[0] is longitude
                    ds[1] is latitude
                agg_type (str):
                    Aggregation method to use for binning. Default is same as 
                    set in config, passed in by parent
            
            Returns:
                xr.Dataset:
                    Downsampled data
            '''
            if agg_type == 'MIN':
                # Returns min of bin
                data = data.coarsen(lat=ds[1],boundary='pad').min()
                data = data.coarsen(long=ds[0],boundary='pad').min()
            elif agg_type == 'MAX':
                # Returns max of bin
                data = data.coarsen(lat=ds[1],boundary='pad').max()
                data = data.coarsen(long=ds[0],boundary='pad').max()
            elif agg_type == 'MEAN':
                # Returns mean of bin
                data = data.coarsen(lat=ds[1],boundary='pad').mean()
                data = data.coarsen(long=ds[0],boundary='pad').mean()
            elif agg_type == 'MEDIAN':
                # Returns median of bin
                data = data.coarsen(lat=ds[1],boundary='pad').median()
                data = data.coarsen(long=ds[0],boundary='pad').median()
            elif agg_type == 'STD':
                # Returns std_dev of range
                data = data.coarsen(lat=ds[1],boundary='pad').std()
                data = data.coarsen(long=ds[0],boundary='pad').std()
            elif agg_type =='COUNT': 
                # Returns every first element in bin
                data = data.thin(lat=ds[1])
                data = data.thin(long=ds[0])
            return data
    
        def downsample_df(data, ds, agg_type):
            '''
            Downsample pandas dataframe
            Not implemented as it just adds to processing time, 
            defeating the purpose
            '''
            logger.warning(
                '\tDownsampling called on pd.DataFrame! Downsampling a df' \
                'too computationally expensive, returning original df'
                )
            return data

        # Set to params if no specific aggregate type specified
        if agg_type is None:
            agg_type = self.aggregate_type
        
        # If no downsampling
        if self.downsample_factors == (1,1) or \
           self.downsample_factors == [1,1]:
            logger.debug("\tself.downsample() called but don't have to")
            return self.data
        else:
            logger.info(f"\tDownsampling data by {self.downsample_factors}")
        # Otherwise, downsample appropriately
        if type(self.data) == pd.core.frame.DataFrame:
            return downsample_df(self.data, self.downsample_factors, agg_type)
        elif type(self.data) == xr.core.dataset.Dataset:
            return downsample_xr(self.data, self.downsample_factors, agg_type)
        
    def get_data_col_name(self):
        '''
        Retrieve name of data column (for pd.DataFrame), or variable 
        (for xr.Dataset). Used for when data_name not defined in params.
        Variable names are appended and comma seperated

        Returns:
            str: 
                Name of data columns, comma seperated
        '''
        def get_data_names_from_df(data):
            '''
            Filters out standard columns to extract only data column's name
            '''
            # Store name of data column for future reference
            columns = data.columns
            # Filter out lat, long, time columns leaves us with data column name
            filtered_cols = filter(lambda col: \
                                    col not in ['lat','long','time'], columns)
            data_names = list(filtered_cols)
            # Turn into comma seperated string and return
            return ','.join(data_names)
        
        def get_data_names_from_xr(data):
            '''
            Extracts variable name directly from xr.Dataset metadata
            '''
            # Extract data variables from xr.Dataset
            data_names = list(data.keys())
            # Turn into comma seperated string and return
            return ','.join(data_names)
        
        logger.debug(f"\tRetrieving data name from {type(self.data)}")
        # Choose method of extraction based on data type
        if type(self.data) == pd.core.frame.DataFrame:
            return get_data_names_from_df(self.data)
        elif type(self.data) == xr.core.dataset.Dataset:
            return get_data_names_from_xr(self.data)

    def get_data_col_name_list(self):
        '''
        Retrieve names of data columns (for pd.DataFrame), or variable 
        (for xr.Dataset). Used for when data_name not defined in params.

        Returns:
            list: 
                Contains strings of data namesk
        '''
        return self.get_data_col_name().split(',')

    def set_data_col_name(self, new_names):
        '''
        Sets name of data column/data variables from a comma-seperated string
        
        Args:
            name_dict (dict): 
                Dictionary mapping old variable names to new variable names,
                of the form {old_name (str): new_name (str)}

        Returns:
            xr.Dataset or pd.DataFrame: 
                Data with variable name changed
        '''
        def set_names_df(data, name_dict):
            '''
            Renames data columns in pandas dataframe
            '''
            # Rename data column to new name
            return data.rename(columns=name_dict)
        def set_names_xr(data, name_dict):
            '''
            Renames data variables in xarray dataset
            '''
            # Rename data variable to new name
            return data.rename(name_dict)
        # Get existing column names
        old_names = self.get_data_col_name().split(',')
        # Ensure that can do replacement of columns
        assert len(old_names) == len(new_names)
        # Set up mapping of old names to new names
        name_dict = {old_col: new_names[i] 
                     for i, old_col in enumerate(old_names)}
        # Change names
        # Change data name depending on data type
        if type(self.data) == pd.core.frame.DataFrame:
            return set_names_df(self.data, name_dict)
        elif type(self.data) == xr.core.dataset.Dataset:
            return set_names_xr(self.data, name_dict)
        
    def set_data_col_name_list(self, new_names):
        '''
        Sets name of data column/data variables from a list of strings.
        Also updates self.data_name_list with new names from list
        
        Args:
            new_names (list):
                List of strings containing new variable names
        
        Returns:
            pd.DataFrame or xr.Dataset:
                Original dataset with data variables renamed
        '''
        # Check validity of input
        assert type(new_names) == list, f"'new_names' must be a list! Instead it is a {type(new_names)}"
        assert len(new_names) == 2, f"'new_names' must have a length of 2! Instead it has length {len(new_names)}"
        str_items = [isinstance(name, str) for name in new_names]
        assert all(str_items), f"'new_names' must be list of 'str'. Currently {sum(str_items)} / 2 are strings!"
        new_data_name = ','.join(new_names)
        
        # Set names
        logger.info(f'\tSetting data names to {new_names}')
        self.data_name_list = new_names
        return self.set_data_col_name(new_data_name)

    def calc_curl(self, bounds, data=None, collapse=True, agg_type='MAX'):
        '''
        Calculates the curl of vectors in a cellbox
        
        Args:
            bounds (Boundary):
                Cellbox boundary in which all relevant vectors are contained
            data (pd.DataFrame or xr.Dataset):
                Dataset with 'lat' and 'long' columns/dimensions with vectors
            collapes (bool): 
                Flag determining whether to return an aggregated value, or a 
                vector field (values for each individual vector).
            agg_type (str):
                Method of aggregation if collapsing value. 
                Accepts 'MAX' or 'MEAN'
        
        Returns:
            float or pd.DataFrame:
                float value of aggregated curl if collapse=True, or
                pd.DataFrame of curl vector field if collapse=False
                
        Raises:
            ValueError: If agg_type is not 'MAX' or 'MEAN'
        '''
        if data is None:    dps = self.trim_datapoints(bounds, data=data)
        else:               dps = data
        # Create a meshgrid of vectors from the data
        vector_field = self._create_vector_meshgrid(dps, self.data_name_list)
        # Get component values for each vector
        fx, fy = vector_field[:, :, 0], vector_field[:, :, 1]
        # If not enough datapoints to compute gradient
        if 1 in fx.shape or 1 in fy.shape:
            logger.debug('\tUnable to compute gradient across cell for curl calculation')
            curl = np.nan
        else:
            # Compute partial derivatives
            dfx_dy = np.gradient(fx, axis=1)
            dfy_dx = np.gradient(fy, axis=0)
            # Compute curl
            curl = dfy_dx - dfx_dy

        # If curl is nan
        if np.isnan(curl).all():
            logger.debug('\tAll NaN cellbox encountered')
            return np.nan
        # If want to collapse to max mag value, return scalar
        elif collapse:
            if agg_type == 'MAX': return max(np.nanmax(curl), np.nanmin(curl), key=abs)
            elif agg_type == 'MEAN':    return np.nanmean(curl)
            else: 
                raise ValueError(f"agg_type '{agg_type}' not understood! Requires 'MAX' or 'MEAN'")
        # Else return field
        else:
            return curl

    def calc_dmag(self, bounds, data=None, collapse=True, agg_type='MEAN'):
        '''
        Calculates the dmag of vectors in a cellbox.
        dmag is defined as being the difference in magnitudes between 
        each vector and the average vector within the bounds.\n
        dmag = mag(vector - mean_vector)
        
        Args:
            bounds (Boundary):
                Cellbox boundary in which all relevant vectors are contained
            data (pd.DataFrame or xr.Dataset):
                Dataset with 'lat' and 'long' columns/dimensions with vectors
            collapes (bool): 
                Flag determining whether to return an aggregated value, or a 
                vector field (values for each individual vector).
            agg_type (str):
                Method of aggregation if collapsing value. 
                Accepts 'MAX' or 'MEAN'
        
        Returns:
            float or pd.DataFrame:
                float value of aggregated dmag if collapse=True, or
                pd.DataFrame of dmag vector field if collapse=False
                
        Raises:
            ValueError: If agg_type is not 'MAX' or 'MEAN'
        '''
        if data is None:    dps = self.trim_datapoints(bounds, data=data)
        else:               dps = data
            
        data_names = self.data_name_list
        each_vector = dps[data_names].to_numpy()
        ave_vector = list(self.get_value(bounds, agg_type=agg_type).values())
        
        delta_vector = each_vector - ave_vector
        
        d_mag = np.linalg.norm(delta_vector, axis=1)
        if len(d_mag) == 0:
            logger.debug('\tEmpty cellbox encountered')
            return np.nan
        # If d_mag is nan
        elif np.isnan(d_mag).all():
            logger.debug('\tAll NaN cellbox encountered')
            return np.nan
        # If want to collapse to max mag value, return scalar
        elif collapse:
            if agg_type == 'MAX':       return np.nanmax(d_mag)
            elif agg_type == 'MEAN':    return np.nanmean(d_mag)
            else:
                raise ValueError(f"agg_type '{agg_type}' not understood! Requires 'MAX' or 'MEAN'")
        # Else return field
        else:          return d_mag

    @staticmethod
    def _create_vector_meshgrid(data, data_name_list):
        '''
        Creates a np.meshgrid containing 2D vectors from a pd.DataFrame
        
        Args:
            data (pd.DataFrame): 
                Dataframe with columns 'lat', 'long', and vector x/y components
                lat | long | {v_x} | {v_y}
            data_name_list (list): 
                List of strings containing the vector component names
        
        Returns:
            np.array:
                Table containing vectors as np.arrays at each coord
        
        '''
        def meshgrid_from_df(data, data_name_list):

            # Manipulate into meshgrid of 2D vectors
            x, y = data_name_list
            # Fields of each vector component
            vector_x_field = data.pivot(index='lat', columns='long', values=x)
            vector_y_field = data.pivot(index='lat', columns='long', values=y)
            # Combine into field of vectors
            vector_field = np.stack((vector_x_field, vector_y_field), axis=-1)
            vector_field = np.swapaxes(vector_field, 0, 1)
            return vector_field
        
        def meshgrid_from_xr(data, data_name_list):
            # Extract out each variable and combine as tuple
            data_arrays = [data[name].values 
                                for name in data_name_list]
            # Zip them together to make 2D array of n-dimensional vectors
            return np.dstack(data_arrays)
        
        if type(data) == pd.core.frame.DataFrame:
            return meshgrid_from_df(data, data_name_list)
        elif type(data) == xr.core.dataset.Dataset:
            return meshgrid_from_xr(data, data_name_list)
        
        

    
    