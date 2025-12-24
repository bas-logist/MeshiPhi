"""
Utility functions for regression testing.

This module contains helper functions for extracting and comparing mesh components.
"""


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
