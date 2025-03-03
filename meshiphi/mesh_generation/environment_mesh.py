import json
import logging
import geopandas as gpd
import pandas as pd
from shapely import wkt
import numpy as np
import subprocess
import sys
import os
import tempfile
from shapely import wkt

from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph


from meshiphi.mesh_validation.sampler import Sampler
import collections.abc
import math
from pathlib import Path

class EnvironmentMesh:
    """
        a class that defines the environmental mesh structure and contains each cellbox aggregate information

        Attributes:
            bounds (Boundary): the boundaries of this mesh 
            agg_cellboxes (AggregatedCellBox[]): a list of aggregated cellboxes
            neighbour_graph(NeighbourGraph): an object contains each cellbox neighbours information 
            config (dict): conatins the initial config used to build this mesh\n
    """
    @classmethod
    def load_from_json(cls, mesh_json):
        """
            Constructs an Env.Mesh from a given env-mesh json file to be used by other modules (ex.Vessel Performance Modeller).

            Args:
                mesh_json (dict): a dictionary loaded from an Env-mesh json file of the following format - \n
                    \n
                    {\n
                        "mesh_info": {\n
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
                                },\n
                                ...,\n
                                {...}
                                ], \n
                            "splitting": {\n
                                    "split_depth": (int),\n
                                    "minimum_datapoints": (int)\n
                            }\n
                        },\n
                        "cellboxes": [\n
                            {\n

                            },\n
                            ...,\n
                            {...}\n

                        ],\n
                        "neighbour_graph": [\n
                            {\n

                            },\n
                            ...,\n
                            {...}\n
                        ]\n
                    }\n
            Returns:
                EnvironmentMesh: object that contains all the json file mesh information.\n
        """
        config = mesh_json['config']['mesh_info']
        cellboxes_json = mesh_json['cellboxes']
        agg_cellboxes = []
        bounds = Boundary.from_json(config)
        # load the agg_cellboxes
        for cellbox_json in cellboxes_json:
            agg_cellbox = AggregatedCellBox.from_json(cellbox_json)
            agg_cellboxes.append(agg_cellbox)
        neighbour_graph = NeighbourGraph.from_json(
            mesh_json['neighbour_graph'])
        obj = EnvironmentMesh(bounds, agg_cellboxes, neighbour_graph, config)
        return obj

    def __init__(self, bounds, agg_cellboxes, neighbour_graph, config):
        """
            Args:
              bounds (Boundary): the boundaries of this mesh 
              agg_cellboxes (AggregatedCellBox[]): a list of aggregated cellboxes
              neighbour_graph(NeighbourGraph): an object contains each cellbox neighbours information 
              config (dict): conatins the initial config used to build this mesh.\n
        """

        self.bounds = bounds
        self.agg_cellboxes = agg_cellboxes
        self.neighbour_graph = neighbour_graph
        self.config = config


    def query_inside_mesh(self,point):
        """
            Returns a bool whether the given point is within the cell 

            Args:
                point (tuple) - (lat,long) of point to query
            Returns:
                inside_mesh (bool) - Boolean stating if point inside mesh
        """
        inside_cell = [agg_cell.contains_point(point[0],point[1]) for agg_cell in self.agg_cellboxes]
        if any(inside_cell):
            return True
        else:
            return False

    def query_index(self,point):
        """
            Returns a index of the aggregate cellbox that contains the point

            Args:
                point (tuple) - (lat,long) of point to query
            Returns:
                cellbox_index (str) - Cellbox index containing the point
        """
        inside_cell = [agg_cell.contains_point(point[0],point[1]) for agg_cell in self.agg_cellboxes]

        if any(inside_cell):
            indices = np.where(inside_cell)[0]
            if len(indices) > 1:
                raise Exception('Point within more than one cellbox')    
            else:
                indx = indices[0]
                return self.agg_cellboxes[indx].id
        else:
            raise Exception('Point not within the mesh')



    def _split_loc(self,point):
        """
            Given a point determine if agg_cellboxes should be split or if at maximum split depth

            Args:
                point (tuple) - (lat,long) of point location used for splitting
            Returns:
                further_splittined (bool) - A boolean describing if further splitting is possible
        """
    
        # Defining cellbox containing point
        agg_cellbox_index = self.query_index(point)
        agg_cellbox_wp = self.get_cellbox(agg_cellbox_index)

        # Determing the mesh maximum split depth
        min_dcx = self.config['region']['cell_width']/(2**(self.config['splitting']['split_depth']))
        min_dcy = self.config['region']['cell_height']/(2**(self.config['splitting']['split_depth']))

        # Finding the split depth which contains waypoint
        cb_width  = agg_cellbox_wp.boundary.get_width()
        cb_height = agg_cellbox_wp.boundary.get_height()

        if (cb_width < min_dcx) or (cb_height < min_dcy):
            # Continue if cellbox is at max split depth
            return False
        else:
            # Split mesh if at maximum split depth
            self.split_and_replace(agg_cellbox_wp.id)
            return True


    def split_points(self,points):
        """
            Splitting the mesh to maximum split depth around a series of point locations

            Args:
                points ([tuple,tuple]) - List of tuples (lat,lon) for the different point locations to split about

        """
        for point in points:
            splitting_waypoint = True
            if self.query_inside_mesh(point):
                while splitting_waypoint:
                    splitting_waypoint = self._split_loc(point)

    def get_cellbox(self, cellbox_id):
        """
            returns the cellbox with the given id

            Args:
                cellbox_id (string): the id of the cellbox to be returned
            Returns:
                AggregatedCellBox: the cellbox with the given id
        """
        for cellbox in self.agg_cellboxes:
            if str(cellbox.get_id()) == str(cellbox_id):
                return cellbox

    # Merging meshes
    def merge_mesh(self, mesh2):
        """
            merges the given mesh with this mesh. The given mesh is not modified.

            Args:
                mesh2 (EnvironmentMesh): the mesh to be merged with this mesh
        """

        assert self.validate_merge_compatibility(mesh2), "The given mesh is not compatible with merging with this mesh" 

        # append config files
        if "merged" not in self.config.keys():
            self.config["merged"] = []

        self.config["merged"].append(mesh2.config)

        # merge cellboxes
        mesh2_bounds = mesh2.bounds

        # remove cellboxes within bounds of mesh2 from this mesh
        self.remove_cellboxes_within_bounds(mesh2_bounds)

        # Appended cellboxes from mesh2 to this mesh
        mesh1_max_id = self.get_max_cellbox_id()
        mesh2.increment_ids(mesh1_max_id + 1)
        for cellbox in mesh2.agg_cellboxes:
            self.add_cellbox(cellbox)

        # Appened neighbour graph from mesh2 to this mesh
        for index in mesh2.neighbour_graph.get_graph().keys():
            neighbour_map = mesh2.neighbour_graph.neighbour_graph[index]

            self.neighbour_graph.add_node(index, neighbour_map)

        # Tie the neighbour graphs of the cellboxes on the boundary between the two meshes
        north_ext_cellboxes = self.get_cellboxes_north_of_bounds(mesh2_bounds)
        north_int_cellboxes = mesh2.get_top_edge_cellboxes()
        self.tie_northern_cellbox_ng(north_ext_cellboxes, north_int_cellboxes)

        south_ext_cellboxes = self.get_cellboxes_south_of_bounds(mesh2_bounds)
        south_int_cellboxes = mesh2.get_bottom_edge_cellboxes()
        self.tie_southern_cellbox_ng(south_ext_cellboxes, south_int_cellboxes)

        east_ext_cellboxes = self.get_cellboxes_east_of_bounds(mesh2_bounds)
        east_int_cellboxes = mesh2.get_right_edge_cellboxes()
        self.tie_eastern_cellbox_ng(east_ext_cellboxes, east_int_cellboxes)

        west_ext_cellboxes = self.get_cellboxes_west_of_bounds(mesh2_bounds)
        west_int_cellboxes = mesh2.get_left_edge_cellboxes()
        self.tie_western_cellbox_ng(west_ext_cellboxes, west_int_cellboxes)

    def validate_merge_compatibility(self, mesh2):
        """
            checks if the given mesh is compatible with merging with this mesh

            Args:
                mesh2 (EnvironmentMesh): the mesh to be checked for compatibility
            Returns:
                bool: True if the given mesh is compatible with merging with this mesh, False otherwise
        """

        # check if the bounds of the mesh to be merged is divisible by the cell width and height of this mesh
        l_cell_width = self.config['region']['cell_width']
        l_cell_height = self.config['region']['cell_height']

        m2_bounds_height = mesh2.bounds.get_height()
        m2_bounds_width = mesh2.bounds.get_width()

        if m2_bounds_height % l_cell_height != 0:
            return False
        if m2_bounds_width % l_cell_width != 0:
            return False

        # check if mesh2 is aligned with this mesh

        l_bounds = self.bounds
        s_bounds = mesh2.bounds

        lat_diff = l_bounds.get_lat_min() - s_bounds.get_lat_min()
        if lat_diff % l_cell_height != 0:
            return False

        long_diff = l_bounds.get_long_min() - s_bounds.get_long_min()
        if long_diff % l_cell_width != 0:
            return False 


        return True

    
    def tie_northern_cellbox_ng(self, north_ext_cellboxes, north_int_cellboxes):

        """
        Joins the neighbour graphs of sets of cellboxes on the northen edge of a boundary between two meshes.

        Args:
            north_ext_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly north of the northen edge of the boundary
            north_int_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly south of the northen edge of the boundary
        
        """

        # Tie northen exterior cellboxes to northen interior cellboxes
        for cellbox_l in north_ext_cellboxes:

            south_neighbours = []
            south_west_neighbours = []
            south_east_neighbours = []

            for cellbox_s in north_int_cellboxes:

                cb_l_bounds = cellbox_l.get_bounds()
                cb_s_bounds = cellbox_s.get_bounds()

                neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_l_bounds, cb_s_bounds)

                if (str(neighbour_case) == "4"):
                    south_neighbours.append(int(cellbox_s.get_id()))
                if (str(neighbour_case) == "-1"):
                    south_west_neighbours.append(int(cellbox_s.get_id()))
                if (str(neighbour_case) == "3"):
                    south_east_neighbours.append(int(cellbox_s.get_id()))
                
            for neighbour in south_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["4"].append(neighbour)
            for neighbour in south_west_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-1"].append(neighbour)
            for neighbour in south_east_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["3"].append(neighbour)
            
        # Tie northen interior cellboxes to northen exterior cellboxes

        for cellbox_s in north_int_cellboxes:

            north_neighbours = []
            north_west_neighbours = []
            north_east_neighbours = []

            for cellbox_l in north_ext_cellboxes:

                cb_l_bounds = cellbox_l.get_bounds()
                cb_s_bounds = cellbox_s.get_bounds()

                neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_s_bounds, cb_l_bounds)

                if (str(neighbour_case) == "-4"):
                    north_neighbours.append(int(cellbox_l.get_id()))
                if (str(neighbour_case) == "-3"):
                    north_west_neighbours.append(int(cellbox_l.get_id()))
                if (str(neighbour_case) == "1"):
                    north_east_neighbours.append(int(cellbox_l.get_id()))
                
            for neighbour in north_neighbours:
                self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-4"].append(neighbour)#
            for neighbour in north_west_neighbours:
                self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-3"].append(neighbour)
            for neighbour in north_east_neighbours:
                self.neighbour_graph.get_graph()[cellbox_s.get_id()]["1"].append(neighbour)

    def tie_southern_cellbox_ng(self, south_ext_cellboxes, south_int_cellboxes):
            
            """
            Joins the neighbour graphs of sets of cellboxes on the southern edge of a boundary between two meshes.
    
            Args:
                south_ext_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly south of the southern edge of the boundary
                south_int_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly north of the southern edge of the boundary
            
            """
    
            # Tie southern exterior cellboxes to southern interior cellboxes
            for cellbox_l in south_ext_cellboxes:
    
                north_neighbours = []
                north_west_neighbours = []
                north_east_neighbours = []
    
                for cellbox_s in south_int_cellboxes:
    
                    cb_l_bounds = cellbox_l.get_bounds()
                    cb_s_bounds = cellbox_s.get_bounds()
    
                    neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_l_bounds, cb_s_bounds)
    
                    if (str(neighbour_case) == "-4"):
                        north_neighbours.append(int(cellbox_s.get_id()))
                    if (str(neighbour_case) == "-3"):
                        north_west_neighbours.append(int(cellbox_s.get_id()))
                    if (str(neighbour_case) == "1"):
                        north_east_neighbours.append(int(cellbox_s.get_id()))
                    
                for neighbour in north_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-4"].append(neighbour)
                for neighbour in north_west_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-3"].append(neighbour)
                for neighbour in north_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["1"].append(neighbour)
                
            # Tie southern interior cellboxes to southern exterior cellboxes
    
            for cellbox_s in south_int_cellboxes:
                        
                south_neighbours = []
                south_west_neighbours = []
                south_east_neighbours = []
        
                for cellbox_l in south_ext_cellboxes:
        
                    cb_l_bounds = cellbox_l.get_bounds()
                    cb_s_bounds = cellbox_s.get_bounds()
        
                    neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_s_bounds, cb_l_bounds)
        
                    if (str(neighbour_case) == "4"):
                        south_neighbours.append(int(cellbox_l.get_id()))
                    if (str(neighbour_case) == "-1"):
                        south_west_neighbours.append(int(cellbox_l.get_id()))
                    if (str(neighbour_case) == "3"):
                        south_east_neighbours.append(int(cellbox_l.get_id()))
                        
                for neighbour in south_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["4"].append(neighbour)
                for neighbour in south_west_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-1"].append(neighbour)
                for neighbour in south_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["3"].append(neighbour)

    def tie_eastern_cellbox_ng(self, east_ext_cellboxes, east_int_cellboxes):

        """
        Joins the neighbour graphs of sets of cellboxes on the eastern edge of a boundary between two meshes.

        Args:
            east_ext_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly east of the eastern edge of the boundary
            east_int_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly west of the eastern edge of the boundary
        
        """

        # Tie eastern exterior cellboxes to eastern interior cellboxes
        for cellbox_l in east_ext_cellboxes:

            west_neighbours = []
            south_west_neighbours = []
            north_west_neighbours = []

            for cellbox_s in east_int_cellboxes:

                cb_l_bounds = cellbox_l.get_bounds()
                cb_s_bounds = cellbox_s.get_bounds()

                neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_l_bounds, cb_s_bounds)

                if (str(neighbour_case) == "-2"):
                    west_neighbours.append(int(cellbox_s.get_id()))
                if (str(neighbour_case) == "-1"):
                    south_west_neighbours.append(int(cellbox_s.get_id()))
                if (str(neighbour_case) == "-3"):
                    north_west_neighbours.append(int(cellbox_s.get_id()))
                
            for neighbour in west_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-2"].append(neighbour)
            for neighbour in south_west_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-1"].append(neighbour)
            for neighbour in north_west_neighbours:
                self.neighbour_graph.get_graph()[cellbox_l.get_id()]["-3"].append(neighbour)
            
        # Tie eastern interior cellboxes to eastern exterior cellboxes

        for cellbox_s in east_int_cellboxes:
                
                east_neighbours = []
                south_east_neighbours = []
                north_east_neighbours = []
    
                for cellbox_l in east_ext_cellboxes:
    
                    cb_l_bounds = cellbox_l.get_bounds()
                    cb_s_bounds = cellbox_s.get_bounds()
    
                    neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_s_bounds, cb_l_bounds)
    
                    if (str(neighbour_case) == "2"):
                        east_neighbours.append(int(cellbox_l.get_id()))
                    if (str(neighbour_case) == "3"):
                        south_east_neighbours.append(int(cellbox_l.get_id()))
                    if (str(neighbour_case) == "1"):
                        north_east_neighbours.append(int(cellbox_l.get_id()))
                    
                for neighbour in east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["2"].append(neighbour)
                for neighbour in south_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["3"].append(neighbour)
                for neighbour in north_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_s.get_id()]["1"].append(neighbour)

    def tie_western_cellbox_ng(self, west_ext_cellboxes, west_int_cellboxes):
            
            """
            Joins the neighbour graphs of sets of cellboxes on the western edge of a boundary between two meshes.
    
            Args:
                west_ext_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly west of the western edge of the boundary
                west_int_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly east of the western edge of the boundary
            
            """
    
            # Tie western exterior cellboxes to western interior cellboxes
            for cellbox_l in west_ext_cellboxes:
    
                east_neighbours = []
                south_east_neighbours = []
                north_east_neighbours = []
    
                for cellbox_s in west_int_cellboxes:
    
                    cb_l_bounds = cellbox_l.get_bounds()
                    cb_s_bounds = cellbox_s.get_bounds()
    
                    neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_l_bounds, cb_s_bounds)
    
                    if (str(neighbour_case) == "2"):
                        east_neighbours.append(int(cellbox_s.get_id()))
                    if (str(neighbour_case) == "3"):
                        south_east_neighbours.append(int(cellbox_s.get_id()))
                    if (str(neighbour_case) == "1"):
                        north_east_neighbours.append(int(cellbox_s.get_id()))
                    
                for neighbour in east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["2"].append(neighbour)
                for neighbour in south_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["3"].append(neighbour)
                for neighbour in north_east_neighbours:
                    self.neighbour_graph.get_graph()[cellbox_l.get_id()]["1"].append(neighbour)
                
            # Tie western interior cellboxes to western exterior cellboxes
    
            for cellbox_s in west_int_cellboxes:
                    
                    west_neighbours = []
                    south_west_neighbours = []
                    north_west_neighbours = []
        
                    for cellbox_l in west_ext_cellboxes:
        
                        cb_l_bounds = cellbox_l.get_bounds()
                        cb_s_bounds = cellbox_s.get_bounds()
        
                        neighbour_case = self.neighbour_graph.get_neighbour_case_bounds(cb_s_bounds, cb_l_bounds)
        
                        if (str(neighbour_case) == "-2"):
                            west_neighbours.append(int(cellbox_l.get_id()))
                        if (str(neighbour_case) == "-1"):
                            south_west_neighbours.append(int(cellbox_l.get_id()))
                        if (str(neighbour_case) == "-3"):
                            north_west_neighbours.append(int(cellbox_l.get_id()))

                    for neighbour in west_neighbours:
                        self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-2"].append(neighbour)
                    for neighbour in south_west_neighbours:
                        self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-1"].append(neighbour)
                    for neighbour in north_west_neighbours:
                        self.neighbour_graph.get_graph()[cellbox_s.get_id()]["-3"].append(neighbour)


    def get_cellboxes_within_bounds(self, bounds):
        """
            returns the cellboxes within the given bounds. 
            Only cellboxes that are completely within the given bounds are returned.

            Args:
                bounds (Boundary): the bounds encapsulating the cellboxes to be returned
            Returns:
                AggregatedCellBox[]: the cellboxes within the given bounds
        """
        cells_within_bounds = []
        
        for cellbox in self.agg_cellboxes:
            cb_bounds = cellbox.get_bounds()

            if (cb_bounds.get_long_min() >= bounds.get_long_min() and 
                cb_bounds.get_long_max() <= bounds.get_long_max() and 
                cb_bounds.get_lat_min() >= bounds.get_lat_min() and 
                cb_bounds.get_lat_max() <= bounds.get_lat_max()):
            
                cells_within_bounds.append(cellbox)

        return cells_within_bounds


    def get_cellboxes_north_of_bounds(self, bounds):
        """
            returns all cellboxes that are directly north of the given bounds.
            Only cellboxes which are touching the north edge of the boundary, 
            yet lie entirely outside of the boundary will be returned

            Args:
                bounds (Boundary): the bounds encapsulating the cellboxes to be returned
            Returns: 
                north_cellboxes (AggregatedCellBox[]): a list of cellboxes that are directly north of the given bounds
        """

        north_cellboxes = []

        for cellbox in self.agg_cellboxes:
            if (cellbox.get_bounds().get_lat_min() == bounds.get_lat_max() and
                cellbox.get_bounds().get_long_max() >= bounds.get_long_min() and
                cellbox.get_bounds().get_long_min() <= bounds.get_long_max()):
            
                north_cellboxes.append(cellbox)
            
        return north_cellboxes

    def get_cellboxes_south_of_bounds(self, bounds):

        south_cellboxes = []

        for cellbox in self.agg_cellboxes:
            if (cellbox.get_bounds().get_lat_max() == bounds.get_lat_min() and
                cellbox.get_bounds().get_long_max() >= bounds.get_long_min() and
                cellbox.get_bounds().get_long_min() <= bounds.get_long_max()):
            
                south_cellboxes.append(cellbox)
            
        return south_cellboxes

    def get_cellboxes_east_of_bounds(self, bounds):

        east_cellboxes = []

        for cellbox in self.agg_cellboxes:
            if (cellbox.get_bounds().get_long_min() == bounds.get_long_max() and
                cellbox.get_bounds().get_lat_min() >= bounds.get_lat_min() and
                cellbox.get_bounds().get_lat_max() <= bounds.get_lat_max()):
            
                east_cellboxes.append(cellbox)
            
        return east_cellboxes

    def get_cellboxes_west_of_bounds(self, bounds):
            
            west_cellboxes = []
    
            for cellbox in self.agg_cellboxes:
                if (cellbox.get_bounds().get_long_max() == bounds.get_long_min() and
                    cellbox.get_bounds().get_lat_min() >= bounds.get_lat_min() and
                    cellbox.get_bounds().get_lat_max() <= bounds.get_lat_max()):
                
                    west_cellboxes.append(cellbox)
                
            return west_cellboxes


    def get_top_edge_cellboxes(self):

        top_cellboxes = []
        mesh_bounds = self.bounds

        for cellbox in self.agg_cellboxes:
            cb_bounds = cellbox.get_bounds()

            if cb_bounds.get_lat_max() == mesh_bounds.get_lat_max():
                top_cellboxes.append(cellbox)
        
        return top_cellboxes
    
    def get_bottom_edge_cellboxes(self):

        bottom_cellboxes = []
        mesh_bounds = self.bounds

        for cellbox in self.agg_cellboxes:
            cb_bounds = cellbox.get_bounds()

            if cb_bounds.get_lat_min() == mesh_bounds.get_lat_min():
                bottom_cellboxes.append(cellbox)

        return bottom_cellboxes

    def get_right_edge_cellboxes(self):

        right_cellboxes = []
        mesh_bounds = self.bounds

        for cellbox in self.agg_cellboxes:
            cb_bounds = cellbox.get_bounds()

            if cb_bounds.get_long_max() == mesh_bounds.get_long_max():
                right_cellboxes.append(cellbox)

        return right_cellboxes

    def get_left_edge_cellboxes(self):

        left_cellboxes = []
        mesh_bounds = self.bounds

        for cellbox in self.agg_cellboxes:
            cb_bounds = cellbox.get_bounds()

            if cb_bounds.get_long_min() == mesh_bounds.get_long_min():
                left_cellboxes.append(cellbox)

        return left_cellboxes


    def remove_cellboxes_within_bounds(self, bounds):
        """
            removes the cellboxes within the given bounds. 
            Only cellboxes that are completely within the given bounds are removed.

            Args:
                bounds (Boundary): the bounds encapsulating the cellboxes to be removed
        """
        cells_within_bounds = self.get_cellboxes_within_bounds(bounds)
        for cellbox in cells_within_bounds:
            self.remove_cellbox(cellbox)
  
    def get_max_cellbox_id(self):
        """
            returns the maximum cellbox id in the mesh

            Returns:
                int: the maximum cellbox id
        """
        max_id = 0
        for cellbox in self.agg_cellboxes:
            if int(cellbox.get_id()) > max_id:
                max_id = int(cellbox.get_id())
        return max_id

    def remove_cellbox(self, cellbox):
        """
            removes the given cellbox from the mesh

            Args:
                cellbox (AggregatedCellBox): the cellbox to be removed
        """
        self.agg_cellboxes.remove(cellbox)

        self.neighbour_graph.remove_node_and_update_neighbours(cellbox.get_id())

    def add_cellbox(self, cellbox):
        """
            adds the given cellbox to the mesh
        """
        self.agg_cellboxes.append(cellbox)

    def increment_ids(self, increment):

        for cellbox in self.agg_cellboxes:
            cellbox.set_id(str(int(cellbox.get_id()) + increment))
            cellbox.agg_data['id'] = str(int(cellbox.get_id()) + increment)

        self.neighbour_graph.increment_ids(increment)
        
    # Splitting
    def sim_split_cellbox(self, cellbox_id):
        """
            splits the cellbox with the given id

            Args:
                cellbox_id (string): the id of the cellbox to be split
            Returns: 
                split_cells (list<AggregatedCellBox>): a list of the new cellboxes created by the split
        """
        cellbox = self.get_cellbox(cellbox_id)

        max_id = self.get_max_cellbox_id()

        # Copy agg_data, update id's
        agg_data = cellbox.get_agg_data()
        agg_data1 = agg_data.copy()
        agg_data1['id'] = str(max_id + 1)
        agg_data2 = agg_data.copy()
        agg_data2['id'] = str(max_id + 2)
        agg_data3 = agg_data.copy()
        agg_data3['id'] = str(max_id + 3)
        agg_data4 = agg_data.copy()
        agg_data4['id'] = str(max_id + 4)

        bounds = cellbox.get_bounds()
        split_bounds = bounds.split()

        cellbox1 = AggregatedCellBox(split_bounds[0], agg_data1, str(max_id + 1))
        cellbox2 = AggregatedCellBox(split_bounds[1], agg_data2, str(max_id + 2))
        cellbox3 = AggregatedCellBox(split_bounds[2], agg_data3, str(max_id + 3))
        cellbox4 = AggregatedCellBox(split_bounds[3], agg_data4, str(max_id + 4))

        return [cellbox1, cellbox2, cellbox3, cellbox4]

    def split_and_replace(self, cellbox_id):
        """
            splits the cellbox with the given id and replaces it with the new cellboxes

            Args:
                cellbox_id (string): the id of the cellbox to be split
        """
        
        # Create new cellboxes and append to agg_cellboxes
        split_cellboxes = self.sim_split_cellbox(cellbox_id)
        for cellbox in split_cellboxes:
            self.agg_cellboxes.append(cellbox)

        # get ID's of new cellboxes
        north_west_index = int(split_cellboxes[1].get_agg_data()['id'])
        north_east_index = int(split_cellboxes[3].get_agg_data()['id'])
        south_west_index = int(split_cellboxes[0].get_agg_data()['id'])
        south_east_index = int(split_cellboxes[2].get_agg_data()['id'])

        # Get neighbours of original cellbox
        south_neighbour_index = self.neighbour_graph.get_neighbours(cellbox_id, "4")
        north_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_id, "-4")
        east_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_id, "2")
        west_neighbour_indx = self.neighbour_graph.get_neighbours(cellbox_id, "-2")

        # ================== Create Neighbour Maps ==================
        # initialize the neighbour map of SW cellbox
        sw_neighbour_map = {
            "1": [north_east_index],
            "2": [south_east_index],
            "3": [], 
            "4": [],
            "-1": self.neighbour_graph.get_neighbours(cellbox_id, "-1"),
            "-2": [],
            "-3": [],
            "-4": [north_west_index]
        }
        # fill remaining neighbour map
        sw_neighbour_map = self.fill_sw_neighbour_map(sw_neighbour_map, south_west_index, south_neighbour_index, west_neighbour_indx)
        self.neighbour_graph.add_node(str(south_west_index), sw_neighbour_map)

        # initialize the neighbour map of NW cellbox
        nw_neighbour_map = {
            "1": [],
            "2": [north_east_index],
            "3": [south_east_index],
            "4": [south_west_index], 
            "-1": [], 
            "-2": [], 
            "-3": self.neighbour_graph.get_neighbours(cellbox_id, "-3"),
            "-4": []
        }
        # fill remaining neighbour map
        nw_neighbour_map = self.fill_nw_neighbour_map(nw_neighbour_map, north_west_index, north_neighbour_indx, west_neighbour_indx)
        self.neighbour_graph.add_node(str(north_west_index), nw_neighbour_map)

        # initialize the neighbour map of NE cellbox
        ne_neighbour_map = {
            "1": self.neighbour_graph.get_neighbours(cellbox_id, "1"),
            "2": [], 
            "3": [],
            "4": [south_east_index],
            "-1": [south_west_index],
            "-2": [north_west_index],
            "-3": [],
            "-4": []
        }
        # fill remaining neighbour map
        ne_neighbour_map = self.fill_ne_neighbour_map(ne_neighbour_map, north_east_index, north_neighbour_indx, east_neighbour_indx)
        self.neighbour_graph.add_node(str(north_east_index), ne_neighbour_map)

        # initialize the neighbour map of SE cellbox
        se_neighbour_map = {
            "1": [],
            "2": [],
            "3": self.neighbour_graph.get_neighbours(cellbox_id, "3"),
            "4": [],
            "-1": [],
            "-2": [south_west_index],
            "-3": [north_west_index],
            "-4": [north_east_index]
        }
        # fill remaining neighbour map
        se_neighbour_map = self.fill_se_neighbour_map(se_neighbour_map, south_east_index, south_neighbour_index, east_neighbour_indx)
        self.neighbour_graph.add_node(str(south_east_index), se_neighbour_map)

        # ================== Update Neighbours of original cellbox ==================

        # update corner neighbours
        ne_corner_index = self.neighbour_graph.get_neighbours(cellbox_id, "1")
        se_corner_index = self.neighbour_graph.get_neighbours(cellbox_id, "3")
        nw_corner_index = self.neighbour_graph.get_neighbours(cellbox_id, "-3")
        sw_corner_index = self.neighbour_graph.get_neighbours(cellbox_id, "-1")

        if len(ne_corner_index) > 0:
            self.neighbour_graph.update_neighbour(str(ne_corner_index[0]), "-1", [north_east_index])
        if len(se_corner_index) > 0:
            self.neighbour_graph.update_neighbour(str(se_corner_index[0]), "-3", [south_east_index])
        if len(nw_corner_index) > 0:
            self.neighbour_graph.update_neighbour(str(nw_corner_index[0]), "3", [north_west_index])
        if len(sw_corner_index) > 0:
            self.neighbour_graph.update_neighbour(str(sw_corner_index[0]), "1", [south_west_index])


        # update sides neighbours
        ne_bounds = self.get_cellbox(north_east_index).get_bounds()
        nw_bounds = self.get_cellbox(north_west_index).get_bounds()
        se_bounds = self.get_cellbox(south_east_index).get_bounds()
        sw_bounds = self.get_cellbox(south_west_index).get_bounds()
        
        # update north cellbox neighbours
        self.neighbour_graph.remove_node_from_neighbours(cellbox_id, -4)

        for indx in north_neighbour_indx:
            cellbox_bounds = self.get_cellbox(indx).get_bounds()

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, ne_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), north_east_index)
            
            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, nw_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), north_west_index)


        # update south cellbox neighbours
        self.neighbour_graph.remove_node_from_neighbours(cellbox_id, 4)
        
        for indx in south_neighbour_index:
            cellbox_bounds = self.get_cellbox(indx).get_bounds()

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, se_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), south_east_index)
            
            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, sw_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), south_west_index)


        # update east cellbox neighbours
        self.neighbour_graph.remove_node_from_neighbours(cellbox_id, 2)

        for indx in east_neighbour_indx:
            cellbox_bounds = self.get_cellbox(indx).get_bounds()

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, ne_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), north_east_index)

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, se_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), south_east_index)


        # update west cellbox neighbours
        self.neighbour_graph.remove_node_from_neighbours(cellbox_id, -2)

        for indx in west_neighbour_indx:
            cellbox_bounds = self.get_cellbox(indx).get_bounds()

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, nw_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), north_west_index)

            crossing_case = self.neighbour_graph.get_neighbour_case_bounds(cellbox_bounds, sw_bounds)
            if crossing_case != 0:
                self.neighbour_graph.add_neighbour(str(indx), str(crossing_case), south_west_index)


        # remove original cellbox from mesh.
        cellbox = self.get_cellbox(cellbox_id)
        self.agg_cellboxes.remove(cellbox)
        self.neighbour_graph.remove_node(cellbox_id)

    def fill_se_neighbour_map(self, se_neighbour_map, se_neighbour_id, south_neighbour_index, east_neighbour_indx):
        """
            fills the south east neighbour map with the given values
            Args: 
                se_neighbour_map (dict): the map to be filled
                se_neighbour_ID (string): the index of the south east cellbox
                south_neighbour_index (List<String>): the index of the south neighbours of the parent cellbox
                east_neighbour_indx (List<String>): the index of the east neighbour of the parent cellbox
            Returns:
                se_neighbour_map (dict): the filled map
        """
        se_bounds = self.get_cellbox(se_neighbour_id).get_bounds()

        for indx in south_neighbour_index:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(se_bounds, neighbour_bounds) == 4:
                se_neighbour_map["4"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(se_bounds, neighbour_bounds) == -1:
                se_neighbour_map["-1"].append(indx)

        for indx in east_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(se_bounds, neighbour_bounds) == 2:
                se_neighbour_map["2"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(se_bounds, neighbour_bounds) == 1:
                se_neighbour_map["1"].append(indx)

        return se_neighbour_map

    def fill_ne_neighbour_map(self, ne_neighbour_map, ne_neighbour_id, north_neighbour_indx, east_neighbour_indx):
        """
            fills the north east neighbour map with the given values
            Args: 
                ne_neighbour_map (dict): the map to be filled
                ne_neighbour_ID (string): the index of the north east cellbox
                north_neighbour_index (List<String>): the index of the north neighbours of the parent cellbox
                east_neighbour_indx (List<String>): the index of the east neighbour of the parent cellbox
            Returns:
                ne_neighbour_map (dict): the filled map
        """
        ne_bounds = self.get_cellbox(ne_neighbour_id).get_bounds()

        for indx in north_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(ne_bounds, neighbour_bounds) == -4:
                ne_neighbour_map["-4"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(ne_bounds, neighbour_bounds) == -3:
                ne_neighbour_map["-3"].append(indx)

        for indx in east_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(ne_bounds, neighbour_bounds) == 2:
                ne_neighbour_map["2"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(ne_bounds, neighbour_bounds) == 3:
                ne_neighbour_map["3"].append(indx)

        return ne_neighbour_map

    def fill_sw_neighbour_map(self, sw_neighbour_map, sw_neighbour_id, south_neighbour_index, west_neighbour_indx):
        """
            fills the south west neighbour map with the given values
            Args: 
                sw_neighbour_map (dict): the map to be filled
                sw_neighbour_ID (string): the index of the south west cellbox
                south_neighbour_index (List<String>): the index of the south neighbours of the parent cellbox
                west_neighbour_indx (List<String>): the index of the west neighbour of the parent cellbox
            Returns:
                sw_neighbour_map (dict): the filled map
        """
        sw_bounds = self.get_cellbox(sw_neighbour_id).get_bounds()

        for indx in south_neighbour_index:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(sw_bounds, neighbour_bounds) == 3:
                sw_neighbour_map["3"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(sw_bounds, neighbour_bounds) == 4:
                sw_neighbour_map["4"].append(indx)

        for indx in west_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(sw_bounds, neighbour_bounds) == -2:
                sw_neighbour_map["-2"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(sw_bounds, neighbour_bounds) == -3:
                sw_neighbour_map["-3"].append(indx)

        return sw_neighbour_map

    def fill_nw_neighbour_map(self, nw_neighbour_map, nw_neighbour_id, north_neighbour_indx, west_neighbour_indx):
        """
            fills the north west neighbour map with the given values
            Args: 
                nw_neighbour_map (dict): the map to be filled
                nw_neighbour_ID (string): the index of the north west cellbox
                north_neighbour_index (List<String>): the index of the north neighbours of the parent cellbox
                west_neighbour_indx (List<String>): the index of the west neighbour of the parent cellbox
            Returns:
                nw_neighbour_map (dict): the filled map
        """
        nw_bounds = self.get_cellbox(nw_neighbour_id).get_bounds()

        for indx in north_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(nw_bounds, neighbour_bounds) == -4:
                nw_neighbour_map["-4"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(nw_bounds, neighbour_bounds) == 1:
                nw_neighbour_map["1"].append(indx)

        for indx in west_neighbour_indx:
            neighbour_bounds = self.get_cellbox(indx).get_bounds()
            if self.neighbour_graph.get_neighbour_case_bounds(nw_bounds, neighbour_bounds) == -2:
                nw_neighbour_map["-2"].append(indx)
            if self.neighbour_graph.get_neighbour_case_bounds(nw_bounds, neighbour_bounds) == -1:
                nw_neighbour_map["-1"].append(indx)

        return nw_neighbour_map


    def to_json(self):
        """
            Returns this Mesh converted to a JSON object.\n

            Returns:
                json: a string representation of the CellGird parseable as a JSON object. The JSON object is of the form -\n

                    {\n
                        "config": the config used to initialize the Mesh,\n
                        "cellboxes": a list of CellBoxes contained within the Mesh,\n
                        "neighbour_graph": a graph representing the adjacency of CellBoxes within the Mesh.\n
                    }\n
        """
        output = dict()
        output['config'] = {'mesh_info': self.config}
        output["cellboxes"] = self.cellboxes_to_json()
        output['neighbour_graph'] = self.neighbour_graph.get_graph()


        return json.loads(json.dumps(output, indent=4))
    
    def to_shapely(self):

        msh_shapely =  gpd.GeoDataFrame(pd.DataFrame(self.cellboxes_to_json())).set_index('id')
        msh_shapely['geometry'] = msh_shapely['geometry'].apply(wkt.loads)
        msh_shapely = gpd.GeoDataFrame(msh_shapely, crs='EPSG:4326', geometry='geometry')
        return msh_shapely


    def to_png(self, params_file, path):
        """
            exports a mesh and saves to a png file
            Args:
                params_file: A format configuration files as a json object
                path: The path to save the png file
        """
        from meshiphi.mesh_plotting.mesh_plotter import MeshPlotter

        mesh_json = self.to_json()
        plotter = MeshPlotter(mesh_json)

        if (params_file != None):
            with open(params_file) as f:
                data = f.read()
                format_params = json.loads(data)

        for item in format_params['cmaps']:
            plotter.plot_cmap(item['data_name'], item['cmap'])
        for item in format_params['bools']:
            plotter.plot_bool(item['data_name'], item['colour'])
            
        plotter.save(path)

    def to_geojson(self, params_file = None):
        """
            Returns the cellboxes of this mesh converted to a geoJSON format.\n

            Returns:
                geojson: The cellboxes of this mesh in a geoJSON format

            NOTE:
                geoJSON format does not contain all the data included in the standard 
                .to_json() format. geoJSON meshes do not contain the configs used to 
                build them, or the neighbour-graph which details how each of the 
                cellboxes are connected together.\n
        """
        geojson = ""
        mesh_json = self.to_json()

        if (params_file != None):
            with open(params_file) as f:
                data = f.read()
                format_params = json.loads(data)
            data_name = format_params['data_name']
            logging.info("exporting layer : " + str(data_name))

        # Formatting mesh to geoJSON
        mesh_df = pd.DataFrame(mesh_json['cellboxes'])

        for column in mesh_df.columns:

            if column in ['id', 'geometry']:
                continue
            # remove unnecessary columns
            if (params_file != None) and column not in [str(data_name)]:
                mesh_df = mesh_df.drop(column, axis=1)
            # remove unnecessary columns
            elif column in ['cx', 'cy', 'dcx', 'dcy']:
                mesh_df = mesh_df.drop(column, axis=1)
            # convert lists to mean
            elif mesh_df[column].dtype == list:
                mesh_df[column] = [np.mean(x) for x in mesh_df[column]]
            # convert bools to ints
            elif mesh_df[column].dtype == bool:
                mesh_df[column] = mesh_df[column].astype(int)
                mesh_df[column] = mesh_df[column].replace(0, np.nan)
            
        # Remove infs and replace with nan
        mesh_df = mesh_df.replace([np.inf, -np.inf], np.nan)

        mesh_df['geometry'] = mesh_df['geometry'].apply(wkt.loads)
        mesh_gdf = gpd.GeoDataFrame(
            mesh_df, crs="EPSG:4326", geometry="geometry")
        geojson = json.loads(mesh_gdf.to_json())

        return geojson

    def to_tif(self, params_file,  path):
        """
                generates a representation of the mesh in geotif image format.\n

                Args:
                    params_file(string) (optional): a path to a file that contains a dict of the folowing export parameters (If not given, default values are used for image export). The file should be of the following format -\n
                            \n
                            {\n
                                "data_name": "elevation",\n
                                "sampling_resolution": [\n
                                    150,\n
                                    150\n
                                 ],\n
                                "projection": "3031",\n
                            }\n
                            Where data_name (string) is the name of the mesh data that will be included in the tif image (ex. SIC, elevation), if it is a vector data (e.g. fuel) then the vector mean is calculated for each pixel,
                            sampling_resolution ([int]) is a 2d array that represents the sampling resolution the geotiff will be generated at (how many pixels in the final image),
                            projection (int) is an int representing the ESPG sampling projection used to create the geotiff image  (default is 4326),
                            and colour_conf (string) contains the path to color config file, which is a text-based file containing the association between data_name values and colors. It contains 4 columns per line: the data_name value and the corresponding red, green, blue value between 0 and 255, an example format where values range from 0 to 100 is -\n
                                    \n
                                    0 240 250 160  \n
                                    30 230 220 170  \n
                                    60 220 220 220 \n
                                    100 250 250 250  \n
                    path (string): the path to save the generated tif image.\n
        """
        def generate_samples():
            """
                generates uniform lat, long samples covering the image resolution space.\n

                Returns:
                    samples([[lat,long],..]): an array of samples, each item in the array is a 2d array that contains each sample lat and long.\n

            """
            mesh_height = self.bounds.get_lat_max() - self.bounds.get_lat_min()
            mesh_width = self.bounds.get_long_max() - self.bounds.get_long_min()
            pixel_height = mesh_height / ncols
            pixel_width = mesh_width / nlines
            samples = []
            # has to move in this direction as we start rendering from the upper left pixel
            for lat in np.arange(self.bounds.get_lat_max(), self.bounds.get_lat_min(), -1*pixel_height):
                for long in np.arange(self.bounds.get_long_min(), self.bounds.get_long_max(), pixel_width):
                    pixel_lat = lat - 0.5 * pixel_height   # centeralize the pixel lat value
                    pixel_long = long + 0.5*pixel_width   # centeralize the pixel long value
                    samples = np.append(samples, pixel_lat)
                    samples = np.append(samples, pixel_long)
            # shape the samples in 2d array (each entry in the array holds sample lat and long
            samples = np.reshape(samples, (nlines * ncols, 2))
            return samples

        def get_sample_value(sample):
            """
                finds the aggregated cellbox that contains the sample lat and long and returns the value within.\n

                Args:
                    sample ([lat,long]): an array conatins the sample latitude and longtitude
                Returns:
                    the aggregated value of 'data_name'(specified in to_tif params) 

             """
            lat = sample[0]
            long = sample[1]
            value = np.nan
            for agg_cellbox in self.agg_cellboxes:
                if agg_cellbox.contains_point(lat, long):
                    # get the agg_value
                    try:
                        value = agg_cellbox.agg_data[data_name]
                    except KeyError:
                        logging.debug(f'{data_name} not found in cellbox!')
                        value = np.nan
                        
                    if isinstance(value, collections.abc.Sequence): # if it is a vector then take the mean
                        value = np.mean (value)
                        if value == float('inf') : # repalce inf with nan
                            value = np.nan
                    # break to make sure we avoid getting multiple values (for lat and long on the bounds of multiple cellboxes)
                    break
            return value

        def get_geo_transform(extent, nlines, ncols):
            """
                transforms from the image coordinate space (row, column) to the georeferenced coordinate space. \n
                Returns:    
                  GT : array consists of 6 items representing how GDAL would place the top left pixel on the generated Geotiff:\n
                  GT[0] x-coordinate of the upper-left corner of the upper-left pixel.\n
                  GT[1] w-e pixel resolution / pixel width.\n
                  GT[2] row rotation (typically zero).\n
                  GT[3] y-coordinate of the upper-left corner of the upper-left pixel.\n
                  GT[4] column rotation (typically zero).\n
                  GT[5] n-s pixel resolution / pixel height (negative value for a north-up image).\n

            """
            resx = (extent[2] - extent[0]) / ncols
            resy = (extent[3] - extent[1]) / nlines
            return [extent[0], resx, 0, extent[3], 0, -resy]

        def load_params(params_file):
            """
                  loads the parameters of the tif export and override the default values.\n

                  Args:
                      params_file (string): a path to a file containing a dict of the export params 
                  
                  Returns:
                      params (dict): a dict object that contains the loaded parameters

            """
            params = {"data_name": "SIC", "sampling_resolution": [
                100, 100], "projection": "4326"}  # the default values
            if (params_file != None):
                with open(params_file) as f:
                    data = f.read()
                    input_params = json.loads(data)
                if (input_params != None):
                    if ("projection" in input_params.keys()):
                        params["projection"] = input_params["projection"]
                    if ("data_name" in input_params.keys()):
                        params["data_name"] = input_params["data_name"]
                    if ("sampling_resolution" in input_params.keys()):
                        params["sampling_resolution"] = input_params["sampling_resolution"]
                    if ("colour_conf" in input_params.keys()):
                        params["colour_conf"] = input_params["colour_conf"]
            return params

        def transform_proj(path, params, default_proj):
            """
                  method that transforms the generated tif into another projection

                  Args:
                        path(string): the path of the generated tif
                        params (dict): a dict that contains the export parametrs
                        default_proj (stirng): a string represents the default projection (EPSG:4326).\n

            """
            if params["projection"] != str(default_proj):
                dest = osr.SpatialReference()
                dest.ImportFromEPSG(int(params["projection"]))
                # transform to target proj and save
                gdal.Warp(str(path),  str(path), dstSRS=dest.ExportToWkt())
        
        def set_colour(data, input_file, params):
            """
                  method that changes the color of the generated tif instead of using the default greyscale.
                  It defines a scale of RGB colors based on the range of data values(an example file is in unit_tests/resources/colour_conf.txt).\n

                  Args:
                        data ([float]): an array conatins the values of the 'data_name'
                        input_path(string): the path of the generated grey tif
                        params (dict): a dict that contains the export parametrs.\n

            """
            fp, color_file = tempfile.mkstemp(suffix='.txt')
            data = data[~np.isnan(data)]  # get rid of the nans before calculating range
            _max = np.nanmax(data)
            _min = np.nanmin(data)
            _range = _max-_min
            inf_color = '255 0 0' # red color for inf value
            colors = ['255 255 255', '173 216 230', '0 0 128', '0 0 139']  # default color
            with open(color_file, 'w') as f:
                for i, c in enumerate(colors[:-1]):
                    f.write(str(int(_min + (i + 1)*_range/len(colors))) +
                            ' ' + c + '\n')
                f.write(str(int(_max - _range/len(colors))) +
                        ' ' + colors[-1] + '\n')
                f.write (str(np.nan) +
                        ' ' + inf_color + '\n') # render nans in red
            os.close(fp)
            if "colour_conf" in params.keys():
                color_file = params["colour_conf"]
            cmd = "gdaldem color-relief " + input_file \
                + ' ' + color_file + ' ' + input_file
            subprocess.check_call(cmd, shell=True)
            # remove additional files created while generating the tif
            file_path = os.path.abspath(input_file)
            dir_path = os.path.split(file_path)[0]
            additional_files = ["grid_data" , "grid_data.aux.xml"]
            for file in additional_files: 
                file_path = Path(dir_path +"/"+ file)
                if os.path.isfile (file_path):
                     os.remove(file_path)

        # Only import if we need GDAL, to avoid having it as a requirement
        from osgeo import gdal, ogr, osr
        
        params = {}
        params = load_params(params_file)
        data_name = params["data_name"]
        DEFAULT_PROJ = 4326

        # Get image dimensions
        nlines = params["sampling_resolution"][0]
        ncols = params["sampling_resolution"][1]

        # define image extent based on mesh bounds
        extent = [self.bounds.get_long_min(), self.bounds.get_lat_min(
        ), self.bounds.get_long_max(), self.bounds.get_lat_max()]

        logging.info("Generating the tif image ...")
        samples = generate_samples()
        # create raster band and populate with sampled data of image_size (sampling_resolution)
        driver = gdal.GetDriverByName('GTiff')
        # reading the samples value
        data = []
        data = np.reshape(np.asarray([get_sample_value(
            sample) for sample in samples], dtype=np.float32), (nlines, ncols))
        # create a temp grid
        grid_data = driver.Create(
            'grid_data', ncols, nlines, 1, gdal.GDT_Float32)
        # setup geo-transform
        grid_data.SetGeoTransform(get_geo_transform(extent, nlines, ncols))
        # Write data
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(DEFAULT_PROJ)
        grid_data.SetProjection(srs.ExportToWkt())
        grid_data.GetRasterBand(1).WriteArray(data)
    

        # Save the file
        driver.CreateCopy(path, grid_data, 0)
        transform_proj(path, params, DEFAULT_PROJ)
        set_colour(data, path, params)
        logging.info(f'Generated GeoTIFF: {path}')

    def cellboxes_to_json(self):
        """
            returns a list of dictionaries containing information about each cellbox
            in this Mesh.
            all cellboxes will include id, geometry, cx, cy, dcx, dcy

            Returns:
                cellboxes (list<dict>): a list of CellBoxes which form the Mesh.
                    CellBoxes are of the form -

                    {
                        "id": (string) ... \n
                        "geometry": (string) POLYGON(...), \n
                        "cx": (float) ..., \n
                        "cy": (float) ..., \n
                        "dcx": (float) ..., \n
                        "dcy": (float) ..., \n
                        \n
                        "value_1": (float) ..., \n
                        ..., \n
                        "value_n": (float) ... \n
                    }
        """

        cellboxes_json = []
        for cellbox in self.agg_cellboxes:

            # Get json for CellBox
            cell = cellbox.to_json()

            cellboxes_json.append(cell)
        return cellboxes_json

    def update_cellbox(self, index, values):
        """
            method that adds values to the dict of a cellbox at certain index (to be used by the vessel perf. module to add the perf. metrics to the cellbox)

            Args:
              index (int): the index of the cellbox to be updated
              values (dict): a dict contains perf. metrics names and values
        """
        if index > -1 or index < len(self.agg_cellboxes):
            self.agg_cellboxes[index].agg_data.update(values)
        else:
            raise ValueError('Invalid cellbox index')

    def save(self, path, format="JSON", format_params=None):
        """
            Saves this object to a location in local storage in a specific format. 

            Args:
                path (String): The file location the mesh will be saved to.
                format (String) (optional): The format the mesh will be saved in.
                    If not format is given, default is JSON.
                    Supported formats are\n
                        - JSON \n
                        - GEOJSON
        """

        logging.info(f"Saving mesh in {format} format to {path}")
        if format.upper() == "TIF":
            self.to_tif(format_params, path)

        elif format.upper() == "JSON":
            with open(path, 'w') as path:
                json.dump(self.to_json(), path, indent=4)
           
        elif format.upper() == "GEOJSON":
            with open(path, 'w') as path:
                json.dump(self.to_geojson(format_params), path, indent=4)

        elif format.upper() == "PNG":
            self.to_png(format_params, path)

        else:
            logging.warning(f"Cannot save mesh in a {format} format")

