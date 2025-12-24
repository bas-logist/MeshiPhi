"""
Test utilities module containing helper functions and fixtures used across test suite.
This module consolidates reusable test helpers to follow DRY principles.
"""

import json
import copy
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.dataloaders.factory import DataLoaderFactory
from meshiphi.mesh_generation.cellbox import CellBox
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph


def create_cellbox(bounds, id=0, parent=None, params=None, splitting_conds=None, min_dp=5):
    """
    Helper function that simplifies creation of test cases

    Args:
        bounds (Boundary): Boundary of cellbox
        id (int, optional): Cellbox ID to initialise. Defaults to 0.
        parent (CellBox, optional): Cellbox to link as a parent. Defaults to None.
        params (dict, optional): Parameters for dataloader. Defaults to None.
        splitting_conds (list, optional): Splitting conditions. Defaults to None.
        min_dp (int, optional): Minimum datapoints. Defaults to 5.

    Returns:
        CellBox: Cellbox with completed attributes
    """
    dataloader = create_dataloader(bounds, params, min_dp=min_dp)
    metadata = create_metadata(bounds, dataloader, splitting_conds=splitting_conds)

    new_cellbox = CellBox(bounds, id)
    new_cellbox.data_source = [metadata]
    new_cellbox.parent = parent
    
    return new_cellbox


def create_dataloader(bounds, params=None, min_dp=5):
    """
    Create a dataloader for testing.
    
    Args:
        bounds (Boundary): Boundary for the dataloader
        params (dict, optional): Dataloader parameters. Defaults to None.
        min_dp (int, optional): Minimum datapoints. Defaults to 5.
    
    Returns:
        DataLoader: Configured dataloader instance
    """
    if params is None:
        params = {
            'dataloader_name': 'rectangle',
            'data_name': 'dummy_data',
            'width': bounds.get_width()/4,
            'height': bounds.get_height()/4,
            'centre': (bounds.getcx(), bounds.getcy()),
            'nx': 15,
            'ny': 15,
            "aggregate_type": "MEAN",
            "value_fill_type": 'parent'
        }
    dataloader = DataLoaderFactory().get_dataloader(params['dataloader_name'],
                                                    bounds,
                                                    params,
                                                    min_dp=min_dp)
    return dataloader


def create_metadata(bounds, dataloader, splitting_conds=None):
    """
    Create metadata for testing.
    
    Args:
        bounds (Boundary): Boundary for the metadata
        dataloader (DataLoader): Dataloader instance
        splitting_conds (list, optional): Splitting conditions. Defaults to None.
    
    Returns:
        Metadata: Configured metadata instance
    """
    if splitting_conds is None:
        splitting_conds = [{
            'threshold': 0.5,
            'upper_bound': 0.75,
            'lower_bound': 0.25
        }]
    data_source = Metadata(dataloader,
                           splitting_conditions=splitting_conds,
                           value_fill_type='parent',
                           data_subset=dataloader.trim_datapoints(bounds))
    return data_source


def compare_cellbox_lists(s, t):
    """
    Compare two lists of cellboxes for equality (order-independent).
    
    Args:
        s (list): First list of cellboxes
        t (list): Second list of cellboxes
    
    Returns:
        bool: True if lists contain same elements, False otherwise
    """
    t = list(t)   # make a mutable copy
    try:
        for elem in s:
            t.remove(elem)
    except ValueError:
        return False
    return not t


def json_dict_to_file(json_dict, filename):
    """
    Converts a dictionary to a JSON formatted file

    Args:
        json_dict (dict): Dict to write to JSON
        filename (str): Path to file being written
    """
    with open(filename, 'w') as fp:
        json.dump(json_dict, fp, indent=4)


def file_to_json_dict(filename):
    """
    Reads in a JSON file and returns dict of contents

    Args:
        filename (str): Path to file to be read

    Returns:
        dict: Dictionary with JSON contents
    """
    with open(filename, 'r') as fp:
        json_dict = json.load(fp)
    return json_dict


def create_ng_from_dict(ng_dict, global_mesh=False):
    """
    Create a NeighbourGraph from a dictionary.
    
    Args:
        ng_dict (dict): Dictionary representation of neighbour graph
        global_mesh (bool, optional): Whether this is a global mesh. Defaults to False.
    
    Returns:
        NeighbourGraph: Configured neighbour graph instance
    """
    ng = NeighbourGraph()
    ng.neighbour_graph = copy.deepcopy(ng_dict)
    ng._is_global_mesh = global_mesh
    return ng
