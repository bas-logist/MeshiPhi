"""
Regression testing package to ensure consistent functionality in development
of the MeshiPhi python package.
"""

import json
import logging
import os

import pytest

import meshiphi

# Import test functions - pytest will auto-discover them from test_comparisons.py
from . import test_comparisons  # noqa: F401

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# Apply markers to all tests in this module
pytestmark = pytest.mark.slow


def setup_module():
    """Log MeshiPhi version at module setup"""
    LOGGER.info(f"MeshiPhi version: {meshiphi.__version__}")


def test_record_output(mesh_pair, tmp_path):
    """
    Store generated meshes to avoid recomputing for diagnosis upon failure.

    Saves test fixtures after generation to enable post-failure analysis without
    regenerating computationally expensive meshes.

    Args:
        mesh_pair (dict): Fixture holding generated meshes
        tmp_path (fixture): Pytest built-in fixture for unique temporary directory

    Note:
        Saves files to parent folder to prevent pytest from overwriting subdirectories
        after 3 tests. Reference: https://docs.pytest.org/en/7.1.x/how-to/tmp_path.html
    """
    test_name = mesh_pair["test"]
    test_basename = test_name.split(".")[0]
    save_filename = os.path.join(tmp_path, "..", f"{test_basename}.comparison.json")

    # Extract only mesh data, excluding test name
    meshes = {key: val for key, val in mesh_pair.items() if key != "test"}

    with open(save_filename, "w") as fp:
        json.dump(meshes, fp, indent=4)
