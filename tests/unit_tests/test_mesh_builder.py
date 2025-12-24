import unittest
import json
from pathlib import Path
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
from meshiphi.mesh_generation.mesh_builder import MeshBuilder
from meshiphi.mesh_generation.direction import Direction
from meshiphi.mesh_generation.boundary import Boundary


class TestMeshBuilder(unittest.TestCase):
    """Tests for MeshBuilder class"""
    
    def setUp(self):
        """Set up test mesh builder"""
        test_dir = Path(__file__).parent
        self.json_file_path = test_dir / "resources/global_grf_normal.json"
        
        with open(self.json_file_path, "r") as config_file:
            self.json_file = json.load(config_file)
            self.config = self.json_file['config']['mesh_info']
            self.mesh_builder = MeshBuilder(self.config)
            self.env_mesh = self.mesh_builder.build_environmental_mesh()

    def test_check_global_mesh(self):
        """Test global mesh functionality and neighbour relationships"""
        # grid_width is 72 in this mesh
        self.assertEqual(self.mesh_builder.neighbour_graph.is_global_mesh(), True)
        
        # Test cases for neighbour relationships
        test_cases = [
            # (cellbox1_idx, cellbox2_idx, expected_direction, description)
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
        ]
        
        for cb1_idx, cb2_idx, expected_dir, description in test_cases:
            with self.subTest(case=description):
                actual_dir = self.mesh_builder.neighbour_graph.get_neighbour_case(
                    self.mesh_builder.mesh.cellboxes[cb1_idx],
                    self.mesh_builder.mesh.cellboxes[cb2_idx]
                )
                self.assertEqual(actual_dir, expected_dir)