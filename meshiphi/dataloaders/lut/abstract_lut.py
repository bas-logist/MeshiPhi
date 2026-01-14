from __future__ import annotations

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd
from shapely.ops import unary_union
from shapely.strtree import STRtree

from meshiphi.dataloaders.dataloader_interface import DataLoaderInterface

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary

logger = logging.getLogger(__name__)


class LutDataLoader(DataLoaderInterface):  # type: ignore[misc]
    """
    Abstract class for all LookUp Table Datasets.
    """

    # Type hints for dynamically set attributes (set via setattr in __init__)
    files: list[str] | None
    data_name: str | None
    dataloader_name: str
    value: bool | float | None = None  # LUT-specific: value to assign to shapes
    aggregate_type: str = "MEAN"  # Aggregation type for LUT data

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
            self.data (gpd.DataFrame):
                Data stored by dataloader to use when called upon by the mesh.
                Must be saved in mercator projection (EPSG:4326), with
                columns 'geometry' and data_name.
            self.data_name (str):
                Name of scalar variable. Must be the column name in the dataframe

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

        # Get data name from column name if not set in params
        if self.data_name is None:
            logger.debug("\tSetting self.data_name from column name")
            self.data_name = self.get_data_col_name()
        # or if set in params, set col name to data name
        else:
            logger.debug(f"\tSetting data column name to {self.data_name}")
            self.data = self.set_data_col_name(self.data_name)

        # Verify that all geometries are acceptable inputs
        self.data = self.verify_data()

        # Calculate fraction of boundary that data covers
        data_coverage = self.calculate_coverage(bounds)
        logger.info(
            "\tMercator data range (roughly) covers "
            + f"{np.round(data_coverage * 100, 0).astype(int)}% "
            + "of initial boundary"
        )
        # If there's 0 datapoints in the initial boundary, raise ValueError
        if data_coverage == 0:
            logger.error("\tDataloader has no data in initial region!")
            raise ValueError(
                f"Dataloader {params['dataloader_name']}"
                + " contains no data within initial region!"
            )
        # Cut dataset down to initial boundary
        logger.info(
            f"\tTrimming data to initial boundary: {(bounds.get_lat_min(), bounds.get_long_min())} to {(bounds.get_lat_max(), bounds.get_long_max())}"
        )

        self.data = self.trim_datapoints(bounds)

    @abstractmethod
    def import_data(self, bounds: Boundary) -> Any:  # gpd.GeoDataFrame
        """
        User defined method for importing data from files, or even generating
        data from scratch

        Returns:
            pd.DataFrame:
                Coordinates and data being imported from file \n
                if pd.DataFrame,
                    - Must have columns 'geometry' and data_name
                    - Must have single data column

        """

    def add_default_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Set default values for all LUT dataloaders. This function should be
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

        if "aggregate_type" not in params:
            params["aggregate_type"] = "MEAN"

        return params

    def verify_data(self, data: Any = None) -> pd.DataFrame:
        """
        Verifies that all geometries read in are Polygons or MultiPolygons
        If MultiPolygon, then split out into multiple Polygons

        Args:
            data (pd.DataFrame, optional):
                DataFrame with at least columns 'geometry' and a variable.
                Defaults to dataloader's data attribute.

        Raises:
            ValueError: If read in a geometry that is not Polygon or MultiPolygon
        """

        if data is None:
            data = self.data

        # List of rows to include in cleaned dataframe
        new_data = []
        # For each entry
        for index, row in data.iterrows():
            # Add row if Polygon
            if row.geometry.geom_type == "Polygon":
                new_data.append(data.loc[[index]])
            # Split out multipolygons to single polygons, and add rows
            elif row.geometry.geom_type == "MultiPolygon":
                polygons = list(row.geometry.geoms)
                new_df = pd.concat([data.loc[[index]]] * len(polygons))
                new_df["geometry"] = polygons
                new_data.append(new_df)
            # Otherwise, geometry not usable
            else:
                raise ValueError(
                    f"{row.geometry.geom_type} not acceptable geometry type."
                    + " Must be a Polygon or MultiPolygon!"
                )
        return pd.concat(new_data, ignore_index=True)

    def calculate_coverage(self, bounds: Boundary, data: Any = None) -> float:
        """
        Calculates percentage of boundary covered by dataset

        Args:
            bounds (Boundary):
                Boundary being compared against
            data (pd.DataFrame):
                Dataset with shapely polygons in 'geometry' column
                Defaults to objects internal dataset.

        Returns:
            float:
                Decimal fraction of boundary covered by the dataset
        """
        if data is None:
            data = self.data
        # Extract just polygons as a series if it's a dataframe
        if isinstance(data, pd.core.frame.DataFrame):
            data = data["geometry"]
        # No coverage if no data
        if data.empty:
            return 0
        # Calculate coverage fraction
        bounds_polygon = bounds.to_polygon()
        # Extract out polygons, add to multipolygon
        data_polygon = unary_union(data.tolist())

        overlap_area = data_polygon.intersection(bounds_polygon).area
        total_area = bounds_polygon.area

        return cast("float", overlap_area / total_area)

    def trim_datapoints(self, bounds: Boundary, data: Any = None) -> pd.DataFrame:
        """
        Trims datapoints from self.data within boundary defined by 'bounds'.
        self.data can be pd.DataFrame or xr.Dataset

        Args:
            bounds (Boundary): Limits of lat/long/time to select data from

        Returns:
            pd.DataFrame:
                Trimmed dataset in same format as self.data
        """
        if data is None:
            data = self.data
        # Limit time to boundary
        if "time" in data.index.names:
            data = data.loc[bounds.get_time_min() : bounds.get_time_max()]

        # Find intersection of each polygon to the boundary
        bounds_polygon = bounds.to_polygon()
        lut_polys = STRtree(list(data["geometry"]))
        intersections = lut_polys.query(bounds_polygon, predicate="intersects").tolist()
        # Return only rows intersecting with cellbox boundary
        return data.iloc[intersections]

    def get_value(
        self, bounds: Boundary, agg_type: str | None = None, skipna: bool = False, data: Any = None
    ) -> dict[str, float]:
        """
        Retrieve aggregated value from within bounds

        Args:
            aggregation_type (str): Method of aggregation of datapoints within
                bounds. Can be upper or lower case.
                Accepts 'MIN', 'MAX', 'MEAN', 'MEDIAN', 'STD', 'COUNT'
            bounds (Boundary): Boundary object with limits of lat/long
            skipna (bool): Defines whether to propogate NaN's or not
                Default = False (includes NaN's)

        Returns:
            dict:
                {variable (str): aggregated_value (float)}
                Aggregated value within bounds following aggregation_type

        Raises:
            ValueError: aggregation type not in list of available methods
        """
        polygons = self.trim_datapoints(bounds, data=data)
        logger.debug(
            f"\t{len(polygons)} polygons found for attribute "
            + f"'{self.data_name}' within bounds '{bounds}'"
        )

        ret_val = np.nan

        if agg_type is None:
            agg_type = self.aggregate_type
        # If want the number of datapoints
        if agg_type == "COUNT":
            ret_val = len(polygons)
        # If no data
        elif len(polygons) == 0:
            ret_val = np.nan
        # Return float of aggregated value
        elif agg_type == "MIN":
            ret_val = polygons[self.data_name].min(skipna=skipna)
        elif agg_type == "MAX":
            ret_val = polygons[self.data_name].max(skipna=skipna)

        elif agg_type in ["MEAN", "MEDIAN", "STD"]:
            # Skipna not easily parsed to remaining calculations, so force it here
            if skipna:
                polygons = polygons.dropna()
            # Mean, median, and std dev need to be weighted by size of polygons
            polygons = polygons.assign(
                weights=lambda row: self.calculate_coverage(bounds, row["geometry"])
            )
            if agg_type == "MEAN":
                ret_val = np.average(polygons[self.data_name], weights=polygons["weights"])

            elif agg_type == "MEDIAN":
                # Chunk by cumulative weight
                polygons["cumulative_weights"] = polygons["weights"].cumsum(skipna=skipna)
                # Find middle of cumulative weight
                total_weight = polygons["weights"].sum(skipna=skipna)
                median_pos = total_weight / 2
                # Extract top half and return lowest value (value closest to halfway)
                top_half = polygons.loc[polygons["cumulative_weights"] >= median_pos]
                ret_val = top_half.iloc[0]

            elif agg_type == "STD":
                # Calculate std dev manually to account for weight
                average = np.average(polygons[self.data_name], weights=polygons["weights"])
                variance = np.average(
                    np.power(polygons[self.data_name] - average, 2),
                    weights=polygons["weights"],
                )
                ret_val = np.sqrt(variance)
        # If aggregation_type not available
        else:
            raise ValueError(f"Unknown aggregation type {agg_type}")

        # Convert numpy bool to python bool for JSON serialisation
        if isinstance(ret_val, np.bool_):
            ret_val = bool(ret_val)

        if self.data_name is None:
            raise ValueError("data_name is None")
        return {self.data_name: ret_val}

    def get_hom_condition(
        self, bounds: Boundary, splitting_conds: dict[str, Any], data: Any = None
    ) -> str:
        """
        Retrieves homogeneity condition of data within
        boundary.

        Args:
            bounds (Boundary): Boundary object with limits of datarange to analyse
            splitting_conds (dict): Containing the following keys: \n
                'boundary':
                    `(boolean)` True if user wants to split when polygon boundary
                    goes through bounds

        Returns:
            str:
                The homogeniety condtion returned is of the form: \n
                'CLR' = the boundary is completely contained within the LUT
                regions, no need to split\n
                'MIN' = the boundary contains no LUT data, can't split \n
                'HET' = the boundary contains an edge within the LUT data,
                should split

        """
        bounds_polygon = bounds.to_polygon()
        # Extract polygons that overlap the boundary
        polygons = self.trim_datapoints(bounds, data=data)["geometry"].tolist()

        hom_type = "CLR"
        # If there's no polygon that overlaps with bounds
        if not any(polygon.intersects(bounds_polygon) for polygon in polygons):
            if splitting_conds["split_lock"] is True:
                hom_type = "HOM"
        # If we want to split on the boundary
        elif splitting_conds["boundary"] and any(
            p.boundary.intersects(bounds_polygon) for p in polygons
        ):
            hom_type = "HET"

        # Otherwise no boundaries intersected bounds
        return hom_type

    def reproject(self) -> None:
        """
        Reprojection not supported by LookUpTable Dataloader
        """
        logger.warning("Reprojection not supported by LookUpTable Dataloader")

    def downsample(self) -> None:
        """
        Downsampling not supported by LookUpTable Dataloader
        """
        logger.warning("Downsampling not supported by LookUpTable Dataloader")

    def get_data_col_name(self) -> str:
        """
        Retrieve name of data column.
        Used for when data_name not defined in params.

        Returns:
            str:
                Name of data column

        Raises:
            AssertionError:
                If multiple possible data columns found, can't retrieve data
                name
        """

        logger.debug(f"\tRetrieving data name from {type(self.data)}")

        unique_cols = list(set(self.data.columns) - {"time", "geometry"})

        assert len(unique_cols) == 1, f"Expected only one data column! Instead, found {unique_cols}"

        return str(unique_cols[0])

    def set_data_col_name(self, new_name: str) -> pd.DataFrame:
        """
        Sets name of data column/data variable

        Args:
            name (str): Name to replace currently stored name with

        Returns:
            pd.DataFrame:
                Data with variable name changed
        """

        old_name = self.get_data_col_name()
        if old_name != new_name:
            logger.info(f"\tChanging data name from {old_name} to {new_name}")
            return self.data.rename({old_name: new_name})
        logger.info(f"\tData is already labelled '{new_name}'")
        return self.data
