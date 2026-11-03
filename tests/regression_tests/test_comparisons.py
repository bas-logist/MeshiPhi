"""
Comparison functions for regression testing mesh components.

This module provides functions for testing cellbox and neighbour graph
consistency between old and new mesh versions.
"""

import pandas as pd
import pytest

from .utils import extract_common_boundaries_for_comparison, round_dataframe_values

# Apply markers to all tests in this module
pytestmark = pytest.mark.slow


# Cellbox comparison test functions


def test_mesh_cellbox_count(mesh_pair):
    """
    Test that cellbox count is preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If cellbox counts differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_mesh = mesh_a["cellboxes"]
    new_mesh = mesh_b["cellboxes"]

    cellbox_count_a = len(regression_mesh)
    cellbox_count_b = len(new_mesh)

    assert cellbox_count_a == cellbox_count_b, (
        f"Incorrect number of cellboxes in new mesh. Expected: {cellbox_count_a}, got: {cellbox_count_b}"
    )


def test_mesh_cellbox_ids(mesh_pair):
    """
    Test that cellbox IDs are preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If any cellbox IDs differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_mesh = mesh_a["cellboxes"]
    new_mesh = mesh_b["cellboxes"]

    indxed_a = {cellbox["id"]: cellbox for cellbox in regression_mesh}
    indxed_b = {cellbox["id"]: cellbox for cellbox in new_mesh}

    regression_mesh_ids = set(indxed_a.keys())
    new_mesh_ids = set(indxed_b.keys())

    missing_a_ids = list(new_mesh_ids - regression_mesh_ids)
    missing_b_ids = list(regression_mesh_ids - new_mesh_ids)

    assert set(indxed_a) == set(indxed_b), (
        f"Mismatch in cellbox IDs. ID's {missing_a_ids} have appeared in the new mesh. "
        f"ID's {missing_b_ids} are missing from the new mesh"
    )


def test_mesh_cellbox_values(mesh_pair):
    """
    Test that cellbox values are preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If any values of any attributes differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    # Retrieve cellboxes from meshes as dataframes
    df_a = pd.DataFrame(mesh_a["cellboxes"]).set_index("geometry")
    df_b = pd.DataFrame(mesh_b["cellboxes"]).set_index("geometry")

    # Extract only cellboxes with same boundaries, drop ID as it may differ
    common_bounds = extract_common_boundaries_for_comparison(mesh_a, mesh_b)
    df_a = df_a.loc[common_bounds].drop(columns=["id"])
    df_b = df_b.loc[common_bounds].drop(columns=["id"])

    # Round values to significant figures for comparison
    df_a = round_dataframe_values(df_a)
    df_b = round_dataframe_values(df_b)

    # Find differences
    diff = df_a.compare(df_b).rename({"self": "old", "other": "new"})

    assert diff.empty, (
        f"Mismatch between values in common cellboxes:\n{diff.to_string(max_colwidth=10)}"
    )


def test_mesh_cellbox_attributes(mesh_pair):
    """
    Test that cellbox attributes are preserved between mesh versions.

    Note:
        Assumes all cellboxes in a mesh have the same attributes,
        so only compares the first cellbox from each mesh.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If cellbox attributes differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_mesh = mesh_a["cellboxes"]
    new_mesh = mesh_b["cellboxes"]

    regression_mesh_attributes = set(regression_mesh[0].keys())
    new_mesh_attributes = set(new_mesh[0].keys())

    missing_a_attributes = list(new_mesh_attributes - regression_mesh_attributes)
    missing_b_attributes = list(regression_mesh_attributes - new_mesh_attributes)

    assert regression_mesh_attributes == new_mesh_attributes, (
        f"Mismatch in cellbox attributes. Attributes {missing_a_attributes} have appeared in the new mesh. "
        f"Attributes {missing_b_attributes} are missing in the new mesh"
    )


# Neighbour graph comparison test functions


def test_mesh_neighbour_graph_count(mesh_pair):
    """
    Test that neighbour graph node count is preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If node counts differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_graph = mesh_a["neighbour_graph"]
    new_graph = mesh_b["neighbour_graph"]

    regression_graph_count = len(regression_graph.keys())
    new_graph_count = len(new_graph.keys())

    assert regression_graph_count == new_graph_count, (
        f"Incorrect number of nodes in neighbour graph. Expected: {regression_graph_count} nodes, "
        f"got: {new_graph_count} nodes."
    )


def test_mesh_neighbour_graph_ids(mesh_pair):
    """
    Test that neighbour graph node IDs are preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If node IDs differ
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_graph = mesh_a["neighbour_graph"]
    new_graph = mesh_b["neighbour_graph"]

    regression_graph_ids = set(regression_graph.keys())
    new_graph_ids = set(new_graph.keys())

    missing_a_keys = list(new_graph_ids - regression_graph_ids)
    missing_b_keys = list(regression_graph_ids - new_graph_ids)

    assert regression_graph_ids == new_graph_ids, (
        f"Mismatch in neighbour graph nodes. {len(missing_a_keys)} nodes have appeared in the new graph. "
        f"{len(missing_b_keys)} nodes are missing from the new graph."
    )


def test_mesh_neighbour_graph_values(mesh_pair):
    """
    Test that neighbour graph edge values are preserved between mesh versions.

    Args:
        mesh_pair (dict): Fixture containing old_mesh and new_mesh

    Raises:
        AssertionError: If neighbour sets differ for any node
    """
    mesh_a = mesh_pair["old_mesh"]
    mesh_b = mesh_pair["new_mesh"]

    regression_graph = mesh_a["neighbour_graph"]
    new_graph = mesh_b["neighbour_graph"]

    mismatch_neighbours = {}

    for node in regression_graph:
        # Prevent crashing if node not found (will be detected by test_neighbour_graph_ids)
        if node in new_graph:
            neighbours_a = regression_graph[node]
            neighbours_b = new_graph[node]

            # Sort the lists of neighbours as ordering is not important
            sorted_neighbours_a = {k: sorted(neighbours_a[k]) for k in neighbours_a}
            sorted_neighbours_b = {k: sorted(neighbours_b[k]) for k in neighbours_b}

            if sorted_neighbours_b != sorted_neighbours_a:
                mismatch_neighbours[node] = sorted_neighbours_b

    assert not mismatch_neighbours, (
        f"Mismatch in neighbour graph neighbours. {len(mismatch_neighbours)} nodes "
        f"have changed in the new mesh."
    )
