from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import xarray as xr  # noqa: TC002

from meshiphi.dataloaders.vector.abstract_vector import VectorDataLoader
from meshiphi.utils import gaussian_random_field

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary


class VectorGRFDataLoader(VectorDataLoader):  # type: ignore[misc]
    def add_default_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Set default values for abstract GRF dataloaders, starting by
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
        # Set default vector dataloader params
        params = super().add_default_params(params)

        # Params that all GRF dataloaders need
        if "seed" not in params:
            params["seed"] = None
        if "size" not in params:
            params["size"] = 512
        if "alpha" not in params:
            params["alpha"] = 3
        # Column/variable names
        if params["data_name"] is None:
            params["data_name"] = "uC,vC"
        data_name = params["data_name"]
        if data_name is not None:
            if "vec_x" not in params:
                params["vec_x"] = data_name.split(",")[0]
            if "vec_y" not in params:
                params["vec_y"] = data_name.split(",")[1]
        # Min/Max magnitude
        if "min" not in params:
            params["min"] = 0
        if "max" not in params:
            params["max"] = 10

        return params

    def import_data(self, bounds: Boundary) -> xr.Dataset:
        """
        Creates data in the form of a Gaussian Random Field

        Args:
            bounds (Boundary): Initial boundary to limit the dataset to

        Returns:
            pd.DataFrame:
                Scalar dataset within limits of bounds. Dataset has coordinates
                'lat', 'long', and variable name 'data'. \n
                NOTE - In __init__, variable name will be set to data_name if
                defined in config

        """

        def grf_to_vector(
            magnitudes: np.ndarray[Any, Any],
            directions: np.ndarray[Any, Any],
            min_val: float,
            max_val: float,
        ) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
            # Scale to max/min
            magnitudes = magnitudes * (max_val - min_val) + min_val

            dy = np.cos(directions) * magnitudes
            dx = np.sin(directions) * magnitudes

            return dx, dy

        # Set seed for generation. If not specified, will be 'random'
        np.random.seed(self.seed)

        # Validate required attributes
        if self.size is None:
            raise ValueError("size parameter is required for VectorGRFDataLoader")
        if self.alpha is None:
            raise ValueError("alpha parameter is required for VectorGRFDataLoader")
        if self.vec_x is None or self.vec_y is None:
            raise ValueError("vec_x and vec_y parameters are required for VectorGRFDataLoader")

        # Create a GRF of magnitudes and angles
        magnitudes = gaussian_random_field(self.size, self.alpha)
        directions = gaussian_random_field(self.size, self.alpha)
        directions = np.radians(360 * directions)

        vec_x, vec_y = grf_to_vector(magnitudes, directions, self.min, self.max)

        # Set up domain of field
        lat_array = np.linspace(bounds.get_lat_min(), bounds.get_lat_max(), self.size)
        long_array = np.linspace(bounds.get_long_min(), bounds.get_long_max(), self.size)
        latv, longv = np.meshgrid(lat_array, long_array, indexing="ij")

        # Create an entry for each row in final dataframe
        rows = [
            {
                "lat": latv[i, j],
                "long": longv[i, j],
                self.vec_x: vec_x[i, j],
                self.vec_y: vec_y[i, j],
            }
            for i in range(self.size)
            for j in range(self.size)
        ]
        # Cast to dataframe
        data = pd.DataFrame(rows).set_index(["lat", "long"])
        # Set to xarray dataset
        return data.to_xarray()
