import unittest
import json
from pathlib import Path
from meshiphi.mesh_generation.mesh_builder import MeshBuilder
from meshiphi.mesh_generation.direction import Direction


class TestMeshBuilder(unittest.TestCase):
    def setUp(self):
        self.config = None
        self.env_mesh = None
        # Use Path to construct absolute path from repository root
        test_dir = Path(__file__).parent
        self.json_file = test_dir / "resources/global_grf_normal.json"
        with open(self.json_file, "r") as config_file:
            self.json_file = json.load(config_file)
            self.config = self.json_file["config"]["mesh_info"]
            self.mesh_builder = MeshBuilder(self.config)
            self.env_mesh = self.mesh_builder.build_environmental_mesh()
        #  self.env_mesh.save("global_mesh.json")

    def test_check_global_mesh(self):
        # grid_width is 72 in this mesh so checking cellboxes around grid_width multiples (cellboxes at the min and max longtitude)
        self.assertEqual(self.mesh_builder.neighbour_graph.is_global_mesh(), True)
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[0],
                self.mesh_builder.mesh.cellboxes[71],
            ),
            Direction.west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[71],
                self.mesh_builder.mesh.cellboxes[0],
            ),
            Direction.east,
        )

        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[0],
                self.mesh_builder.mesh.cellboxes[143],
            ),
            Direction.north_west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[72],
                self.mesh_builder.mesh.cellboxes[71],
            ),
            Direction.south_west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[72],
                self.mesh_builder.mesh.cellboxes[143],
            ),
            Direction.west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[72],
                self.mesh_builder.mesh.cellboxes[215],
            ),
            Direction.north_west,
        )

        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[143],
                self.mesh_builder.mesh.cellboxes[72],
            ),
            Direction.east,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[143],
                self.mesh_builder.mesh.cellboxes[70],
            ),
            Direction.south_west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[143],
                self.mesh_builder.mesh.cellboxes[142],
            ),
            Direction.west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[143],
                self.mesh_builder.mesh.cellboxes[214],
            ),
            Direction.north_west,
        )

        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[1], self.mesh_builder.mesh.cellboxes[0]
            ),
            Direction.west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[0], self.mesh_builder.mesh.cellboxes[1]
            ),
            Direction.east,
        )

        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[1],
                self.mesh_builder.mesh.cellboxes[72],
            ),
            Direction.north_west,
        )
        self.assertEqual(
            self.mesh_builder.neighbour_graph.get_neighbour_case(
                self.mesh_builder.mesh.cellboxes[1],
                self.mesh_builder.mesh.cellboxes[74],
            ),
            Direction.north_east,
        )
