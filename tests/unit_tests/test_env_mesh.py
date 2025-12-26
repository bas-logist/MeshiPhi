"""
EnvironmentMesh class tests.
"""
import pytest
import json
import os
import tempfile
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
from meshiphi.mesh_generation.mesh_builder import MeshBuilder
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph
from tests.conftest import REGRESSION_TESTS_DIR


@pytest.fixture
def env_mesh_data():
    """Load environment mesh data from test file."""
    json_file_path = REGRESSION_TESTS_DIR / "example_meshes/env_meshes/grf_reprojection.json"
    
    with open(json_file_path, "r") as config_file:
        json_file = json.load(config_file)
        config = json_file['config']['mesh_info']
        env_mesh = MeshBuilder(config).build_environmental_mesh()
    
    loaded_env_mesh = EnvironmentMesh.load_from_json(json_file)
    
    return {
        'env_mesh': env_mesh,
        'loaded_env_mesh': loaded_env_mesh
    }


def test_load_from_json(env_mesh_data):
    """Test loading environment mesh from JSON"""
    loaded = env_mesh_data['loaded_env_mesh']
    original = env_mesh_data['env_mesh']
    
    assert loaded.bounds.get_bounds() == original.bounds.get_bounds()
    assert len(loaded.agg_cellboxes) == len(original.agg_cellboxes)
    assert len(loaded.neighbour_graph.get_graph()) == len(original.neighbour_graph.get_graph())


def test_update_agg_cellbox(env_mesh_data):
    """Test updating aggregated cellbox data"""
    loaded_env_mesh = env_mesh_data['loaded_env_mesh']
    loaded_env_mesh.update_cellbox(0, {"x": "5"})
    assert loaded_env_mesh.agg_cellboxes[0].get_agg_data()["x"] == "5"


def test_to_tif():
    """
    Test TIFF export functionality with GDAL.
    
    Verifies that environment meshes can be exported to GeoTIFF format
    and that the resulting files are valid.
    """
    pytest.importorskip("osgeo.gdal", reason="GDAL not available - install with: conda install -c conda-forge gdal")
    
    # Create a simple test mesh with minimal data
    lat_range = [-10, -5]
    long_range = [10, 15]
    bounds = Boundary(lat_range, long_range)
    
    # Minimal boxes, graph and config
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
        assert os.path.exists(tmp_path)
        # Verify it's a valid tiff file
        assert os.path.getsize(tmp_path) > 0
    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(params_path):
            os.remove(params_path)
