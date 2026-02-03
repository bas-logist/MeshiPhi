"""
Shared pytest configuration and constants for MeshiPhi tests.
"""

import copy
import json
import logging
import os
import time
from pathlib import Path

import pytest

import meshiphi
from meshiphi.dataloaders.factory import DataLoaderFactory
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.cellbox import CellBox
from meshiphi.mesh_generation.metadata import Metadata
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph

# Logger for test execution
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# Significant figure tolerance for regression test comparisons
SIG_FIG_TOLERANCE = 4

# Test directory paths
TESTS_DIR = Path(__file__).parent
REGRESSION_TESTS_DIR = TESTS_DIR / "regression_tests"
UNIT_TESTS_DIR = TESTS_DIR / "unit_tests"

# File locations of all meshes to be recalculated for regression testing
TEST_ENV_MESHES = [
    "grf_normal.json",
    "grf_downsample.json",
    "grf_reprojection.json",
    "grf_sparse.json",
]

TEST_ABSTRACT_MESHES = [
    "vgrad.json",
    "hgrad.json",
    "checkerboard_1.json",
    "checkerboard_2.json",
    "checkerboard_3.json",
    "circle.json",
    "circle_quadrant_split.json",
    "circle_quadrant_nosplit.json",
]

# Build full paths
ALL_TEST_MESHES = [
    str(REGRESSION_TESTS_DIR / "example_meshes/env_meshes" / mesh) for mesh in TEST_ENV_MESHES
] + [
    str(REGRESSION_TESTS_DIR / "example_meshes/abstract_env_meshes" / mesh)
    for mesh in TEST_ABSTRACT_MESHES
]


# Unit test helper functions
def create_cellbox(bounds, id=0, parent=None, params=None, splitting_conds=None, min_dp=5):
    """
    Helper function that simplifies creation of test cases.

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
            "dataloader_name": "rectangle",
            "data_name": "dummy_data",
            "width": bounds.get_width() / 4,
            "height": bounds.get_height() / 4,
            "centre": (bounds.getcx(), bounds.getcy()),
            "nx": 15,
            "ny": 15,
            "aggregate_type": "MEAN",
            "value_fill_type": "parent",
        }
    return DataLoaderFactory().get_dataloader(
        params["dataloader_name"], bounds, params, min_dp=min_dp
    )


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
        splitting_conds = [{"threshold": 0.5, "upper_bound": 0.75, "lower_bound": 0.25}]
    return Metadata(
        dataloader,
        splitting_conditions=splitting_conds,
        value_fill_type="parent",
        data_subset=dataloader.trim_datapoints(bounds),
    )


def compare_cellbox_lists(s, t):
    """
    Compare two lists of cellboxes for equality (order-independent).

    Args:
        s (list): First list of cellboxes
        t (list): Second list of cellboxes

    Returns:
        bool: True if lists contain same elements, False otherwise
    """
    t = list(t)  # make a mutable copy
    try:
        for elem in s:
            t.remove(elem)
    except ValueError:
        return False
    return not t


def json_dict_to_file(json_dict, filename):
    """
    Converts a dictionary to a JSON formatted file.

    Args:
        json_dict (dict): Dict to write to JSON
        filename (str): Path to file being written
    """
    with open(filename, "w") as fp:
        json.dump(json_dict, fp, indent=4)


def file_to_json_dict(filename):
    """
    Reads in a JSON file and returns dict of contents.

    Args:
        filename (str): Path to file to be read

    Returns:
        dict: Dictionary with JSON contents
    """
    with open(filename) as fp:
        return json.load(fp)


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


# Regresstion test helper functions
def calculate_env_mesh(mesh_config):
    """
    Creates a new environmental mesh from the old mesh's config.

    Args:
        mesh_config (dict): Config to generate new mesh from

    Returns:
        dict: Newly regenerated mesh as JSON
    """
    start = time.perf_counter()

    mesh_builder = meshiphi.MeshBuilder(mesh_config)
    new_mesh = mesh_builder.build_environmental_mesh()

    end = time.perf_counter()

    cellbox_count = len(new_mesh.agg_cellboxes)
    elapsed_time = end - start
    LOGGER.info(f"Mesh containing {cellbox_count} cellboxes built in {elapsed_time:.2f} seconds")

    return new_mesh.to_json()


@pytest.fixture(scope="session", autouse=False, params=ALL_TEST_MESHES)
def mesh_pair(request):
    """
    Creates a pair of JSON objects: one newly generated, one as old reference.

    Args:
        request (fixture): Pytest fixture object including list of meshes to regenerate

    Returns:
        dict: Dictionary containing test name, old mesh, and newly generated mesh
    """
    mesh_path = request.param
    LOGGER.info(f"Test File: {mesh_path}")

    with open(mesh_path) as fp:
        old_mesh = json.load(fp)

    mesh_config = old_mesh["config"]["mesh_info"]
    new_mesh = calculate_env_mesh(mesh_config)

    test_name = os.path.basename(mesh_path)

    return {"test": test_name, "old_mesh": old_mesh, "new_mesh": new_mesh}


# Unit test fixtures
@pytest.fixture
def arbitrary_boundary():
    """Standard arbitrary boundary for testing."""
    return Boundary([10, 20], [30, 40])


@pytest.fixture
def temporal_boundary():
    """Boundary with temporal component for testing."""
    return Boundary([10, 20], [30, 40], ["1970-01-01", "2021-12-31"])


@pytest.fixture
def meridian_boundary():
    """Boundary crossing the prime meridian."""
    return Boundary([-50, -40], [-10, 10])


@pytest.fixture
def antimeridian_boundary():
    """Boundary crossing the antimeridian."""
    return Boundary([-50, -40], [170, -170])


@pytest.fixture
def equatorial_boundary():
    """Boundary crossing the equator."""
    return Boundary([-10, 10], [30, 40])


@pytest.fixture
def dummy_cellbox(arbitrary_boundary):
    """Basic cellbox for testing modifications."""
    return create_cellbox(arbitrary_boundary)


@pytest.fixture
def dummy_agg_cellbox():
    """Basic aggregated cellbox for testing."""
    arbitrary_agg_data = {"dummy_data": 1}
    return AggregatedCellBox(Boundary([45, 60], [45, 60]), arbitrary_agg_data, 0)


@pytest.fixture
def arbitrary_agg_cellbox():
    """Arbitrary aggregated cellbox for testing."""
    arbitrary_agg_data = {"dummy_data": 1}
    return AggregatedCellBox(Boundary([45, 60], [45, 60]), arbitrary_agg_data, 1)


@pytest.fixture
def equatorial_agg_cellbox():
    """Aggregated cellbox crossing equator."""
    arbitrary_agg_data = {"dummy_data": 1}
    return AggregatedCellBox(Boundary([-10, 10], [45, 60]), arbitrary_agg_data, 2)


@pytest.fixture
def meridian_agg_cellbox():
    """Aggregated cellbox crossing prime meridian."""
    arbitrary_agg_data = {"dummy_data": 1}
    return AggregatedCellBox(Boundary([45, 60], [-10, 10]), arbitrary_agg_data, 3)


@pytest.fixture
def antimeridian_agg_cellbox():
    """Aggregated cellbox crossing antimeridian."""
    arbitrary_agg_data = {"dummy_data": 1}
    return AggregatedCellBox(Boundary([45, 60], [170, -170]), arbitrary_agg_data, "4")
