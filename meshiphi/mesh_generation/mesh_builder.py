"""

In this section we will discuss the usage of the MeshBuilder functionality of meshiphi.\n

Example:
    An example of how to run this code can be executed by running the following in an ipython/Jupyter Notebook::\n

        from meshiphi.mesh_generation.mesh_builder import MeshBuilder

        import json
        with open('./config.json', 'r') as f:
            config = json.load(f)['config']

        mesh_builder = MeshBuilder(config)
        mesh_builder.build_environmental_mesh() \n

"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from tqdm import tqdm

from meshiphi.config_validation.config_validator import validate_mesh_config
from meshiphi.dataloaders.factory import DataLoaderFactory
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.cellbox import CellBox
from meshiphi.mesh_generation.direction import Direction
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
from meshiphi.mesh_generation.mesh import Mesh
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph
from meshiphi.utils import longitude_distance, longitude_domain

logger = logging.getLogger(__name__)


class MeshBuilder:
    """

    A class resposible for building an environment mesh based on a provided config file.

    """

    def __init__(self, config: dict[str, Any]) -> None:
        """

        Constructs a Mesh from a given config file.\n

        Args:
            config (dict): config file which defines the attributes of the Mesh to be constructed. config is of the form: \n
                    {\n
                    "region": {\n
                        "lat_min": (real),\n
                        "lat_max": (real),\n
                        "long_min": (real),\n
                        "long_max": (real),\n
                        "start_time": (string) 'YYYY-MM-DD',\n
                        "end_time": (string) 'YYYY-MM-DD',\n
                        "cell_width": (real),\n
                        "cell_height" (real),\n
                        "split_depth" (int)\n
                    },\n
                    "data_sources": [\n
                        {\n
                            "loader": (string)\n
                            "params" (dict)\n
                        }\n
                    ],\n
                    "splitting": { \n
                        "split_depth": (int),\n
                        "minimum_datapoints": (int)\n
                        }\n
                    }

                NOTE: In the case of constructing a global mesh, the longtitude range should be -180:180.

                "j_grid" (bool): True if the Mesh to be constructed should be of the same format as the original Java CellGrid, to be used for regression testing.\n

        """
        logger.info("Initialising Mesh Builder")
        validate_mesh_config(config)
        self.config = config
        bounds = Boundary.from_json(config)

        # Configs may contain reference to system time for start_time and end_time
        # which are parsed to datetime format when initialising boundary.
        # updates config start_time/ end_time once system time has been parsed.
        self.config["region"]["start_time"] = bounds.get_time_min()
        self.config["region"]["end_time"] = bounds.get_time_max()

        cell_width = config["region"]["cell_width"]
        cell_height = config["region"]["cell_height"]

        self.validate_bounds(bounds, cell_width, cell_height)

        logger.info("Initialising mesh...")
        logger.info("Initialising cellboxes...")

        cellboxes = []
        cellboxes = self.initialize_cellboxes(bounds, cell_width, cell_height)

        # Calculate width of mesh in cell-coordinates rather than degrees
        grid_width = np.divide(bounds.get_width(), cell_width)

        min_datapoints = 5
        if "splitting" in self.config:
            min_datapoints = self.config["splitting"]["minimum_datapoints"]
        meta_data_list = self.initialize_meta_data(bounds, min_datapoints)

        # Initialise the metadata for each cellbox, including subsets of each
        # dataloader's data set
        logger.info("Initialising cellbox metadata...")
        for cellbox in tqdm(
            cellboxes,
            bar_format="{desc}{n_fmt}/{total_fmt} |{bar}| {percentage:3.0f}%, [{elapsed} elapsed] ",
        ):
            # checking to avoid any dummy cellboxes
            # (the ones that were split and replaced)
            if isinstance(cellbox, CellBox):
                cellbox.set_minimum_datapoints(min_datapoints)
                # Update metadata with cellbox's data subset
                updated_meta_data_list = self.initialize_meta_data_subsets(
                    cellbox.bounds, meta_data_list
                )
                # assign meta data to each cellbox
                cellbox.set_data_source(updated_meta_data_list)

        logger.info("Initialising neighbour graph...")
        self.neighbour_graph = NeighbourGraph(cellboxes, grid_width)
        self.neighbour_graph.set_global_mesh(
            self.check_global_mesh(bounds, cellboxes, int(grid_width))
        )

        max_split_depth = 0
        if "splitting" in self.config:
            max_split_depth = self.config["splitting"]["split_depth"]
        self.mesh = Mesh(bounds, cellboxes, self.neighbour_graph, max_split_depth)
        self.mesh.set_config(config)

    def initialize_meta_data(self, bounds: Boundary, min_datapoints: int) -> list[Metadata]:
        """
        Creates a metadata object which holds information about the data sources
        within a cellbox.

        Args:
            bounds (Boundary):
                Outer boundary of the mesh being created

            min_datapoints (int):
                Minimum number of datapoints each dataloader is allowed to
                aggregate
        Returns:
            list(Metadata):
                Array of metadata objects; one for each data source
        """
        meta_data_list = []
        splitting_conds = []
        if "data_sources" in self.config:
            for data_source in self.config["data_sources"]:
                loader_name = data_source["loader"]
                loader = DataLoaderFactory.get_dataloader(
                    loader_name, bounds, data_source["params"], min_datapoints
                )

                logger.debug("Creating data loader {}".format(data_source["loader"]))
                updated_splitting_cond = []  # create this list to get rid of the data_name in the conditions as it is not handeled by the DataLoader, remove after talking to Harry to address this in the loader
                if "splitting_conditions" in data_source["params"]:
                    splitting_conds = data_source["params"]["splitting_conditions"]
                    for split_cond in splitting_conds:
                        cond = split_cond[loader.data_name]
                        updated_splitting_cond.append(cond)

                value_fill_type = self.check_value_fill_type(data_source)

                # Update list of files in config to match the ones read in by dataloader
                if "files" in data_source["params"]:
                    data_source["params"]["files"] = loader.files

                meta_data_obj = Metadata(
                    loader, updated_splitting_cond, str(value_fill_type), loader.data
                )
                meta_data_list.append(meta_data_obj)

        return meta_data_list

    def initialize_meta_data_subsets(
        self, bounds: Boundary, meta_data_list: list[Metadata]
    ) -> list[Metadata]:
        """
        Updates cellbox metadata objects to include data subsets which contain
        datapoints from only within the cellbox boundaries (as opposed to the
        entire mesh's boundary)

        Args:
            bounds (Boundary):
                Outer boundary of the cellbox

            meta_data_list (list(Metadata)):
                Cellbox's metadata that needs to be updated with data subsets

        Returns:
            list(Metadata):
                Array of metadata objects; one for each data source. Includes
                data_subsets
        """
        logger.debug(f"Initilizing data subset for {bounds}")
        updated_meta_data_list = []
        # For each set of data within the cellbox
        for source in meta_data_list:
            # Limit data within dataloader to just that within cellbox boundary
            data_subset = source.data_loader.trim_datapoints(bounds)
            # Update metadata object with this data subset
            updated_meta_data_list += [
                Metadata(
                    source.get_data_loader(),
                    source.get_splitting_conditions(),
                    source.get_value_fill_type(),
                    data_subset,
                )
            ]

        return updated_meta_data_list

    def check_value_fill_type(self, data_source: dict[str, Any]) -> str | float:
        def is_float(element: Any) -> bool:
            if element is None:
                return False
            try:
                float(element)
                return True
            except ValueError:
                return False

        value_fill_type = "parent"
        if "value_fill_types" in data_source["params"]:
            if is_float(data_source["params"]["value_fill_types"]) or data_source["params"][
                "value_fill_types"
            ] in ["parent", "Nan"]:
                value_fill_type = data_source["params"]["value_fill_types"]
            else:
                logger.warning(
                    "Invalid value for value_fill_types, setting to the default(parent) instead."
                )
        return value_fill_type

    def initialize_cellboxes(
        self, bounds: Boundary, cell_width: float, cell_height: float
    ) -> list[CellBox]:
        cellboxes: list[CellBox] = []
        (bounds.get_lat_max() - bounds.get_lat_min()) / cell_height

        lat_range = np.arange(bounds.get_lat_min(), bounds.get_lat_max(), cell_height)

        # Account for going over the antimeridian with longitude_distance
        (longitude_distance(bounds.get_long_min(), bounds.get_long_max()) / cell_width)

        long_range_temp = (
            np.arange(bounds.get_long_min(), bounds.get_long_max(), cell_width)
            if bounds.get_long_min() < bounds.get_long_max()
            else np.arange(bounds.get_long_min(), bounds.get_long_max() + 360, cell_width)
        )
        # Cast to within -180:180
        long_range = longitude_domain(long_range_temp)

        for lat in lat_range:
            for long in long_range:
                cell_lat_range = [float(lat), float(lat + cell_height)]
                # If doesn't go over anti-meridian
                if long + cell_width <= 180:
                    cell_long_range = [float(long), float(long + cell_width)]
                else:
                    cell_long_range = [float(long), float(long + cell_width - 360)]
                cell_bounds = Boundary(cell_lat_range, cell_long_range, bounds.get_time_range())
                cell_id = str(len(cellboxes))
                cellbox = CellBox(cell_bounds, cell_id)
                cellboxes.append(cellbox)
        return cellboxes

    def add_dataloader(
        self,
        Dataloader: Any,
        params: dict[str, Any],
        bounds: Boundary | None = None,
        name: str = "myDataLoader",
        min_dp: int = 5,
    ) -> MeshBuilder:
        """
        Adds a dataloader to a pre-existing mesh by adding to the metadata

        Args:
            Dataloader (ScalarDataLoader or VectorDataLoader):
                Dataloader object to add to metadata
            params (dict):
                Parameters to initialise dataloader with
            bounds (Boundary):
            name (str):
                Name of the dataloader used in config

        Returns:
            MeshBuilder:
                Original MeshBuilder object (self) with added metadata for
                new dataloader
        """
        if bounds is None:
            bounds = Boundary.from_json(self.config)

        logger.debug("Adding dataloader")
        dataloader = Dataloader(bounds, params)
        updated_splitting_cond = []
        if "splitting_conditions" in params:
            splitting_conds = params["splitting_conditions"]
            updated_splitting_cond = [
                split_cond[dataloader.data_name] for split_cond in splitting_conds
            ]

        data_source = {"loader": name, "params": params}
        value_fill_type = self.check_value_fill_type(data_source)

        meta_data_obj = Metadata(dataloader, updated_splitting_cond, str(value_fill_type))

        for cellbox in self.mesh.cellboxes:
            if isinstance(cellbox, CellBox):
                cellbox.set_minimum_datapoints(min_dp)
                # Add new meta data to list of data sources per cellbox
                cellbox.set_data_source([*cellbox.get_data_source(), meta_data_obj])  # type: ignore[misc]

        return self

    def validate_bounds(self, bounds: Boundary, cell_width: float, cell_height: float) -> None:
        if (bounds.get_long_max() - bounds.get_long_min()) % 360 % cell_width != 0:
            raise ValueError(
                f"The defined longitude region <{bounds.get_long_min()} :{bounds.get_long_max()}> "
                f"is not divisable by the initial cell width <{cell_width}>"
            )

        if (bounds.get_lat_max() - bounds.get_lat_min()) % cell_height != 0:
            raise ValueError(
                f"The defined latitude region <{bounds.get_lat_min()} :{bounds.get_lat_max()}> "
                f"is not divisable by the initial cell height <{cell_height}>"
            )

    def check_global_mesh(
        self, bounds: Boundary, cellboxes: list[CellBox], grid_width: int
    ) -> bool:
        """
         Checks if the mesh is a global one and connects the cellboxes at the minimum longtitude and max longtitude accordingly

        Args:
             bounds (Boundary): an object represents the bounds of the mesh
             cellboxes (list<Cellbox>): a list that contains the mesh initial cellboxes (before any splitting)
             grid_width (int): an int represents the width of the mesh ( the number of cellboxes it contains horizontally)
        Returns:
             is_global_mesh (bool): a boolean indicates if the mesh is a global one
        """
        is_global_mesh = False
        if (
            bounds.get_long_max() == abs(bounds.get_long_min()) == 180
        ):  # check if it is a global mesh
            is_global_mesh = True
            # find indeces of cellboxes at the min longtitude and max longtitude
            min_long_cellboxes = cellboxes[::grid_width]
            max_long_cellboxes = cellboxes[grid_width - 1 :: grid_width]
            # update NG to connect cellboxes
            for i in range(len(min_long_cellboxes)):
                self.neighbour_graph.add_neighbour(
                    int(min_long_cellboxes[i].get_id()),
                    Direction.west,
                    int(max_long_cellboxes[i].get_id()),
                )
                self.neighbour_graph.add_neighbour(
                    int(max_long_cellboxes[i].get_id()),
                    Direction.east,
                    int(min_long_cellboxes[i].get_id()),
                )
                # checks to avoid the very upper and lower cellboxes as they do not have north/south neighbours
                if 0 <= i < len(min_long_cellboxes) - 1:
                    self.neighbour_graph.add_neighbour(
                        int(min_long_cellboxes[i].get_id()),
                        Direction.north_west,
                        int(max_long_cellboxes[i + 1].get_id()),
                    )
                    self.neighbour_graph.add_neighbour(
                        int(max_long_cellboxes[i].get_id()),
                        Direction.north_east,
                        int(min_long_cellboxes[i + 1].get_id()),
                    )
                if 0 < i <= len(min_long_cellboxes) - 1:
                    self.neighbour_graph.add_neighbour(
                        int(min_long_cellboxes[i].get_id()),
                        Direction.south_west,
                        int(max_long_cellboxes[i - 1].get_id()),
                    )
                    self.neighbour_graph.add_neighbour(
                        int(max_long_cellboxes[i].get_id()),
                        Direction.south_east,
                        int(min_long_cellboxes[i - 1].get_id()),
                    )

        return is_global_mesh

    def to_json(self) -> dict[str, Any]:
        """
        Returns this Mesh converted to a JSON object.

        Returns:
            json (json): a string representation of the CellGird parseable as a JSON object. The JSON object is of the form -

                {
                    "config": the config used to initialize the Mesh,
                    "cellboxes": a list of CellBoxes contained within the Mesh,
                    "neighbour_graph": a graph representing the adjacency of CellBoxes within the Mesh
                }
        """
        output: dict[str, Any] = {}
        output["config"] = {"mesh_info": self.config}
        output["cellboxes"] = self.mesh.get_cellboxes()
        output["neighbour_graph"] = self.neighbour_graph.get_graph()
        return output

    def split_and_replace(self, cellbox: CellBox) -> list[CellBox]:
        """
        Replaces a cellbox given by parameter 'cellbox' in this grid with
        4 smaller cellboxes representing the four corners of the given cellbox.
        A neighbours map is then created for each of the 4 new cellboxes
        and the neighbours map for all surrounding cell boxes is updated.

        Args:
            cellbox (CellBox): the CellBox within this Mesh to be split into
                4 smaller CellBox objects.

        """
        split_cellboxes = cellbox.split(len(self.mesh.cellboxes))
        self.mesh.cellboxes += split_cellboxes
        cellboxes = self.mesh.cellboxes
        cellbox_indx = cellboxes.index(cellbox)

        north_west_indx = cellboxes.index(split_cellboxes[0])
        north_east_indx = cellboxes.index(split_cellboxes[1])
        south_west_indx = cellboxes.index(split_cellboxes[2])
        south_east_indx = cellboxes.index(split_cellboxes[3])

        south_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_indx, Direction.south)
        north_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_indx, Direction.north)
        east_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_indx, Direction.east)
        west_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_indx, Direction.west)

        # Create neighbour map for SW split cell.
        sw_neighbour_map = {
            Direction.north_east: [north_east_indx],
            Direction.east: [south_east_indx],
            Direction.south_east: [],
            Direction.south: [],
            # update to use the NG class
            Direction.south_west: self.neighbour_graph.get_neighbours(
                cellbox_indx, Direction.south_west
            ),
            Direction.west: [],
            Direction.north_west: [],
            Direction.north: [north_west_indx],
        }

        self.fill_sw_neighbour_map(
            south_west_indx, south_neighbour_indx, west_neighbour_indx, sw_neighbour_map
        )
        self.neighbour_graph.add_node(south_west_indx, sw_neighbour_map)

        # Create neighbour map for NW split cell
        nw_neighbour_map = {
            Direction.north_east: [],
            Direction.east: [north_east_indx],
            Direction.south_east: [south_east_indx],
            Direction.south: [south_west_indx],
            Direction.south_west: [],
            Direction.west: [],
            Direction.north_west: self.neighbour_graph.get_neighbours(
                cellbox_indx, Direction.north_west
            ),
            Direction.north: [],
        }

        self.fill_nw_map(
            north_west_indx, north_neighbour_indx, west_neighbour_indx, nw_neighbour_map
        )
        self.neighbour_graph.add_node(north_west_indx, nw_neighbour_map)

        # Create neighbour map for NE split cell
        ne_neighbour_map = {
            Direction.north_east: self.neighbour_graph.get_neighbours(
                cellbox_indx, Direction.north_east
            ),
            Direction.east: [],
            Direction.south_east: [],
            Direction.south: [south_east_indx],
            Direction.south_west: [south_west_indx],
            Direction.west: [north_west_indx],
            Direction.north_west: [],
            Direction.north: [],
        }
        self.fill_ne_map(
            north_east_indx, north_neighbour_indx, east_neighbour_indx, ne_neighbour_map
        )
        self.neighbour_graph.add_node(north_east_indx, ne_neighbour_map)

        # Create neighbour map for SE split cell
        se_neighbour_map = {
            Direction.north_east: [],
            Direction.east: [],
            Direction.south_east: self.neighbour_graph.get_neighbours(
                cellbox_indx, Direction.south_east
            ),
            Direction.south: [],
            Direction.south_west: [],
            Direction.west: [south_west_indx],
            Direction.north_west: [north_west_indx],
            Direction.north: [north_east_indx],
        }

        self.fill_se_map(
            south_east_indx, south_neighbour_indx, east_neighbour_indx, se_neighbour_map
        )
        self.neighbour_graph.add_node(south_east_indx, se_neighbour_map)

        # Update neighbours of cellbox_indx with the new neighbours coming from splitting the cellbox.

        # Update north neighbours of cellbox_indx with the new neighbours comming from the splitted cellbox
        self.neighbour_graph.update_neighbours(
            cellbox_indx, [north_west_indx, north_east_indx], Direction.north, cellboxes
        )
        # Update east neighbour cellbox_indx with the new neighbours comming from the splitted cellbox
        self.neighbour_graph.update_neighbours(
            cellbox_indx, [north_east_indx, south_east_indx], Direction.east, cellboxes
        )
        # Update south neighbour cellbox_indx with the new neighbours comming from the splitted cellbox
        self.neighbour_graph.update_neighbours(
            cellbox_indx, [south_west_indx, south_east_indx], Direction.south, cellboxes
        )
        # Update west neighbour cellbox_indx with the new neighbours comming from the splitted cellbox
        self.neighbour_graph.update_neighbours(
            cellbox_indx, [north_west_indx, south_west_indx], Direction.west, cellboxes
        )
        # Update corner neighbour maps
        self.neighbour_graph.update_corner_neighbours(
            cellbox_indx,
            north_west_indx,
            north_east_indx,
            south_west_indx,
            south_east_indx,
        )

        # remove the original splitted cellbox from the neighbour_graph
        self.neighbour_graph.remove_node(cellbox_indx)
        # set the original splitted cellbox to None
        cellboxes[cellbox_indx] = None  # type: ignore[call-overload]

        return split_cellboxes

    def _get_cellbox_by_id(
        self, cellboxes: list[CellBox | None], cellbox_id: Any
    ) -> CellBox | None:
        """Get cellbox from list by ID, handling both int indices and Any IDs"""
        if isinstance(cellbox_id, int) and 0 <= cellbox_id < len(cellboxes):
            return cellboxes[cellbox_id]
        # Fallback: search by ID
        for cb in cellboxes:
            if cb is not None and cb.id == cellbox_id:
                return cb
        return None

    ############################## methods to fill the neighbour maps of the splitted cells ########################

    def fill_se_map(
        self,
        south_east_indx: str | int,
        south_neighbour_indx: list[Any],
        east_neighbour_indx: list[Any],
        se_neighbour_map: dict[int, list[Any]],
    ) -> None:
        """
        method that fills the South east neighbours
        """
        cellboxes: list[CellBox | None] = self.mesh.cellboxes  # type: ignore[assignment]
        se_cellbox = self._get_cellbox_by_id(cellboxes, south_east_indx)
        for indx in south_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(se_cellbox, indx_cellbox) == Direction.south:
                se_neighbour_map[4].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(se_cellbox, indx_cellbox)
                == Direction.south_west
            ):
                se_neighbour_map[-1].append(indx)
        for indx in east_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(se_cellbox, indx_cellbox) == Direction.east:
                se_neighbour_map[2].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(se_cellbox, indx_cellbox)
                == Direction.north_east
            ):
                se_neighbour_map[1].append(indx)

    def fill_ne_map(
        self,
        north_east_indx: str | int,
        north_neighbour_indx: list[Any],
        east_neighbour_indx: list[Any],
        ne_neighbour_map: dict[int, list[Any]],
    ) -> None:
        """
        method that fills the North east neighbours
        """
        cellboxes: list[CellBox | None] = self.mesh.cellboxes  # type: ignore[assignment]
        ne_cellbox = self._get_cellbox_by_id(cellboxes, north_east_indx)
        for indx in north_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(ne_cellbox, indx_cellbox) == Direction.north:
                ne_neighbour_map[-4].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(ne_cellbox, indx_cellbox)
                == Direction.north_west
            ):
                ne_neighbour_map[-3].append(indx)
        for indx in east_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(ne_cellbox, indx_cellbox) == Direction.east:
                ne_neighbour_map[2].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(ne_cellbox, indx_cellbox)
                == Direction.south_east
            ):
                ne_neighbour_map[3].append(indx)

    def fill_nw_map(
        self,
        north_west_indx: str | int,
        north_neighbour_indx: list[Any],
        west_neighbour_indx: list[Any],
        nw_neighbour_map: dict[int, list[Any]],
    ) -> None:
        """
        method that fills the North west neighbours
        """
        cellboxes: list[CellBox | None] = self.mesh.cellboxes  # type: ignore[assignment]
        nw_cellbox = self._get_cellbox_by_id(cellboxes, north_west_indx)
        for indx in north_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(nw_cellbox, indx_cellbox) == Direction.north:
                nw_neighbour_map[-4].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(nw_cellbox, indx_cellbox)
                == Direction.north_east
            ):
                nw_neighbour_map[1].append(indx)
        for indx in west_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(nw_cellbox, indx_cellbox) == Direction.west:
                nw_neighbour_map[-2].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(nw_cellbox, indx_cellbox)
                == Direction.south_west
            ):
                nw_neighbour_map[-1].append(indx)

    def fill_sw_neighbour_map(
        self,
        south_west_indx: str | int,
        south_neighbour_indx: list[Any],
        west_neighbour_indx: list[Any],
        sw_neighbour_map: dict[int, list[Any]],
    ) -> None:
        """
        method that fills the South west neighbours
        """
        cellboxes: list[CellBox | None] = self.mesh.cellboxes  # type: ignore[assignment]
        sw_cellbox = self._get_cellbox_by_id(cellboxes, south_west_indx)
        for indx in south_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if (
                self.neighbour_graph.get_neighbour_case(sw_cellbox, indx_cellbox)
                == Direction.south_east
            ):
                sw_neighbour_map[3].append(indx)
            if self.neighbour_graph.get_neighbour_case(sw_cellbox, indx_cellbox) == Direction.south:
                sw_neighbour_map[4].append(indx)
        for indx in west_neighbour_indx:
            indx_cellbox = self._get_cellbox_by_id(cellboxes, indx)
            if self.neighbour_graph.get_neighbour_case(sw_cellbox, indx_cellbox) == Direction.west:
                sw_neighbour_map[-2].append(indx)
            if (
                self.neighbour_graph.get_neighbour_case(sw_cellbox, indx_cellbox)
                == Direction.north_west
            ):
                sw_neighbour_map[-3].append(indx)

    def split_to_depth(self, split_depth: int) -> None:
        """
        splits all cellboxes in this grid until a maximum split depth
        is reached, or all cellboxes are homogeneous.

        Args:
            split_depth (int): The maximum split depth reached by any CellBox
                within this Mesh after splitting.
        """
        logger.info("Splitting cellboxes...")
        # loop over the data_sources then cellboxes to implement depth-first splitting. should be simpler and loop over cellboxes only once we switch to breadth-first splitting
        # this impl assumws all the cellboxes have the same data sources. should not be the caase once we switch to breadth-first splitting.
        data_sources = self.mesh.cellboxes[0].get_data_source()
        if data_sources is None:
            return

        # Set up data_source progress bar
        ds_pbar = tqdm(
            range(len(data_sources)),
            position=0,
            bar_format="{desc}{n_fmt}/{total_fmt} |{bar}| {percentage:3.0f}%, [{elapsed} elapsed] ",
        )
        sd_pbar = tqdm(
            range(split_depth),
            position=1,
            leave=False,
            bar_format=" Split depth: {n_fmt}/{total_fmt} |{bar}| {percentage:3.0f}%{postfix} ",
        )
        for index in ds_pbar:
            # Update name of data source being processed
            ds_pbar.set_description(
                f" Processing {data_sources[index].get_data_loader().dataloader_name} data"
            )

            if len(data_sources[index].get_splitting_conditions()) > 0:
                # Set up split depth progress bar
                level = 0
                sd_pbar = tqdm(
                    range(split_depth),
                    position=1,
                    leave=False,
                    bar_format=" Split depth: {n_fmt}/{total_fmt} |{bar}| {percentage:3.0f}%{postfix} ",
                )

                for cb_index, cellbox in enumerate(self.mesh.cellboxes):
                    ds_pbar.update(0)
                    if isinstance(cellbox, CellBox):
                        if cellbox.get_split_depth() > level:
                            level = cellbox.get_split_depth()
                            # If we're a split level further down, iterate progress in progress bar
                            sd_pbar.update()
                        # Split the cellbox
                        should_split = cellbox.should_split(index + 1)
                        if (cellbox.get_split_depth() < split_depth) & should_split:
                            self.split_and_replace(cellbox)
                        # Update number of cellboxes processed
                        sd_pbar.set_postfix_str(
                            f"[Cellbox {cb_index + 1} / {len(self.mesh.cellboxes)}]"
                        )
        tqdm.write("")
        ds_pbar.clear()
        sd_pbar.clear()

    def build_environmental_mesh(self) -> EnvironmentMesh:
        """
        splits the mesh then goes through the mesh cellboxes and builds an evironmental mesh that contains the cellboxes aggregated data

        Returns:
            EnvironmentMesh: an object that represents the constructed nonunifrom mesh and contains the aggregated cellboxs and neighbour graph
        """
        self.split_to_depth(self.mesh.get_max_split_depth())
        agg_cellboxes = []

        logger.info("Aggregating cellboxes...")
        for agg_cell_count, cellbox in enumerate(
            tqdm(
                self.mesh.cellboxes,
                bar_format=" Aggregating cellboxes: {n_fmt}/{total_fmt} |{bar}| {percentage:3.0f}%, [{elapsed} elapsed] ",
            ),
            start=1,
        ):
            if isinstance(cellbox, CellBox):
                logger.debug(f"aggregating cellbox ({agg_cell_count}/{len(self.mesh.cellboxes)})")
                agg_cellboxes.append(cellbox.aggregate())

        return EnvironmentMesh(
            self.mesh.get_bounds(),
            agg_cellboxes,
            self.neighbour_graph,
            self.get_config(),
        )

    def get_config(self) -> dict[str, Any]:
        """
        returns the config
        """
        return self.config
