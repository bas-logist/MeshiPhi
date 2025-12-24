"""
Utility functions for regression testing.

This module contains helper functions for extracting and comparing mesh components.
"""

import pandas as pd
from meshiphi.utils import round_to_sigfig

SIG_FIG_TOLERANCE = 4


def extract_neighbour_graph(mesh_json):
    """
    Extracts the neighbour graph from a mesh JSON object.

    Args:
        mesh_json (dict): Mesh JSON containing neighbour graph information

    Returns:
        dict: Neighbour graph from mesh
    """
    return mesh_json['neighbour_graph']


def extract_cellboxes(mesh_json):
    """
    Extracts cellboxes from a mesh JSON object.

    Args:
        mesh_json (dict): Mesh JSON containing cellbox information

    Returns:
        list: List of cellboxes from mesh
    """
    return mesh_json['cellboxes']


def extract_common_boundaries(mesh_json):
    """
    Extracts common boundaries from mesh config to narrow cellbox attribute checks.

    Args:
        mesh_json (dict): Mesh JSON containing configuration information

    Returns:
        set: Set of common boundaries (keys) present in all cellboxes
    """
    if not mesh_json['cellboxes']:
        return set()

    # Start with first cellbox's keys
    common_boundaries = set(mesh_json['cellboxes'][0]['geometry'].keys())
    
    # Intersect with keys from remaining cellboxes
    for cellbox in mesh_json['cellboxes'][1:]:
        common_boundaries &= set(cellbox['geometry'].keys())
    
    return common_boundaries


def round_dataframe_values(df):
    """
    Helper function to round float and list-of-float values in a dataframe.

    Args:
        df (DataFrame): Pandas dataframe to round values in

    Returns:
        DataFrame: Modified dataframe with rounded values
    """
    # Round float columns to sig figs
    float_cols = df.select_dtypes(include=float).columns
    for col in float_cols:
        df[col] = round_to_sigfig(df[col].to_numpy(), sigfig=SIG_FIG_TOLERANCE)
    
    # Round list columns that contain floats
    list_cols = df.select_dtypes(include=list).columns
    for col in list_cols:
        round_col = []
        for val in df[col]:
            if isinstance(val, list) and all(isinstance(x, float) for x in val):
                round_col.append(round_to_sigfig(val, sigfig=SIG_FIG_TOLERANCE))
            else:
                round_col.append(val)
        df[col] = round_col
    
    return df


def extract_common_boundaries_for_comparison(mesh_a, mesh_b):
    """
    Creates a list of common geometry boundaries between two mesh JSONs.

    Args:
        mesh_a (dict): First mesh JSON to extract boundaries from
        mesh_b (dict): Second mesh JSON to extract boundaries from

    Returns:
        list: List of common cellbox geometries (as strings)
    """
    bounds_a = [cb['geometry'] for cb in extract_cellboxes(mesh_a)]
    bounds_b = [cb['geometry'] for cb in extract_cellboxes(mesh_b)]

    common_bounds = [geom for geom in bounds_a if geom in bounds_b]

    return common_bounds
