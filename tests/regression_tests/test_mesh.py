"""
Regression testing package to ensure consistent functionality in development
of the MeshiPhi python package.
"""

import json
import pytest
import time
import os
from pathlib import Path
import logging

import meshiphi

# Import test functions
from .mesh_test_functions import (
    test_mesh_cellbox_attributes,
    test_mesh_cellbox_count,
    test_mesh_cellbox_ids,
    test_mesh_cellbox_values,
    test_mesh_neighbour_graph_count,
    test_mesh_neighbour_graph_ids,
    test_mesh_neighbour_graph_values
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# Use Path to construct absolute paths from repository root
TEST_DIR = Path(__file__).parent

# File locations of all meshes to be recalculated for regression testing
TEST_ENV_MESHES = [
    'grf_normal.json',
    'grf_downsample.json',
    'grf_reprojection.json',
    'grf_sparse.json'
]

TEST_ABSTRACT_MESHES = [
    'vgrad.json',
    'hgrad.json',
    'checkerboard_1.json',
    'checkerboard_2.json',
    'checkerboard_3.json',
    'circle.json',
    'circle_quadrant_split.json',
    'circle_quadrant_nosplit.json'
]

# Build full paths
ALL_TEST_MESHES = (
    [str(TEST_DIR / 'example_meshes/env_meshes' / mesh) for mesh in TEST_ENV_MESHES] +
    [str(TEST_DIR / 'example_meshes/abstract_env_meshes' / mesh) for mesh in TEST_ABSTRACT_MESHES]
)


def setup_module():
    """Log MeshiPhi version at module setup"""
    LOGGER.info(f'MeshiPhi version: {meshiphi.__version__}')

@pytest.fixture(scope='session', autouse=False, params=ALL_TEST_MESHES)
def mesh_pair(request):
    """
    Creates a pair of JSON objects: one newly generated, one as old reference.
    
    Args:
        request (fixture): Pytest fixture object including list of meshes to regenerate

    Returns:
        dict: Dictionary containing test name, old mesh, and newly generated mesh
    """
    mesh_path = request.param
    LOGGER.info(f'Test File: {mesh_path}')
   
    with open(mesh_path, 'r') as fp:
        old_mesh = json.load(fp)
    
    mesh_config = old_mesh['config']['mesh_info']
    new_mesh = calculate_env_mesh(mesh_config)
    
    test_name = os.path.basename(mesh_path)

    return {
        "test": test_name,
        "old_mesh": old_mesh,
        "new_mesh": new_mesh
    }

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
    LOGGER.info(f'Mesh containing {cellbox_count} cellboxes built in {elapsed_time:.2f} seconds')

    return new_mesh.to_json()


def test_record_output(mesh_pair, tmp_path):
    """
    Store fixtures after generation to avoid recomputing meshes for diagnosis upon failure.

    Args:
        mesh_pair (dict): Fixture holding generated meshes
        tmp_path (fixture): Pytest built-in fixture for unique temporary directory
    
    Note:
        Saves files to parent folder to prevent pytest from overwriting subdirectories
        after 3 tests. Reference: https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html
    """
    test_name = mesh_pair['test']
    test_basename = test_name.split('.')[0]
    save_filename = os.path.join(tmp_path, '..', f'{test_basename}.comparison.json')

    # Extract only mesh data, excluding test name
    meshes = {key: val for key, val in mesh_pair.items() if key != 'test'}

    with open(save_filename, 'w') as fp:
        json.dump(meshes, fp, indent=4)
