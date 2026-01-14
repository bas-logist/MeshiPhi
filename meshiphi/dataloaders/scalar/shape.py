import logging

import numpy as np
import pandas as pd

from meshiphi.dataloaders.scalar.abstract_scalar import ScalarDataLoader

logger = logging.getLogger(__name__)


class ShapeDataLoader(ScalarDataLoader):
    def add_default_params(self, params):
        """
        Set default values for abstract shape dataloaders, starting by
        including defaults for scalar dataloaders.

        Args:
            params (dict):
                Dictionary containing attributes that are required for the
                shape being loaded. Must include 'shape'.

        Returns:
            (dict):
                Dictionary of attributes the dataloader will require,
                completed with default values if not provided in config.
        """
        # Add default scalar params
        params = super().add_default_params(params)

        # Number of datapoints to populate per axis
        if "nx" not in params:
            params["nx"] = 101
        if "ny" not in params:
            params["ny"] = 101

        # Scaling factor to multiply data points by
        if "multiplier" not in params:
            params["multiplier"] = 1

        # Define default circle parameters
        if params["dataloader_name"] == "circle":
            if "radius" not in params:
                params["radius"] = 1
            if "centre" not in params:
                params["centre"] = (None, None)
        # Define default rectangle parameters
        elif params["dataloader_name"] == "rectangle":
            if "width" not in params:
                params["width"] = 1
            if "height" not in params:
                params["width"] = 1
            if "centre" not in params:
                params["centre"] = (None, None)
        # Define default gradient params
        elif params["dataloader_name"] == "gradient":
            if "vertical" not in params:
                params["vertical"] = True
        # Define default checkerboard params
        elif params["dataloader_name"] == "checkerboard":
            if "gridsize" not in params:
                params["gridsize"] = (1, 1)

        return params

    def import_data(self, bounds):
        """
        Generates data in the form of an abstract shape, such as circle,
        checkerboard, or gradient. This method acts like a factory in that
        it simply selects the correct shape method to enact

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            data_xr (xarray):
                xarray with coordinates within bounds, and values between
                [0:1]. xarray has dimensions 'lat', 'long', 'time', and
                'dummy_data' (by default)
        """
        # TODO Move self.lat/long = np.linspace here after reg tests pass

        # Generate abstract data set
        if self.dataloader_name == "circle":
            data = self.gen_circle(bounds)
        elif self.dataloader_name == "checkerboard":
            data = self.gen_checkerboard(bounds)
        elif self.dataloader_name == "gradient":
            data = self.gen_gradient(bounds)
        elif self.dataloader_name == "rectangle":
            data = self.gen_rectangle(bounds)
        else:
            raise ValueError(f"Unknown abstract shape type: {self.dataloader_name}")

        # No need to trim data, as was defined by bounds
        return data.set_index(["lat", "long"]).to_xarray()

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
        if self.radius is None:
            raise ValueError("radius parameter is required for circle")
        if self.centre is None:
            self.centre = (None, None)
        c_y = self.lat[int(self.ny / 2)] if self.centre[0] is None else self.centre[0]
        c_x = self.long[int(self.nx / 2)] if self.centre[1] is None else self.centre[1]

        # Create vectors for row and col idx's
        y = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny).reshape(-1, 1)
        x = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        logger.info("\tCreating mask of circle")
        # Create a 2D-array with distance from defined centre
        dist_from_centre = np.sqrt((x - c_x) ** 2 + (y - c_y) ** 2)
        # Turn this into a mask of values within radius
        mask = dist_from_centre <= self.radius
        # Set up empty dataframe to populate with dummy data
        dummy_df = pd.DataFrame(columns=["lat", "long", "dummy_data"])
        logger.info("\tGenerating dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Create a new row, adding mask value
                row = pd.DataFrame(
                    data={
                        "lat": self.lat[i],
                        "long": self.long[j],
                        "dummy_data": mask[i][j],
                    },
                    index=[0],
                )
                # Avoid concat with empty df
                dummy_df = row if dummy_df.empty else pd.concat([dummy_df, row], ignore_index=True)

        # Change boolean values to int
        dummy_df["dummy_data"] = dummy_df["dummy_data"].astype(int)
        # Multiply by scaling factor if present
        if self.multiplier is None:
            self.multiplier = 1.0
        dummy_df["dummy_data"] = dummy_df["dummy_data"] * self.multiplier

        return dummy_df

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
        self.lat = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny)
        # Generate cols
        self.long = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        logger.info("\tCreating gradient of values")
        # Create 1D gradient
        if self.vertical is None:
            self.vertical = True  # Default to vertical gradient
        gradient = np.linspace(0, 1, self.ny) if self.vertical else np.linspace(0, 1, self.nx)

        dummy_df = pd.DataFrame(columns=["lat", "long", "dummy_data"])
        logger.info("- Generating dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Change dummy data depending on which axis to gradient
                datum = gradient[i] if self.vertical else gradient[j]
                # Create a new row, adding datum value
                row = pd.DataFrame(
                    data={
                        "lat": self.lat[i],
                        "long": self.long[j],
                        "dummy_data": datum,
                    },
                    index=[0],
                )
                # Avoid concat with empty df
                dummy_df = row if dummy_df.empty else pd.concat([dummy_df, row], ignore_index=True)

        # Multiply by scaling factor if present
        dummy_df["dummy_data"] = dummy_df["dummy_data"] * self.multiplier

        return dummy_df

    def gen_checkerboard(self, bounds):
        """
        Generates a checkerboard pattern within bounds of lat/long min/max
        Square size can be defined in the config, as well as resolution of
        simulated datapoints
        Args:
            bounds (Boundary): Limits of lat/long to generate within
        """
        logger.info("\tSetting up boundary of dataset")
        # Generate rows
        self.lat = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny, endpoint=False)
        # Generate cols
        self.long = np.linspace(
            bounds.get_long_min(), bounds.get_long_max(), self.nx, endpoint=False
        )

        logger.info("- Creating series of 0's and 1's for lat/long")
        # Create checkerboard pattern
        if self.gridsize is None:
            self.gridsize = (1, 1)
        if isinstance(self.gridsize, int):
            gridsize_tuple = (self.gridsize, self.gridsize)
        else:
            gridsize_tuple = self.gridsize
        # Create horizontal stripes of 0's and 1's, stripe size defined by gridsize
        horizontal = np.floor((self.lat - bounds.get_lat_min()) / gridsize_tuple[1]) % 2
        # Create vertical stripes of 0's and 1's, stripe size defined by gridsize
        vertical = np.floor((self.long - bounds.get_long_min()) / gridsize_tuple[0]) % 2
        dummy_df = pd.DataFrame(columns=["lat", "long", "dummy_data"])
        logger.info("- Generating dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Horizontal XOR Vertical should create boxes
                datum = (horizontal[i] + vertical[j]) % 2
                # Create a new row, adding datum value
                row = pd.DataFrame(
                    data={
                        "lat": self.lat[i],
                        "long": self.long[j],
                        "dummy_data": datum,
                    },
                    index=[0],
                )
                # Avoid concat with empty df
                dummy_df = row if dummy_df.empty else pd.concat([dummy_df, row], ignore_index=True)

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
        if self.width is None or self.height is None:
            raise ValueError("width and height parameters are required for rectangle")
        if self.centre is None:
            self.centre = (None, None)
        c_y = self.lat[int(self.ny / 2)] if self.centre[0] is None else self.centre[0]
        c_x = self.long[int(self.nx / 2)] if self.centre[1] is None else self.centre[1]

        # Create vectors for row and col idx's
        y = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.ny).reshape(-1, 1)
        x = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.nx)

        logger.info("\tCreating mask of a rectangle")
        # Create a 2D-array with distance along cartesian axes from defined centre
        x_dist_from_centre = np.abs(x - c_x)
        y_dist_from_centre = np.abs(y - c_y)
        # Turn this into a mask of values within the rectangle
        mask = np.logical_and(x_dist_from_centre <= self.width, y_dist_from_centre <= self.height)
        # Set up empty dataframe to populate with dummy data
        dummy_df = pd.DataFrame(columns=["lat", "long", "dummy_data"])
        logger.info("\tGenerating dataset")
        # For each combination of lat/long
        for i in range(self.ny):
            for j in range(self.nx):
                # Create a new row, adding mask value
                row = pd.DataFrame(
                    data={
                        "lat": self.lat[i],
                        "long": self.long[j],
                        "dummy_data": mask[i][j],
                    },
                    index=[0],
                )
                # Avoid concat with empty df
                dummy_df = row if dummy_df.empty else pd.concat([dummy_df, row], ignore_index=True)

        # Change boolean values to int
        dummy_df["dummy_data"] = dummy_df["dummy_data"].astype(int)
        # Multiply by scaling factor if present
        if self.multiplier is None:
            self.multiplier = 1.0
        dummy_df["dummy_data"] = dummy_df["dummy_data"] * self.multiplier

        return dummy_df
