from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any, cast

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import CRS, Transformer
from rasterio.enums import Resampling

from meshiphi.dataloaders.dataloader_interface import DataLoaderInterface
from meshiphi.mesh_generation.boundary import Boundary

logger = logging.getLogger(__name__)


class ScalarDataLoader(DataLoaderInterface):
    """
    Abstract class for all scalar Datasets.
    """

    # Type hints for dynamically set attributes (set via setattr in __init__)
    files: list[str] | None
    data_name: str | None
    dataloader_name: str
    in_proj: str
    out_proj: str
    x_col: str
    y_col: str
    downsample_factors: list[int]
    aggregate_type: str
    min_dp: int
    fast_reprojection: bool
    # Shape-specific attributes (set by shape dataloaders)
    # nx and ny always have defaults (101), so they're not optional
    ny: int = 101
    nx: int = 101
    vertical: bool | None = None
    multiplier: float | None = None
    radius: float | None = None
    centre: tuple[float, float] | tuple[None, None] | None = None
    width: float | None = None
    height: float | None = None
    gridsize: int | tuple[int, int] | None = None
    # GRF-specific attributes
    seed: int | None = None
    size: int | None = None
    alpha: float | None = None
    binary: bool | None = None
    threshold: float | None = None
    min: float | None = None
    max: float | None = None
    offset: float | None = None

    def __init__(self, bounds: Boundary, params: dict[str, Any]) -> None:
        """
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

        Raises:
            ValueError: If no data lies within the parsed boundary
        """
        # Translates parameters from config input to desired inputs
        params = self.add_default_params(params)
        logger.info(f"Initialising {params['dataloader_name']} dataloader")
        # Creates a class attribute for all keys in params
        for key, val in params.items():
            setattr(self, key, val)

        # Read in and manipulate data to standard form
        self.data = self.import_data(bounds)
        if "files" in params and self.files is not None:
            logger.info("\tFiles read:")
            for file in self.files:
                logger.info(f"\t\t{file}")
        # If need to downsample data
        self.data = self.downsample()
        # If need to reproject data
        if self.in_proj != self.out_proj:
            self.data = self.reproject(
                in_proj=self.in_proj,
                out_proj=self.out_proj,
                x_col=self.x_col,
                y_col=self.y_col,
            )
        # Get data name from column name if not set in params
        if self.data_name is None:
            logger.debug("\tSetting self.data_name from column name")
            self.data_name = self.get_data_col_name()
        # or if set in params, set col name to data name
        else:
            logger.debug(f"\tSetting data column name to {self.data_name}")
            self.data = self.set_data_col_name(self.data_name)

        # Calculate fraction of boundary that data covers
        data_coverage = self.calculate_coverage(bounds)
        logger.info(
            "\tMercator data range (roughly) covers "
            + f"{np.round(data_coverage * 100, 0).astype(int)}% "
            + "of initial boundary"
        )
        # If there's 0 datapoints in the initial boundary, raise ValueError
        if data_coverage == 0:
            logger.warning("\tDataloader has no data in initial region!")
            # raise ValueError(f"Dataloader {params['dataloader_name']}"+\
            #                  " contains no data within initial region!")
        else:
            # Cut dataset down to initial boundary
            logger.info(
                f"\tTrimming data to initial boundary: {(bounds.get_lat_min(), bounds.get_long_min())} to {(bounds.get_lat_max(), bounds.get_long_max())}"
            )

            self.data = self.trim_datapoints(bounds)

    @abstractmethod
    def import_data(self, bounds: Boundary) -> xr.Dataset | pd.DataFrame:
        """
        User defined method for importing data from files, or even generating
        data from scratch

        Returns:
            xr.Dataset or pd.DataFrame:
                Coordinates and data being imported from file \n
                if xr.Dataset,
                    - Must have coordinates 'lat' and 'long'
                    - Must have single data variable

                if pd.DataFrame,
                    - Must have columns 'lat' and 'long'
                    - Must have single data column

                Downsampling and reprojecting happen in __init__() method
        """

    def add_default_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
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
        """
        if "dataloader_name" not in params:
            params["dataloader_name"] = self.__class__.__name__

        if "data_name" not in params:
            params["data_name"] = None

        if "downsample_factors" not in params:
            params["downsample_factors"] = [1, 1]

        if "aggregate_type" not in params:
            params["aggregate_type"] = "MEAN"

        if "min_dp" not in params:
            params["min_dp"] = 5

        if "in_proj" not in params:
            params["in_proj"] = "EPSG:4326"

        if "out_proj" not in params:
            params["out_proj"] = "EPSG:4326"

        if "x_col" not in params:
            params["x_col"] = "lat"

        if "y_col" not in params:
            params["y_col"] = "long"

        if "fast_reprojection" not in params:
            params["fast_reprojection"] = False

        return params

    def calculate_coverage(
        self, bounds: Boundary, data: xr.Dataset | pd.DataFrame | None = None
    ) -> float:
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

        def calculate_coverage_from_df(bounds: Boundary, data: pd.DataFrame) -> float:
            data = data.dropna().reset_index()
            # If empty dataframe, 0% coverage
            if data.empty or data.lat.size == 0 or data.long.size == 0:
                return 0
            # Otherwise, calculate coverage, assuming rectangular region
            # in mercator projection
            # Create a polygon to calculate overlap region from
            data_boundary = Boundary(
                [data.lat.min(), data.lat.max()], [data.long.min(), data.long.max()]
            )
            data_polygon = data_boundary.to_polygon()
            bounds_polygon = bounds.to_polygon()

            # Get fraction of bounds covered by data
            overlap_area = data_polygon.intersection(bounds_polygon).area
            total_area = bounds_polygon.area

            return cast("float", overlap_area / total_area)

        def calculate_coverage_from_xr(bounds: Boundary, data: xr.Dataset) -> float:
            # Remove all NaN columns/rows
            data = data.dropna(dim="lat", how="all")
            data = data.dropna(dim="long", how="all")
            # If no valid coordinates within data range, 0% coverage
            if data.lat.size == 0 or data.long.size == 0:
                return 0
            # Otherwise, calculate coverage, assuming rectangular region
            # in mercator projection
            # Create a polygon to calculate overlap region from
            data_boundary = Boundary(
                [data.lat.min().item(), data.lat.max().item()],
                [data.long.min().item(), data.long.max().item()],
            )
            data_polygon = data_boundary.to_polygon()
            bounds_polygon = bounds.to_polygon()

            # Get fraction of bounds covered by data
            overlap_area = data_polygon.intersection(bounds_polygon).area
            total_area = bounds_polygon.area

            return cast("float", overlap_area / total_area)

        # Use self.data if not no explicit dataset specified
        if data is None:
            data = self.data
        # Calculate data coverage fraction
        if isinstance(self.data, pd.core.frame.DataFrame):
            return calculate_coverage_from_df(bounds, data)
        if isinstance(self.data, xr.core.dataset.Dataset):
            return calculate_coverage_from_xr(bounds, data)
        raise TypeError(f"Unsupported data type: {type(self.data)}")

    def trim_datapoints(
        self, bounds: Boundary, data: xr.Dataset | pd.DataFrame | None = None
    ) -> xr.Dataset | pd.DataFrame:
        """
        Trims datapoints from self.data within boundary defined by 'bounds'.
        self.data can be pd.DataFrame or xr.Dataset

        Args:
            bounds (Boundary): Limits of lat/long/time to select data from

        Returns:
            pd.DataFrame or xr.Dataset:
                Trimmed dataset in same format as self.data
        """

        def trim_datapoints_from_df(data: pd.DataFrame, bounds: Boundary) -> pd.DataFrame:
            """
            Extracts datapoints from a pd.DataFrame

            Args:
                data (pd.DataFrame): Datapoints in dataframe
                bounds (Boundary):
                    Maximum extent of datapoints to include.
                    Will be cut to extent of spatial boundary
                    (and temporal if data includes time)

            Returns:
                pd.DataFrame:
                    Trimmed dataset inclusive of spatial upper bound, and
                    exclusive of spatial lower bound. Inclusive of both
                    upper and lower time bounds
            """
            # Convert bounds to numpy arrays for faster comparison
            lat_min = bounds.get_lat_min()
            lat_max = bounds.get_lat_max()
            long_min = bounds.get_long_min()
            long_max = bounds.get_long_max()

            # Use .values to get numpy arrays
            try:
                lat_vals = data["lat"].values
                long_vals = data["long"].values

                # Build spatial mask using numpy
                if long_min < long_max:
                    spatial_mask = (
                        (lat_vals > lat_min)
                        & (lat_vals <= lat_max)
                        & (long_vals > long_min)
                        & (long_vals <= long_max)
                    )
                else:
                    spatial_mask = (
                        (lat_vals > lat_min)
                        & (lat_vals <= lat_max)
                        & ((long_vals <= long_min) | (long_vals > long_max))
                    )

                # Filter using numpy mask first
                if "time" in data.columns:
                    # For time, convert to datetime if needed and use vectorized comparison
                    spatially_filtered = data.iloc[spatial_mask]

                    # Check if time column is already datetime, if not convert
                    if spatially_filtered["time"].dtype == "object":
                        # Avoid slow object array comparisons by converting to datetime
                        try:
                            time_series = pd.to_datetime(
                                spatially_filtered["time"], errors="coerce"
                            )
                            time_min = pd.to_datetime(bounds.get_time_min())
                            time_max = pd.to_datetime(bounds.get_time_max())
                            time_mask = (time_series >= time_min) & (time_series <= time_max)
                            return spatially_filtered.iloc[time_mask.values]
                        except Exception:
                            # If conversion fails, fall back to original comparison
                            time_mask = (spatially_filtered["time"] >= bounds.get_time_min()) & (
                                spatially_filtered["time"] <= bounds.get_time_max()
                            )
                            return spatially_filtered.loc[time_mask]
                    else:
                        # Already datetime, use direct comparison
                        time_mask = (spatially_filtered["time"] >= bounds.get_time_min()) & (
                            spatially_filtered["time"] <= bounds.get_time_max()
                        )
                        return spatially_filtered.loc[time_mask]
                else:
                    return data.iloc[spatial_mask]

            except Exception as e:
                # Fallback to original boolean masking if query fails
                logger.debug(
                    f"\tDataFrame query optimization failed ({type(e).__name__}), using fallback"
                )
                if bounds.get_long_min() < bounds.get_long_max():
                    mask = (
                        (data["lat"] > bounds.get_lat_min())
                        & (data["lat"] <= bounds.get_lat_max())
                        & (data["long"] > bounds.get_long_min())
                        & (data["long"] <= bounds.get_long_max())
                    )
                else:
                    mask = (
                        (data["lat"] > bounds.get_lat_min())
                        & (data["lat"] <= bounds.get_lat_max())
                        & (data["long"] <= bounds.get_long_min())
                        & (data["long"] > bounds.get_long_max())
                    )
                # Mask with time if time column exists
                if "time" in data.columns:
                    mask &= (data["time"] >= bounds.get_time_min()) & (
                        data["time"] <= bounds.get_time_max()
                    )

                # Return column of data from within bounds
                return data.loc[mask]

        def trim_datapoints_from_xr(data: xr.Dataset, bounds: Boundary) -> xr.Dataset:
            """
            Extracts datapoints from a xr.Dataset

            Args:
                data (xr.Dataset): Datapoints in dataframe
                bounds (Boundary):
                    Maximum extent of datapoints to include.
                    Will be cut to extent of spatial boundary
                    (and temporal if data includes time)

            Returns:
                xr.Dataset:
                    Trimmed dataset inclusive of spatial upper bound, and
                    exclusive of spatial lower bound. Inclusive of both
                    upper and lower time bounds
            """
            # Optimized integer-based indexing
            try:
                # Get coordinate values as numpy arrays
                lat_vals = data.lat.values
                long_vals = data.long.values

                lat_min_idx = np.searchsorted(lat_vals, bounds.get_lat_min(), side="right")
                lat_max_idx = np.searchsorted(lat_vals, bounds.get_lat_max(), side="right")

                if bounds.get_long_min() < bounds.get_long_max():
                    long_min_idx = np.searchsorted(long_vals, bounds.get_long_min(), side="right")
                    long_max_idx = np.searchsorted(long_vals, bounds.get_long_max(), side="right")

                    # Use integer-based indexing
                    data = data.isel(
                        lat=slice(lat_min_idx, lat_max_idx),
                        long=slice(long_min_idx, long_max_idx),
                    )
                else:
                    # Fallback to coordinate-based selection
                    data = data.sel(lat=slice(bounds.get_lat_min(), bounds.get_lat_max()))
                    data_lhs = data.sel(long=slice(-180, bounds.get_long_max()))
                    data_rhs = data.sel(long=slice(bounds.get_long_min(), 180))
                    data = xr.concat([data_lhs, data_rhs], "long")

            except (ValueError, KeyError, AttributeError):
                # Fallback to standard coordinate-based selection if optimisation fails
                data = data.sel(lat=slice(bounds.get_lat_min(), bounds.get_lat_max()))
                if bounds.get_long_min() < bounds.get_long_max():
                    data = data.sel(long=slice(bounds.get_long_min(), bounds.get_long_max()))
                else:
                    data_lhs = data.sel(long=slice(-180, bounds.get_long_max()))
                    data_rhs = data.sel(long=slice(bounds.get_long_min(), 180))
                    data = xr.concat([data_lhs, data_rhs], "long")

            # Select data region within temporal bounds if time exists as a coordinate
            if "time" in data.coords:
                data = data.sel(time=slice(bounds.get_time_min(), bounds.get_time_max()))

            # Trim off any data on the min boundary to be consistent with df
            if len(data.lat) > 0 and bounds.get_lat_min() in data.lat.values:
                data = data.where(data.lat != bounds.get_lat_min(), drop=True)
            if len(data.long) > 0 and bounds.get_long_min() in data.long.values:
                data = data.where(data.long != bounds.get_long_min(), drop=True)

            # Return column of data from within bounds
            return data

        # If no specific data passed in, default to entire dataset
        if data is None:
            data = self.data

        if isinstance(data, pd.core.frame.DataFrame):
            return trim_datapoints_from_df(data, bounds)
        if isinstance(data, xr.core.dataset.Dataset):
            return trim_datapoints_from_xr(data, bounds)
        raise TypeError(f"Unsupported data type: {type(data)}")

    def get_value(  # type: ignore[override]
        self,
        bounds: Boundary,
        data: xr.Dataset | pd.DataFrame | None = None,
        agg_type: str | None = None,
        skipna: bool = True,
    ) -> dict[str, float]:
        """
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
        """

        def get_value_from_df(
            dps: pd.Series, bounds: Boundary, agg_type: str, skipna: bool
        ) -> float:
            """
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
            """
            # Skip NaN's if desired
            if skipna:
                dps = dps.dropna()

            logger.debug(
                f"\t{len(dps)} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'"
            )
            # If want the number of datapoints
            if agg_type == "COUNT":
                return len(dps)
            # If no data
            if len(dps) == 0 or np.isnan(dps).all():
                return np.nan
            # Return float of aggregated value
            if agg_type == "MIN":
                return float(dps.min(skipna=skipna))
            if agg_type == "MAX":
                return float(dps.max(skipna=skipna))
            if agg_type == "MEAN":
                return float(dps.mean(skipna=skipna))
            if agg_type == "MEDIAN":
                return float(dps.median(skipna=skipna))
            if agg_type == "STD":
                return float(dps.std(skipna=skipna))
            # If aggregation_type not available
            raise ValueError(f"Unknown aggregation type {agg_type}")

        def get_value_from_xr(
            dps: xr.DataArray, bounds: Boundary, agg_type: str, skipna: bool
        ) -> float:
            """
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
                np.float64: Aggregated value
            """
            # Extract values to be worked on by numpy functions
            dps = dps.values  # type: ignore[assignment]
            logger.debug(
                f"\t{len(dps)} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'"
            )
            # If want the number of datapoints
            if agg_type == "COUNT":
                return float(dps.size)
            # If no data
            if dps.size == 0 or np.isnan(dps).all():
                return np.nan
            # Return float of aggregated value
            if agg_type == "MIN":
                if skipna:
                    return float(np.nanmin(dps))
                return float(np.min(dps))
            if agg_type == "MAX":
                if skipna:
                    return float(np.nanmax(dps))
                return float(np.max(dps))
            if agg_type == "MEAN":
                if skipna:
                    return float(np.nanmean(dps))
                return float(np.mean(dps))
            if agg_type == "MEDIAN":
                if skipna:
                    return float(np.nanmedian(dps))
                return float(np.median(dps))
            if agg_type == "STD":
                if skipna:
                    return float(np.nanstd(dps))
                return float(np.std(dps))
            if agg_type == "RMSE":
                if skipna:
                    return float(np.sqrt(np.nanmean((dps - np.nanmean(dps)) ** 2)))
                return float(np.sqrt(np.mean((dps - np.mean(dps)) ** 2)))
            # If aggregation_type not available
            raise ValueError(f"Unknown aggregation type {agg_type}")

        # Set to params if no specific aggregate type specified
        if agg_type is None:
            agg_type = self.aggregate_type

        # Limit data series to just the data, excluding coords/index
        dps = self.trim_datapoints(bounds, data=data)[self.data_name]

        if isinstance(self.data, pd.core.frame.DataFrame):
            value = get_value_from_df(dps, bounds, agg_type, skipna)
        elif isinstance(self.data, xr.core.dataset.Dataset):
            value = get_value_from_xr(dps, bounds, agg_type, skipna)

        # Cast to regular float before returning so can be saved in JSON later
        if self.data_name is None:
            raise ValueError("data_name is None")
        return {self.data_name: float(value)}

    def get_hom_condition(
        self,
        bounds: Boundary,
        splitting_conds: dict[str, Any],
        data: xr.Dataset | pd.DataFrame | None = None,
    ) -> str:
        """
        Retrieves homogeneity condition of data within
        boundary.

        Args:
            bounds (Boundary): Boundary object with limits of datarange to analyse
            splitting_conds (dict): Containing the following keys: \n
                'threshold':
                    `(float)` The threshold at which data points of
                    type 'value' within this CellBox are checked to be either
                    above or below
                'upper_bound':
                    `(float)` The lowerbound of acceptable percentage
                    of data_points of type value within this boundary that are
                    above 'threshold'
                'lower_bound':
                    `(float)` The upperbound of acceptable percentage
                    of data_points of type value within this boundary that are
                    above 'threshold'
                'split_lock':
                    `(bool)` If true, a cellbox will not be split by other
                    splitting conditions if it is deemed homogeneous. default = False.

        Returns:
            str:
                The homogeniety condtion returned is of the form: \n
                'CLR' = the proportion of data points within this cellbox over a
                given threshold is lower than the lowerbound \n
                'HOM' = the proportion of data points within this cellbox over a
                given threshold is higher than the upperbound \n
                'MIN' = the cellbox contains less than a minimum number of
                data points \n
                'HET' = the proportion of data points within this cellbox over a
                given threshold if between the upper and lower bound

        """

        def get_hom_condition_from_df(dps: pd.Series, splitting_conds: dict[str, Any]) -> str:
            """
            Determined homogeneity condition from pd.Series.

            Args:
                dps (pd.Series):
                    Datapoints to determine homogeneity condition from
                splitting_conds (dict):
                    Key/Value pairs for threshold, upper_bound and lower_bound.
                    More details in get_hom_condition() docstring

            Returns:
                str:
                    Homogeneity condition of dataset, as described in
                    get_hom_condition() docstring
            """
            # If not enough datapoints
            if len(dps) < self.min_dp:
                hom_type = "CLR"
            # Otherwise, extract the homogeneity condition
            else:
                # Determine fraction of datapoints over threshold value
                num_over_threshold = dps[dps > splitting_conds["threshold"]]
                num_non_nan = np.count_nonzero(~np.isnan(dps))
                if num_non_nan > 0:
                    frac_over_threshold = num_over_threshold.shape[0] / num_non_nan
                else:
                    frac_over_threshold = 0

                # Return homogeneity condition
                if frac_over_threshold <= splitting_conds["lower_bound"]:
                    hom_type = "CLR"
                elif frac_over_threshold >= splitting_conds["upper_bound"]:
                    hom_type = "HOM" if splitting_conds["split_lock"] is True else "CLR"
                else:
                    hom_type = "HET"

            logger.debug(
                f"\thom_condition for attribute: '{self.data_name}' in bounds:'{bounds}' returned '{hom_type}'"
            )
            return hom_type

        def get_hom_condition_from_xr(dps: xr.DataArray, splitting_conds: dict[str, Any]) -> str:
            """
            Determined homogeneity condition from xr.DataArray.

            Args:
                dps (xr.DataArray):
                    Datapoints to determine homogeneity condition from
                splitting_conds (dict):
                    Key/Value pairs for threshold, upper_bound and lower_bound.
                    More details in get_hom_condition() docstring

            Returns:
                str:
                    Homogeneity condition of dataset, as described in
                    get_hom_condition() docstring
            """
            if dps.size < self.min_dp:
                hom_type = "CLR"
                logger.debug(
                    f"\t{dps.size} datapoints found for attribute '{self.data_name}' within bounds '{bounds}'"
                )
            else:
                # Determine fraction of datapoints over threshold value
                num_over_threshold = np.count_nonzero(dps > splitting_conds["threshold"])
                num_non_nan = np.count_nonzero(~np.isnan(dps))
                frac_over_threshold = num_over_threshold / num_non_nan if num_non_nan > 0 else 0
                # Return homogeneity condition
                if frac_over_threshold <= splitting_conds["lower_bound"]:
                    hom_type = "CLR"
                elif frac_over_threshold >= splitting_conds["upper_bound"]:
                    if splitting_conds["split_lock"] is True:
                        hom_type = "HOM"
                        logger.debug(
                            f"\tSplitting locked by attribute: '{self.data_name}' in bounds:'{bounds}'"
                        )
                    else:
                        hom_type = "CLR"
                else:
                    hom_type = "HET"

            logger.debug(
                f"\thom_condition for attribute: '{self.data_name}' in bounds:'{bounds}' returned '{hom_type}'"
            )

            return hom_type

        # Set default values for splitting_conds if not provided
        if "split_lock" not in splitting_conds:
            splitting_conds["split_lock"] = False
        dps = self.trim_datapoints(bounds)[self.data_name] if data is None else data[self.data_name]

        # Retrieve datapoints to analyse
        if isinstance(dps, pd.core.series.Series):
            return get_hom_condition_from_df(dps, splitting_conds)
        if isinstance(dps, xr.core.dataarray.DataArray):
            return get_hom_condition_from_xr(dps, splitting_conds)
        raise TypeError(f"Unknown type {type(dps)}")

    def reproject(
        self,
        in_proj: str = "EPSG:4326",
        out_proj: str = "EPSG:4326",
        x_col: str = "lat",
        y_col: str = "long",
    ) -> xr.Dataset | pd.DataFrame:
        """
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
        """

        def reproject_df(
            data: pd.DataFrame, in_proj: str, out_proj: str, x_col: str, y_col: str
        ) -> pd.DataFrame:
            """
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
            """
            # Do the reprojection
            x, y = Transformer.from_crs(CRS(in_proj), CRS(out_proj), always_xy=True).transform(
                data[x_col].to_numpy(), data[y_col].to_numpy()
            )
            # Replace columns with reprojected columns called 'lat'/'long'
            if x_col != "long":
                data = data.drop(x_col, axis=1)
            if y_col != "lat":
                data = data.drop(y_col, axis=1)
            data["lat"] = y
            data["long"] = x

            return data

        def reproject_xr(
            data: xr.Dataset,
            in_proj: str,
            out_proj: str,
            x_col: str,
            y_col: str,
            fast: bool = False,
        ) -> xr.Dataset:
            """
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
            """
            if fast:
                # If want fast results (uses interpolation)
                max_size = sum(data.sizes.values())
                # Set data CRS
                data = data.rio.write_crs(in_proj)
                # Reproject
                data = data.rio.reproject(
                    out_proj,
                    resampling=Resampling.bilinear,
                    shape=((max_size, max_size)),
                    nodata=np.nan,
                )
                # Rename coordinates
                data = data.rename({x_col: "long", y_col: "lat"})
                # Reorder coords in case they are wrong
                return data.sortby("lat", ascending=True).sortby("long", ascending=True)
            # If want accurate results
            df = data.to_dataframe().reset_index().dropna()
            return reproject_df(df, in_proj, out_proj, x_col, y_col)  # type: ignore[no-any-return]

        # If no reprojection to do
        if in_proj == out_proj:
            logger.debug("\tself.reproject() called but don't need to")
            return self.data
        logger.info(f"\tReprojecting data from {in_proj} to {out_proj}")
        # Choose appropriate method of reprojection based on data type
        if isinstance(self.data, pd.core.frame.DataFrame):
            return reproject_df(self.data, in_proj, out_proj, x_col, y_col)
        if isinstance(self.data, xr.core.dataset.Dataset):
            return reproject_xr(
                self.data, in_proj, out_proj, x_col, y_col, fast=self.fast_reprojection
            )
        raise TypeError(f"Unsupported data type: {type(self.data)}")

    def downsample(self, agg_type: str | None = None) -> xr.Dataset | pd.DataFrame:
        """
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
        """

        def downsample_xr(data: xr.Dataset, ds: list[int], agg_type: str) -> xr.Dataset:
            """
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
            """
            if agg_type == "MIN":
                # Returns min of bin
                data = data.coarsen(lat=ds[1], boundary="pad").min()  # type: ignore[attr-defined]
                data = data.coarsen(long=ds[0], boundary="pad").min()  # type: ignore[attr-defined]
            elif agg_type == "MAX":
                # Returns max of bin
                data = data.coarsen(lat=ds[1], boundary="pad").max()  # type: ignore[attr-defined]
                data = data.coarsen(long=ds[0], boundary="pad").max()  # type: ignore[attr-defined]
            elif agg_type == "MEAN":
                # Returns mean of bin
                data = data.coarsen(lat=ds[1], boundary="pad").mean()  # type: ignore[attr-defined]
                data = data.coarsen(long=ds[0], boundary="pad").mean()  # type: ignore[attr-defined]
            elif agg_type == "MEDIAN":
                # Returns median of bin
                data = data.coarsen(lat=ds[1], boundary="pad").median()  # type: ignore[attr-defined]
                data = data.coarsen(long=ds[0], boundary="pad").median()  # type: ignore[attr-defined]
            elif agg_type == "STD":
                # Returns std_dev of range
                data = data.coarsen(lat=ds[1], boundary="pad").std()  # type: ignore[attr-defined]
                data = data.coarsen(long=ds[0], boundary="pad").std()  # type: ignore[attr-defined]
            elif agg_type == "COUNT":
                # Returns every first element in bin
                data = data.thin(lat=ds[1])
                data = data.thin(long=ds[0])
            return data

        def downsample_df(data: pd.DataFrame, _ds: list[int], _agg_type: str) -> pd.DataFrame:
            """
            Downsample pandas dataframe
            Not implemented as it just adds to processing time,
            defeating the purpose
            """
            logger.warning(
                "\tDownsampling called on pd.DataFrame! Downsampling a df"
                "too computationally expensive, returning original df"
            )
            return data

        # Set to params if no specific aggregate type specified
        if agg_type is None:
            agg_type = self.aggregate_type

        # If no downsampling
        if list(self.downsample_factors) == [1, 1]:
            logger.debug("\tself.downsample() called but don't have to")
            return self.data
        logger.info(f"\tDownsampling data by {self.downsample_factors}")
        # Otherwise, downsample appropriately
        if isinstance(self.data, pd.core.frame.DataFrame):
            return downsample_df(self.data, self.downsample_factors, agg_type)
        if isinstance(self.data, xr.core.dataset.Dataset):
            return downsample_xr(self.data, self.downsample_factors, agg_type)
        raise TypeError(f"Unsupported data type: {type(self.data)}")

    def get_data_col_name(self) -> str:
        """
        Retrieve name of data column (for pd.DataFrame), or variable
        (for xr.Dataset). Used for when data_name not defined in params.

        Returns:
            str:
                Name of data column

        Raises:
            ValueError:
                If multiple possible data columns found, can't retrieve data
                name
        """

        def get_data_name_from_df(data: pd.DataFrame) -> str:
            """
            Filters out standard columns to extract only data column's name
            from pd.DataFrame

            Args:
                data (pd.DataFrame):
                    DataFrame with only 'lat', 'long', 'time' and data_name

            Returns:
                str: Data name extracted from column head
            """
            # Store name of data column for future reference
            columns = data.columns
            # Filter out lat, long, time columns leaves us with data column name
            filtered_cols = filter(lambda col: col not in ["lat", "long", "time"], columns)
            name = list(filtered_cols)
            if len(name) != 1:
                raise ValueError(
                    f"More than 1 data column detected, cannot retrieve data \
                    name! Found columns: {','.join(name)}"
                )
            return str(name[0])

        def get_data_name_from_xr(data: xr.Dataset) -> str:
            """
            Extracts variable name directly from xr.Dataset metadata

            Args:
                data (xr.Dataset):
                    Dataset with only one data variable

            Returns:
                str: Data name extracted from xarray metadata
            """
            # Extract data variables from xr.Dataset
            name = list(data.keys())
            # Ensure there's only 1 data column to read name from
            if len(name) != 1:
                raise ValueError(
                    f"More than 1 data column detected, cannot retrieve data \
                    name! Found columns: {','.join(name)}"  # type: ignore[arg-type]
                )
            return str(name[0])

        logger.debug(f"\tRetrieving data name from {type(self.data)}")
        # Choose method of extraction based on data type
        if isinstance(self.data, pd.core.frame.DataFrame):
            return get_data_name_from_df(self.data)
        if isinstance(self.data, xr.core.dataset.Dataset):
            return get_data_name_from_xr(self.data)
        raise TypeError(f"Unsupported data type: {type(self.data)}")

    def set_data_col_name(self, new_name: str) -> xr.Dataset | pd.DataFrame:
        """
        Sets name of data column/data variable

        Args:
            name (str): Name to replace currently stored name with

        Returns:
            xr.Dataset or pd.DataFrame:
                Data with variable name changed
        """

        def set_name_df(data: pd.DataFrame, old_name: str, new_name: str) -> pd.DataFrame:
            """
            Renames data column in pandas dataframe

            Args:
                data (pd.DataFrame):
                    DataFrame that has old_name as one of column names
                old_name (str):
                    Old column name to replace
                new_name (str):
                    New column name after replacing

            Returns:
                pd.DataFrame:
                    DataFrame with old_name replaced by new_name
            """
            # Rename data column to new name
            return data.rename(columns={old_name: new_name})

        def set_name_xr(data: xr.Dataset, old_name: str, new_name: str) -> xr.Dataset:
            """
            Renames data variable in xarray dataset

            Args:
                data (xr.Dataset):
                    Dataset that has old_name as data variable name
                old_name (str):
                    Old data_variable name to replace
                new_name (str):
                    New data_variable name after replacing

            Returns:
                xr.Dataset:
                    Dataset with old_name replaced by new_name
            """
            # Rename data variable to new name
            return data.rename({old_name: new_name})

        old_name = self.get_data_col_name()
        if old_name != new_name:
            logger.info(f"\tChanging data name from {old_name} to {new_name}")
        # Change data name depending on data type
        if isinstance(self.data, pd.core.frame.DataFrame):
            return set_name_df(self.data, old_name, new_name)
        if isinstance(self.data, xr.core.dataset.Dataset):
            return set_name_xr(self.data, old_name, new_name)
        raise TypeError(f"Unsupported data type: {type(self.data)}")
