"""
Outlined in this section we will discuss the usage of the CellBox functionality of the meshiphi package.
In this series of class distributions we house our discrete representation of input data. In each CellBox,
we represent a way of accessing the information governing our numerical world,
this includes and is not limited to: Ocean Currents, Sea Ice Concentration and Bathymetric depth.\n


    Example:\n
    An example of running this code can be executed by running the following in a ipython/Jupyter Notebook:: \n

            from meshiphi.mesh_generation.cellbox import cellbox \n
            .... \n

    Note:\n
        CellBoxes are intended to be constructed by and used within a Mesh object.
          The methods provided are to extract information for CellBoxes contained within a Mesh. \n

"""

from __future__ import annotations

import logging
from typing import Any, cast

import numpy as np
from shapely.geometry import Point

from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.utils import longitude_domain

logger = logging.getLogger(__name__)


class CellBox:
    """
    A CellBox represnts a geo-spatial/temporal boundary that enables projecting to information within.
    Information about any given value of a CellBox is calculated from aggregating all data points of within those bounds.
    CellBoxes may  be split into smaller CellBoxes and the data points within distributed  between the newly created
    CellBoxes so as to construct a non-uniform mesh of CellBoxes, such as within a Mesh.\n

    Attributes:
        Bounds (Boundary): object that contains the latitude and logtitute range and the time range \n
        id (int):  the id of the cellbox \n

    """

    def __init__(self, bounds: Boundary, id: Any) -> None:
        """

        Args:
            bounds(Boundary): encapsulates latitude, longtitude and time range of the CellBox\n
            id (int):  the id of the cellbox \n
        """
        # Box information relative to bottom left
        self.bounds = bounds
        self.parent: CellBox | None = None
        self.minimum_datapoints = 10
        self.split_depth = 0
        self.data_source: list[Metadata] | None = None
        self.id = id

    ######## setters and getters ########
    def set_minimum_datapoints(self, minimum_datapoints: int) -> None:
        """
        set the minimum number of data contained within CellBox boundaries
        """
        if minimum_datapoints < 0:
            raise ValueError("CellBox: minimum number of data contained can not be negative")
        self.minimum_datapoints = minimum_datapoints

    def set_data_source(self, data_source: list[Metadata]) -> None:
        """
        a method that sets the data source of the cellbox ( which includes the data loaders,
          splitting conditions and aggregation type)

        Args:
            data_source (List <MetaData>): a list of MetaData objects, each object represents a source of this CellBox data
              (where the data comes from, how it is spitted and aggregated)
        """
        self.data_source = data_source

    def set_parent(self, parent: CellBox) -> None:
        """
        set the parent CellBox, which is the bigger CellBox that conains this CellBox
        Args:
            CellBox: the bigger Cellbox object that got splitted to produce this cellbox
        """
        self.parent = parent

    def set_split_depth(self, split_depth: int) -> None:
        """
        set the split depth of a CellBox, which represents is the number of times the CellBox
        has been split to reach it's current size.
        """
        if split_depth < 0:
            raise ValueError("CellBox: split depth can not be negative")
        self.split_depth = split_depth

    def set_id(self, id: Any) -> None:
        """
        method ssts cellbox id
        """
        self.id = id

    def set_bounds(self, bounds: Boundary) -> None:
        """
        Set the boundary of this cellbox
        """
        self.bounds = bounds

    def get_id(self) -> int:
        """
        method returns cellbox cell id
        """
        return int(self.id)

    def get_minimum_datapoints(self) -> int:
        """
        get the minimum number of data contained within CellBox boundaries
        """
        return self.minimum_datapoints

    def get_data_source(self) -> list[Metadata] | None:
        """
        a method that gets the data source of the cellbox
          (the data loaders, splitting conditions and aggregation type)
        returns:
        data_source (List <MetaData>): a list of MetaData objects, each object represents a source
        of this CellBox data (where the data comes from, how it is spitted and aggregated)
        """
        return self.data_source

    def get_parent(self) -> CellBox | None:
        """
        get the parent CellBox, which is the bigger CellBox that conains this CellBox
        """
        return self.parent

    def get_bounds(self) -> Boundary:
        """
        get the spatial and temporal bounds (lat range, long range and time range) of this cellbox
        """
        return self.bounds

    def get_split_depth(self) -> int:
        """
        get the split depth of a CellBox, which represents is the number of times the CellBox
          has been split to reach it's current size.
        """
        return self.split_depth

    def contains_point(self, lat: float, long: float) -> bool:
        """
        Returns true if a given lat/long coordinate is contained within this cellbox.

        Args:
            lat (float): latitude of a given point
            long (float): longitude of a given point

        Returns:
            contains_points (bool): True if this CellBox contains a point given by
                parameters (lat, long)
        """
        shapely_boundary = self.bounds.to_polygon()
        point = Point(long, lat)
        point_within_bounds = cast("bool", shapely_boundary.contains(point))
        point_on_bounds = cast("bool", shapely_boundary.boundary.contains(point))
        point_on_north_edge = shapely_boundary.bounds[2] == point.x
        point_on_east_edge = shapely_boundary.bounds[3] == point.y

        return point_within_bounds or (
            point_on_bounds and (point_on_north_edge or point_on_east_edge)
        )

    ######################################################
    # methods used for splitting a cellbox

    def should_split(self, stop_index: int) -> bool:
        """
        determines if a cellbox should be split based on the homogeneity
        condition of each data type contained within. The homogeneity condition
        of values within this cellbox is calculated using the method
        'get_hom_cond' in each DataLoader object inside CellBox's metadata\n

        if ANY data returns 'HOM':
            do not split
        if ANY data returns 'MIN':
            do not split
        if ALL data returns 'CLR':
            do not split
        else (mixture of CLR & HET):
            split\n
        Args:
            stop_index: the index of the data source at which checking the splitting conditions stops.
            Implemented like this to perform depth-first splitting.
            Should be deprecated once we switch to breadth-first splitting
        Returns:
             bool: True if the splitting_conditions of this CellBox
                will result in the CellBox being split.
        """
        hom_conditions: list[str] = []

        current_data_source = None
        data_source = self.get_data_source()
        if data_source is None:
            return False
        for index in range(stop_index):
            current_data_source = data_source[index]
            data_loader = current_data_source.get_data_loader()
            data_subset = current_data_source.get_data_subset()
            splitting_conditions = current_data_source.get_splitting_conditions()
            if splitting_conditions is not None:
                for splitting_cond in splitting_conditions:
                    hom_cond = data_loader.get_hom_condition(
                        self.bounds, splitting_cond, data=data_subset
                    )
                    hom_conditions.append(hom_cond)
        if "HOM" in hom_conditions:
            return False
        if "MIN" in hom_conditions:
            return False
        return hom_conditions.count("CLR") != len(hom_conditions)

    def should_split_breadth_first(self) -> bool:
        """
        determines if a cellbox should be split based on the homogeneity
        condition of each data type contained within. The homogeneity condition
        of values within this cellbox is calculated using the method
        'get_hom_cond' in each DataLoader object inside CellBox's metadata

        if ANY data returns 'HOM':
            do not split
        if ANY data returns 'MIN':
            do not split
        if ALL data returns 'CLR':
            do not split
        else (mixture of CLR & HET):
            split

        Returns:
            should_split (bool): True if the splitting_conditions of this CellBox
                will result in the CellBox being split.
        """
        hom_conditions: list[str] = []
        data_source = self.data_source
        if data_source is None:
            return False
        for current_data_source in data_source:
            data_loader = current_data_source.get_data_loader()
            data_subset = current_data_source.get_data_subset()
            splitting_conditions = current_data_source.get_splitting_conditions()
            if splitting_conditions is not None:
                for splitting_cond in splitting_conditions:
                    hom_cond = data_loader.get_hom_condition(
                        self.bounds, splitting_cond, data=data_subset
                    )
                    hom_conditions.append(hom_cond)

        if "HOM" in hom_conditions:
            return False
        if "MIN" in hom_conditions:
            return False
        return hom_conditions.count("CLR") != len(hom_conditions)

    def split(self, start_id: int) -> list[CellBox]:
        """
        splits the current cellbox into 4 corners, returns as a list of cellbox objects.

        Args:
            start_id : represenst the start of the splitted cellboxes ids,
              usuallly it is the number of the existing cellboxes
        Returns:
             list<CellBox>: The 4 corner cellboxes generated by splitting
             the cellbox uniformly.
        """
        split_boxes = self.create_splitted_cell_boxes(start_id)

        # set CellBox split_depth, data_source and parent
        data_source = self.get_data_source()
        if data_source is None:
            return split_boxes
        for split_box in split_boxes:
            split_box.set_split_depth(self.get_split_depth() + 1)
            # Create metadata with data subset
            split_box_data_sources = []
            for source in data_source:
                # Extract data for each new cellbox
                data_subset = source.data_loader.trim_datapoints(
                    split_box.bounds, data=source.data_subset
                )
                # Update metadata with that (rest stays the same)
                split_box_data_source = Metadata(
                    source.get_data_loader(),
                    source.get_splitting_conditions(),
                    source.get_value_fill_type(),
                    data_subset,
                )
                split_box_data_sources += [split_box_data_source]
            split_box.set_data_source(split_box_data_sources)
            split_box.set_parent(self)
        return split_boxes

    def create_splitted_cell_boxes(self, index: int) -> list[CellBox]:
        """
        method that creates 4 splitted cellbox
        """
        half_width = self.bounds.get_width() / 2
        half_height = self.bounds.get_height() / 2

        # create 4 new cellboxes
        time_range = self.bounds.get_time_range()
        lat = self.bounds.get_lat_min()
        lat_range = [lat + half_height, lat + self.bounds.get_height()]
        long = self.bounds.get_long_min()
        long_range = [long, longitude_domain(long + half_width)]
        boundary = Boundary(lat_range, long_range, time_range)
        north_west = CellBox(boundary, str(index))

        lat_range = [lat + half_height, lat + self.bounds.get_height()]
        long_range = [
            longitude_domain(long + half_width),
            longitude_domain(long + self.bounds.get_width()),
        ]
        boundary = Boundary(lat_range, long_range, time_range)
        index += 1
        north_east = CellBox(boundary, str(index))

        lat_range = [lat, lat + half_height]
        long_range = [long, longitude_domain(long + half_width)]
        boundary = Boundary(lat_range, long_range, time_range)
        index += 1
        south_west = CellBox(boundary, str(index))

        lat_range = [lat, lat + half_height]
        long_range = [
            longitude_domain(long + half_width),
            longitude_domain(long + self.bounds.get_width()),
        ]
        boundary = Boundary(lat_range, long_range, time_range)
        index += 1
        south_east = CellBox(boundary, str(index))

        return [north_west, north_east, south_west, south_east]

    def aggregate(self) -> AggregatedCellBox:
        """
        aggregates CellBox data using the associated data_sources' aggregate type (ex. MEAN, MAX)
        and returns AggregatedCellBox object

        Returns:
            AggregatedCellbox: object contains the aggregated data within cellbox bounds.
        """
        agg_dict: dict[str, Any] = {}
        data_source = self.get_data_source()
        if data_source is None:
            raise ValueError("Cannot aggregate cellbox with no data source")
        for source in data_source:
            loader = source.get_data_loader()
            data_subset = source.get_data_subset()

            # get the aggregated value from the associated DataLoader
            agg_value = loader.get_value(self.bounds, data=data_subset)
            data_name = loader.data_name
            parent = self.get_parent()
            # check if the data name has many entries (ex. uC,uV)
            if "," in data_name:
                agg_value = self.check_vector_data(source, loader, agg_value, data_name)

            elif np.isnan(agg_value[data_name]):
                if source.get_value_fill_type() == "parent":
                    # if the agg_value empty and get_value_fill_type is parent, then use the parent bounds
                    while parent is not None and np.isnan(agg_value[data_name]):
                        # Search through parent metadata to find match
                        parent_data_source_list = parent.get_data_source()
                        if parent_data_source_list is None:
                            break
                        for parent_source in parent_data_source_list:
                            if parent_source.get_data_loader() == source.get_data_loader():
                                break
                        # If no match found
                        else:
                            raise ValueError("Dataloader not found in parent")
                        parent_data_subset = parent_source.get_data_subset()
                        agg_value = loader.get_value(parent.bounds, data=parent_data_subset)
                        parent = parent.get_parent()
                else:  # not parent, so either float or Nan so set the agg_Data to value_fill_type
                    agg_value[data_name] = source.get_value_fill_type()

            # If already and value for {data_name} in cellbox and it's a NaN, overwrite
            if data_name in agg_dict:
                if np.isnan(agg_dict[data_name]):
                    logger.warning(
                        f"\t{data_name} already exists in cellbox! Overwriting only NaN values"
                    )
                    agg_dict.update(agg_value)
            else:
                agg_dict.update(agg_value)

        agg_cellbox = AggregatedCellBox(self.bounds, agg_dict, self.get_id())
        # free the memory space used by the cellbox
        self.deallocate_cellbox()
        return agg_cellbox

    def check_vector_data(
        self, source: Metadata, loader: Any, agg_value: dict[str, Any], data_name: str
    ) -> dict[str, Any]:
        """
        method that checks if the vector data is None and calls the parent get value
        """
        data_name_list = data_name.split(",")
        for name in data_name_list:
            parent = self.get_parent()
            if np.isnan(agg_value[name]):
                if source.get_value_fill_type() == "parent":
                    # if the agg_value empty and get_value_fill_type is parent, then use the parent bounds
                    while parent is not None and np.isnan(agg_value[name]):
                        # Search through parent metadata to find match
                        parent_data_source = parent.get_data_source()
                        if parent_data_source is None:
                            break
                        for parent_source in parent_data_source:
                            if parent_source.get_data_loader() == source.get_data_loader():
                                break
                        # If no match found
                        else:
                            raise ValueError("Dataloader not found in parent")
                        parent_data_subset = parent_source.get_data_subset()
                        agg_value[name] = loader.get_value(parent.bounds, data=parent_data_subset)[
                            name
                        ]
                        parent = parent.get_parent()
                else:  # not parent, so either float or Nan so set the agg_Data to value_fill_type
                    agg_value[data_name] = source.get_value_fill_type()
        return agg_value

    def deallocate_cellbox(self) -> None:
        """
        Method to free up the memory space allocated by the cellbox
        """
        data_source = self.get_data_source()
        if data_source is None:
            return
        for source in data_source:
            loader = source.get_data_loader()
            del loader
            del source
        parent = self.parent
        # free up the memory space used by the parent cellboxes chain
        while isinstance(parent, CellBox):
            parent_data_source = parent.get_data_source()
            if parent_data_source is None:
                break
            for source in parent_data_source:
                loader = source.get_data_loader()
                del loader
                del source
            grandparent = parent.parent
            del parent
            parent = grandparent
        del self
