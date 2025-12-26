"""
MeshBuilder class tests.
"""
import pytest
import json
from meshiphi.mesh_generation.mesh_builder import MeshBuilder
from meshiphi.mesh_generation.direction import Direction
from tests.conftest import UNIT_TESTS_DIR


@pytest.fixture
def mesh_builder():
    """Create a mesh builder instance for testing."""
    json_file_path = UNIT_TESTS_DIR / "resources/global_grf_normal.json"
    
    with open(json_file_path, "r") as config_file:
        json_file = json.load(config_file)
        config = json_file['config']['mesh_info']
        builder = MeshBuilder(config)
        env_mesh = builder.build_environmental_mesh()
    
    return {
        'builder': builder,
        'env_mesh': env_mesh
    }


def test_check_global_mesh(mesh_builder):
    """Test global mesh functionality"""
    builder = mesh_builder['builder']
    # grid_width is 72 in this mesh
    assert builder.neighbour_graph.is_global_mesh()


@pytest.mark.parametrize("cb1_idx,cb2_idx,expected_dir,description", [
    (0, 71, Direction.west, "edge wrapping west"),
    (71, 0, Direction.east, "edge wrapping east"),
    (0, 143, Direction.north_west, "corner north_west"),
    (72, 71, Direction.south_west, "cross row south_west"),
    (72, 143, Direction.west, "same column west"),
    (72, 215, Direction.north_west, "diagonal north_west"),
    (143, 72, Direction.east, "reverse east"),
    (143, 70, Direction.south_west, "diagonal south_west"),
    (143, 142, Direction.west, "adjacent west"),
    (143, 214, Direction.north_west, "upper diagonal north_west"),
    (1, 0, Direction.west, "simple west"),
    (0, 1, Direction.east, "simple east"),
    (1, 72, Direction.north_west, "vertical north_west"),
    (1, 74, Direction.north_east, "vertical north_east"),
])
def test_neighbour_relationships(mesh_builder, cb1_idx, cb2_idx, expected_dir, description):
    """Test neighbour relationships in global mesh"""
    builder = mesh_builder['builder']
    actual_dir = builder.neighbour_graph.get_neighbour_case(
        builder.mesh.cellboxes[cb1_idx],
        builder.mesh.cellboxes[cb2_idx]
    )
    assert actual_dir == expected_dir
