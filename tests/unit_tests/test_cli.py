from meshiphi.cli import get_args, rebuild_mesh_cli, create_mesh_cli, export_mesh_cli, merge_mesh_cli, meshiphi_test_cli
from meshiphi import __version__ as MESHIPHI_VERSION
from tests.unit_tests.test_utils import json_dict_to_file, file_to_json_dict

import tempfile
import sys
import unittest
import json
from unittest.mock import patch


# Constants for test data
BASIC_CONFIG = {
    "region": {"lat_min": -10, "lat_max": 10, "long_min": -10, "long_max": 10, 
               "start_time": "2000-01-01", "end_time": "2000-12-31", 
               "cell_width": 10, "cell_height": 10},
    "data_sources": [],
    "splitting": {"split_depth": 1, "minimum_datapoints": 5}
}


def get_basic_mesh():
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


BASIC_MESH = get_basic_mesh()
BASIC_OUTPUT = get_basic_mesh()

# Meshes to merge
BASIC_HALF_MESH_1 = {
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

BASIC_HALF_MESH_2 = {
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


def get_basic_merged_mesh():
    """Generate merged mesh for testing"""
    merged_config = BASIC_CONFIG.copy()
    merged_config["merged"] = [BASIC_HALF_MESH_2["config"]["mesh_info"]]
    
    return {
        "config": {"mesh_info": BASIC_HALF_MESH_1["config"]["mesh_info"] | {"merged": [BASIC_HALF_MESH_2["config"]["mesh_info"]]}},
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


BASIC_MERGED_MESH = get_basic_merged_mesh()


class TestCLI(unittest.TestCase):
    """Tests for CLI commands"""

    def setUp(self):
        """Create temporary files for testing"""
        self.output_base_directory = tempfile.mkdtemp()
        self.tmp_config_file = tempfile.NamedTemporaryFile()
        self.tmp_mesh_file = tempfile.NamedTemporaryFile()
        self.tmp_mesh_file_1 = tempfile.NamedTemporaryFile()
        self.tmp_mesh_file_2 = tempfile.NamedTemporaryFile()
        self.tmp_merge_file = tempfile.NamedTemporaryFile()
        self.tmp_output_file = tempfile.NamedTemporaryFile()

    def tearDown(self):
        """Remove temporary files"""
        self.tmp_config_file.close()
        self.tmp_mesh_file.close()
        self.tmp_mesh_file_1.close()
        self.tmp_mesh_file_2.close()
        self.tmp_merge_file.close()
        self.tmp_output_file.close()
    
    def test_get_args_cli(self):
        # TODO:
        #   - Set up arbitrary arguments to patch into sys.argv
        #   - Test that argparser correctly ID's these arguments
        #       - Should have entries for each possible combination of arguments,
        #         so should be updated whenever CLI is updated
        pass
    
    def test_rebuild_mesh_cli(self):
        # Command line entry
        test_args = ['rebuild_mesh', 
                     self.tmp_mesh_file.name,
                     '-o', self.tmp_output_file.name]
        
        # Create files with relevant data for test
        json_dict_to_file(get_basic_mesh(), self.tmp_mesh_file.name)

        # Patch sys.argv with command line entry defined above
        with patch.object(sys, 'argv', test_args):

            # Run the command
            rebuild_mesh_cli()
            
            # Save ground truth and new mesh to JSON dicts
            orig_mesh  = file_to_json_dict(self.tmp_mesh_file.name)
            rebuilt_mesh = file_to_json_dict(self.tmp_output_file.name)

            # Ensure they are the same
            self.assertEqual(orig_mesh, rebuilt_mesh)

    def test_create_mesh_cli(self):
        # Command line entry
        test_args = ['create_mesh', 
                     self.tmp_config_file.name,
                     '-o', self.tmp_output_file.name]
        
        # Create files with relevant data for test
        json_dict_to_file(BASIC_CONFIG, self.tmp_config_file.name)
        json_dict_to_file(get_basic_mesh(), self.tmp_mesh_file.name)

        # Patch sys.argv with command line entry defined above
        with patch.object(sys, 'argv', test_args):

            # Run the command
            create_mesh_cli()
            
            # Save ground truth and new mesh to JSON dicts
            orig_mesh  = file_to_json_dict(self.tmp_mesh_file.name)
            created_mesh = file_to_json_dict(self.tmp_output_file.name)

            # Ensure they are the same
            self.assertEqual(orig_mesh, created_mesh)
    
    def test_export_mesh_cli(self):
        # TODO:
        #   - Test GeoJSON output
        #   - Set up method for comparing PNG and test
        #       - Also allow PNG creation of empty mesh?
        #   - Fix TIF export on Windows
        #   - Set up method for comparing TIF and test
        pass

    def test_merge_mesh_cli(self):
        # Command line entry
        test_args = ['merge_mesh', 
                     self.tmp_mesh_file_1.name,
                     self.tmp_mesh_file_2.name,
                     '-o', self.tmp_output_file.name]
        
        # Create files with relevant data for test
        json_dict_to_file(BASIC_HALF_MESH_1, self.tmp_mesh_file_1.name)
        json_dict_to_file(BASIC_HALF_MESH_2, self.tmp_mesh_file_2.name)
        json_dict_to_file(get_basic_merged_mesh(), self.tmp_mesh_file.name)
        
        # Patch sys.argv with command line entry defined above
        with patch.object(sys, 'argv', test_args):

            # Run the command
            merge_mesh_cli()
            
            # Save ground truth and new mesh to JSON dicts
            orig_mesh  = file_to_json_dict(self.tmp_mesh_file.name)
            created_mesh = file_to_json_dict(self.tmp_output_file.name)

            # Ensure they are the same
            self.assertEqual(orig_mesh, created_mesh)
        
    def test_meshiphi_test_cli(self):
        # TODO:
        #  - Set up method for comparing SVG images
        #  - Compare output json, create BASIC_REG_TEST_OUTPUT constant as ground truth
        #       - And come up with way to consistently test this with only changes to
        #         cli.py
        pass