from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader

import logging
import pandas as pd
import numpy as np


class VectorShapeDataLoader(VectorDataLoader):

    def add_default_params(self, params):
        """
        Set default values for vector shape dataloaders

        Args:
            params (dict):
                Dictionary containing attributes that are required for the
                shape being loaded. Must include 'shape'.

        Returns:
            (dict):
                Dictionary of attributes the dataloader will require,
                completed with default values if not provided in config.
        """
        # Add default vector params
        params = super().add_default_params(params)

        # Number of datapoints to populate per axis
        if 'nx' not in params:
            params['nx'] = 101
        if 'ny' not in params:
            params['ny'] = 101

        # Scaling factor to multiply data points by
        if 'multiplier_u' not in params:
            params['multiplier'] = 1
        if 'multiplier_v' not in params:
            params['multiplier'] = 1

        # Define default circle parameters
        if params['dataloader_name'] == 'circle':
            if 'radius' not in params:
                params['radius'] = 1
            if 'centre' not in params:
                params['centre'] = (None, None)
        # Define default rectangle parameters
        elif params['dataloader_name'] == 'rectangle':
            if 'width' not in params:
                params['width'] = 1
            if 'height' not in params:
                params['width'] = 1
            if 'centre' not in params:
                params['centre'] = (None, None)
        # Define default gradient params
        elif params['dataloader_name'] == 'gradient':
            if 'vertical' not in params:
                params['vertical'] = True

        return params

    def import_data(self, bounds):
        """
        Generates data in the form of an abstract shape, such as circle,
        or gradient. This method acts like a factory in that it simply
        selects the correct shape method to enact

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            data_xr (xarray):
                xarray with coordinates within bounds, and values between
                [0:1]. xarray has dimensions 'lat', 'long', 'time',
                'dummy_data_u' and 'dummy_data_v' (by default)
        """

        # Generate abstract data set
        if self.dataloader_name == 'vector_circle':
            data = self.gen_circle(bounds)
        elif self.dataloader_name == 'vector_gradient':
            data = self.gen_gradient(bounds)
        elif self.dataloader_name == 'vector_rectangle':
            data = self.gen_rectangle(bounds)
        else:
            raise ValueError(
                f'Unknown vector shape type: {self.dataloader_name}'
                )

        data_xr = data.set_index(['lat', 'long']).to_xarray()
        # No need to trim data, as was defined by bounds

        return data_xr

    def gen_gradient(self, bounds):
        """
            Generates a gradient within bounds of lat/long min/max.
            Gradient direction can be defined in the config, as well as
            resolution of simulated datapoints
            Args:
                bounds (Boundary): Limits of lat/long to generate within
        """
        logger.info("\tSetting up boundary of dataset")
        # Generate rows
        self.lat = np.linspace(bounds.get_lat_min(),
                               bounds.get_lat_max(),
                               self.ny)
        # Generate cols
        self.long = np.linspace(bounds.get_long_min(),
                                bounds.get_long_max(),
                                self.nx)

        logger.info("\tCreating gradient of values")
        # Create 1D gradient
        if self.vertical:
            gradient = np.linspace(0, 1, self.ny)
        else:
            gradient = np.linspace(0, 1, self.nx)

        dummy_df = pd.DataFrame(columns=['lat', 'long', 'dummy_data_u', 'dummy_data_v'])
        logger.info("- Generating vector dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Change dummy data depending on which axis to gradient
                datum = gradient[i] if self.vertical else gradient[j]
                # Create a new row, adding datum value
                if self.vertical:
                    row = pd.DataFrame(data={'lat': self.lat[i],
                                             'long': self.long[j],
                                             'dummy_data_u': 0.0,
                                             'dummy_data_v': datum}, index=[0])
                else:
                    row = pd.DataFrame(data={'lat': self.lat[i],
                                             'long': self.long[j],
                                             'dummy_data_u': datum,
                                             'dummy_data_v': 0.0}, index=[0])
                # Avoid concat with empty df
                if dummy_df.empty:
                    dummy_df = row
                else:
                    dummy_df = pd.concat([dummy_df, row],
                                         ignore_index=True)

        # Multiply by scaling factor if present
        dummy_df['dummy_data_u'] = dummy_df['dummy_data_u'] * self.multiplier_u
        dummy_df['dummy_data_v'] = dummy_df['dummy_data_v'] * self.multiplier_v

        return dummy_df

    def gen_circle(self, bounds):
        """
            Generates a circle within bounds of lat/long min/max.
            Circle centre and radius can be defined in the config, as well as
            resolution of simulated datapoints
            Args:
                bounds (Boundary): Limits of lat/long to generate within
        """
        logger.info("\tSetting up boundary of dataset")
        # Generate rows
        self.lat = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny)
        # Generate cols
        self.long = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        # Set centre as centre of data_grid if none specified
        c_y = self.lat[int(self.ny / 2)] if not self.centre[0] else self.centre[0]
        c_x = self.long[int(self.nx / 2)] if not self.centre[1] else self.centre[1]

        # Create vectors for row and col indices
        y = np.vstack(np.linspace(bounds.get_lat_min(),
                                  bounds.get_lat_max(),
                                  self.ny))
        x = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        logger.info("\tCreating mask of circle")
        # Create a 2D-array with distance from defined centre
        dist_from_centre = np.sqrt((x - c_x) ** 2 + (y - c_y) ** 2)
        # Turn this into a mask of values within radius
        mask = dist_from_centre <= self.radius
        # Set up empty dataframe to populate with dummy data
        dummy_df = pd.DataFrame(columns=['lat', 'long', 'dummy_data_u', 'dummy_data_v'])
        logger.info("\tGenerating vector dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Create a new row, adding mask value
                row = pd.DataFrame(data={'lat': self.lat[i],
                                         'long': self.long[j],
                                         'dummy_data_u': mask[i][j],
                                         'dummy_data_v': mask[i][j]}, index=[0])
                # Avoid concat with empty df
                if dummy_df.empty:
                    dummy_df = row
                else:
                    dummy_df = pd.concat([dummy_df, row],
                                         ignore_index=True)

        # Change boolean values to int
        dummy_df['dummy_data_u'] = dummy_df['dummy_data_u'].astype(int)
        dummy_df['dummy_data_v'] = dummy_df['dummy_data_v'].astype(int)
        # Multiply by scaling factor if present
        dummy_df['dummy_data_u'] = dummy_df['dummy_data_u'] * self.multiplier_u
        dummy_df['dummy_data_v'] = dummy_df['dummy_data_v'] * self.multiplier_v

        return dummy_df

    def gen_rectangle(self, bounds):
        """
            Generates a rectangle within bounds of lat/long min/max.
            Side lengths and centroid can be defined in the config, as well as
            resolution of simulated datapoints
            Args:
                bounds (Boundary): Limits of lat/long to generate within
        """
        logger.info("\tSetting up boundary of dataset")
        # Generate rows
        self.lat = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny)
        # Generate cols
        self.long = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        # Set centre as centre of data_grid if none specified
        c_y = self.lat[int(self.ny / 2)] if not self.centre[0] else self.centre[0]
        c_x = self.long[int(self.nx / 2)] if not self.centre[1] else self.centre[1]

        # Create vectors for row and col indices
        y = np.vstack(np.linspace(bounds.get_lat_min(),
                                  bounds.get_lat_max(),
                                  self.ny))
        x = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        logger.info("\tCreating mask of a rectangle")
        # Create a 2D-array with distance along cartesian axes from defined centre
        x_dist_from_centre = np.abs(x - c_x)
        y_dist_from_centre = np.abs(y - c_y)
        # Turn this into a mask of values within the rectangle
        mask = np.logical_and(x_dist_from_centre <= self.width, y_dist_from_centre <= self.height)
        # Set up empty dataframe to populate with dummy data
        dummy_df = pd.DataFrame(columns=['lat', 'long', 'dummy_data_u', 'dummy_data_v'])
        logger.info("\tGenerating vector dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Create a new row, adding mask value
                row = pd.DataFrame(data={'lat': self.lat[i],
                                         'long': self.long[j],
                                         'dummy_data_u': mask[i][j],
                                         'dummy_data_v': mask[i][j]}, index=[0])
                # Avoid concat with empty df
                if dummy_df.empty:
                    dummy_df = row
                else:
                    dummy_df = pd.concat([dummy_df, row],
                                         ignore_index=True)

        # Change boolean values to int
        dummy_df['dummy_data_u'] = dummy_df['dummy_data_u'].astype(int)
        dummy_df['dummy_data_v'] = dummy_df['dummy_data_v'].astype(int)
        # Multiply by scaling factor if present
        dummy_df['dummy_data_u'] = dummy_df['dummy_data_u'] * self.multiplier_u
        dummy_df['dummy_data_v'] = dummy_df['dummy_data_v'] * self.multiplier_v

        return dummy_df
