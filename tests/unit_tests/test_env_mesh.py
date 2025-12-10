import unittest
import json
import os        
from pathlib import Path
import tempfile
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
from meshiphi.mesh_generation.mesh_builder import MeshBuilder
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph


class TestEnvMesh(unittest.TestCase):
    def setUp(self):
        self.config = None
        self.env_mesh = None
        # Use Path to construct absolute path from repository root
        test_dir = Path(__file__).parent.parent
        self.json_file = test_dir / "regression_tests/example_meshes/env_meshes/grf_reprojection.json"
        with open(self.json_file, "r") as config_file:
            self.json_file = json.load(config_file)
            self.config = self.json_file['config']['mesh_info']
            self.env_mesh = MeshBuilder(self.config).build_environmental_mesh()
        self.loaded_env_mesh = EnvironmentMesh.load_from_json(self.json_file)

    def test_load_from_json(self):
        self.assertEqual(self.loaded_env_mesh.bounds.get_bounds(), self.env_mesh.bounds.get_bounds())

        self.assertEqual(len(self.loaded_env_mesh.agg_cellboxes), len(self.env_mesh.agg_cellboxes))
        self.assertEqual(len(self.loaded_env_mesh.neighbour_graph.get_graph()),
                         len(self.env_mesh.neighbour_graph.get_graph()))

    def test_update_agg_cellbox(self):
        self.loaded_env_mesh.update_cellbox(0, {"x": "5"})
        self.assertEqual(self.loaded_env_mesh.agg_cellboxes[0].get_agg_data()["x"], "5")

    def test_to_tif(self):
        """Test GDAL import and basic tif functionality without full mesh processing"""
        # Test that GDAL imports work
        try:
            from osgeo import gdal
        # The reason for doing this is that GDAL is an optional dependency, and only used for
        # exporting to tif. If GDAL is not installed, we skip this test.
        except ImportError:
            self.skipTest("GDAL not available - install with: conda install -c conda-forge gdal")
        
        # Create a simple test mesh with minimal data
        # Boundary constructor takes (lat_range, long_range, time_range=None)
        lat_range = [-10, -5]
        long_range = [10, 15]
        bounds = Boundary(lat_range, long_range)
        
        # Again, minimal boxes, graph and config
        cellbox = AggregatedCellBox(bounds, {"test_value": 1.5}, "test_cellbox_0")
        agg_cellboxes = [cellbox]
        neighbour_graph = NeighbourGraph()
        config = {"test": True}
        
        env_mesh = EnvironmentMesh(bounds, agg_cellboxes, neighbour_graph, config)
        
        # Test tif export with temporary file
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
            tmp_path = tmp.name
        
        # Create format parameters for tif export
        with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as params_file:
            format_params = {
                "data_name": "test_value",
                "sampling_resolution": [10, 10],  # Small resolution for faster test
                "projection": "4326"
            }
            json.dump(format_params, params_file)
            params_path = params_file.name
        
        try:
            env_mesh.save(tmp_path, format="tif", format_params=params_path)
            # Verify the file was created
            self.assertTrue(os.path.exists(tmp_path))
            # Verify it's a valid tiff file
            self.assertGreater(os.path.getsize(tmp_path), 0)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if os.path.exists(params_path):
                os.remove(params_path)
