"""
CLI command tests.
"""
import pytest
import tempfile
import sys
from unittest.mock import patch
from meshiphi.cli import rebuild_mesh_cli, create_mesh_cli, merge_mesh_cli
from meshiphi import __version__ as MESHIPHI_VERSION

# Import helper functions that are now in conftest.py
# These are automatically available in test functions but need explicit import for module level
from tests.conftest import json_dict_to_file, file_to_json_dict


# Constants for test data
BASIC_CONFIG = {
    "region": {"lat_min": -10, "lat_max": 10, "long_min": -10, "long_max": 10, 
               "start_time": "2000-01-01", "end_time": "2000-12-31", 
               "cell_width": 10, "cell_height": 10},
    "data_sources": [],
    "splitting": {"split_depth": 1, "minimum_datapoints": 5}
}


@pytest.fixture
def basic_mesh():
    """Generate basic test mesh"""
    return {
        "config": {"mesh_info": BASIC_CONFIG},
        "cellboxes": [
            {"geometry": "POLYGON ((-10 -10, -10 0, 0 0, 0 -10, -10 -10))", 
             "cx": -5, "cy": -5, "dcx": 5, "dcy": 5, "id": "0"},
            {"geometry": "POLYGON ((0 -10, 0 0, 10 0, 10 -10, 0 -10))", 
             "cx": 5, "cy": -5, "dcx": 5, "dcy": 5, "id": "1"},
            {"geometry": "POLYGON ((-10 0, -10 10, 0 10, 0 0, -10 0))", 
             "cx": -5, "cy": 5, "dcx": 5, "dcy": 5, "id": "2"},
            {"geometry": "POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", 
             "cx": 5, "cy": 5, "dcx": 5, "dcy": 5, "id": "3"}
        ],
        "neighbour_graph": {
            "0": {"1": [3], "2": [1], "3": [], "4": [], "-1": [], "-2": [], "-3": [], "-4": [2]},
            "1": {"1": [], "2": [], "3": [], "4": [], "-1": [], "-2": [0], "-3": [2], "-4": [3]},
            "2": {"1": [], "2": [3], "3": [1], "4": [0], "-1": [], "-2": [], "-3": [], "-4": []},
            "3": {"1": [], "2": [], "3": [], "4": [1], "-1": [0], "-2": [2], "-3": [], "-4": []}
        },
        "meshiphi_version": MESHIPHI_VERSION
    }


@pytest.fixture
def basic_half_mesh_1():
    """First half of mesh for merging tests"""
    return {
        "config": {"mesh_info": {"region": {"lat_min": -10, "lat_max": 0, "long_min": -10, "long_max": 10,
                                            "start_time": "2000-01-01", "end_time": "2000-12-31",
                                            "cell_width": 10, "cell_height": 10},
                                "data_sources": [], "splitting": {"split_depth": 1, "minimum_datapoints": 5}}},
        "cellboxes": [
            {"geometry": "POLYGON ((-10 -10, -10 0, 0 0, 0 -10, -10 -10))", 
             "cx": -5, "cy": -5, "dcx": 5, "dcy": 5, "id": "0"},
            {"geometry": "POLYGON ((0 -10, 0 0, 10 0, 10 -10, 0 -10))", 
             "cx": 5, "cy": -5, "dcx": 5, "dcy": 5, "id": "1"}
        ],
        "neighbour_graph": {
            "0": {"1": [], "2": [1], "3": [], "4": [], "-1": [], "-2": [], "-3": [], "-4": []},
            "1": {"1": [], "2": [], "3": [], "4": [], "-1": [], "-2": [0], "-3": [], "-4": []}
        }
    }


@pytest.fixture
def basic_half_mesh_2():
    """Second half of mesh for merging tests"""
    return {
        "config": {"mesh_info": {"region": {"lat_min": 0, "lat_max": 10, "long_min": -10, "long_max": 10,
                                            "start_time": "2000-01-01", "end_time": "2000-12-31",
                                            "cell_width": 10, "cell_height": 10},
                                "data_sources": [], "splitting": {"split_depth": 1, "minimum_datapoints": 5}}},
        "cellboxes": [
            {"geometry": "POLYGON ((-10 0, -10 10, 0 10, 0 0, -10 0))", 
             "cx": -5, "cy": 5, "dcx": 5, "dcy": 5, "id": "0"},
            {"geometry": "POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", 
             "cx": 5, "cy": 5, "dcx": 5, "dcy": 5, "id": "1"}
        ],
        "neighbour_graph": {
            "0": {"1": [], "2": [1], "3": [], "4": [], "-1": [], "-2": [], "-3": [], "-4": []},
            "1": {"1": [], "2": [], "3": [], "4": [], "-1": [], "-2": [0], "-3": [], "-4": []}
        }
    }


@pytest.fixture
def temp_files():
    """Create temporary files for testing."""
    files = {
        'config': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
        'mesh': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
        'mesh_1': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
        'mesh_2': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
        'merge': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
        'output': tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json'),
    }
    
    yield files
    
    # Cleanup temporary files
    import os
    for f in files.values():
        try:
            f.close()
            if os.path.exists(f.name):
                os.remove(f.name)
        except Exception:
            pass  # Ignore cleanup errors


def test_get_args_cli():
    """Test argparser - placeholder for future implementation.
    
    TODO:
    - Set up arbitrary arguments to patch into sys.argv
    - Test that argparser correctly identifies these arguments
    - Should have entries for each possible combination of arguments
    - Update whenever CLI is updated
    """
    pytest.skip("Argparser testing not yet implemented")


def test_rebuild_mesh_cli(basic_mesh, temp_files):
    """Test rebuild mesh CLI command"""
    # Write mesh to temp file
    json_dict_to_file(basic_mesh, temp_files['mesh'].name)
    
    # Command line entry
    test_args = ['rebuild_mesh', 
                 temp_files['mesh'].name,
                 '-o', temp_files['output'].name]
    
    with patch.object(sys, 'argv', test_args):
        rebuild_mesh_cli()
    
    # Verify output was created
    rebuilt_mesh = file_to_json_dict(temp_files['output'].name)
    assert 'cellboxes' in rebuilt_mesh
    assert 'neighbour_graph' in rebuilt_mesh


def test_create_mesh_cli(temp_files):
    """Test create mesh CLI command"""
    # Write config to temp file
    json_dict_to_file(BASIC_CONFIG, temp_files['config'].name)
    
    # Command line entry
    test_args = ['create_mesh', 
                 temp_files['config'].name,
                 '-o', temp_files['output'].name]
    
    with patch.object(sys, 'argv', test_args):
        create_mesh_cli()
    
    # Verify output was created
    created_mesh = file_to_json_dict(temp_files['output'].name)
    assert 'cellboxes' in created_mesh
    assert 'config' in created_mesh


def test_merge_mesh_cli(basic_half_mesh_1, basic_half_mesh_2, temp_files):
    """Test merge mesh CLI command"""
    # Write meshes to temp files
    json_dict_to_file(basic_half_mesh_1, temp_files['mesh_1'].name)
    json_dict_to_file(basic_half_mesh_2, temp_files['mesh_2'].name)
    
    # Command line entry
    test_args = ['merge_mesh',
                 temp_files['mesh_1'].name,
                 temp_files['mesh_2'].name,
                 '-o', temp_files['output'].name]
    
    with patch.object(sys, 'argv', test_args):
        merge_mesh_cli()
    
    # Verify merged mesh
    merged_mesh = file_to_json_dict(temp_files['output'].name)
    assert 'cellboxes' in merged_mesh
    assert len(merged_mesh['cellboxes']) == 4  # Combined from both meshes
