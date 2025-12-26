import unittest
import copy

from meshiphi.mesh_generation.direction import Direction
from meshiphi.mesh_generation.neighbour_graph import NeighbourGraph
from meshiphi.mesh_generation.cellbox import CellBox
from meshiphi.mesh_generation.boundary import Boundary
from meshiphi.utils import longitude_domain


# Define which direction each cardinal direction lies
NORTHERN_DIRECTIONS = [Direction.north_east, Direction.north, Direction.north_west]
EASTERN_DIRECTIONS = [Direction.north_east, Direction.east, Direction.south_east]
SOUTHERN_DIRECTIONS = [Direction.south_east, Direction.south, Direction.south_west]
WESTERN_DIRECTIONS = [Direction.south_west, Direction.west, Direction.north_west]
DIAGONAL_DIRECTIONS = [
    Direction.north_east,
    Direction.north_west,
    Direction.south_east,
    Direction.south_west,
]
ALL_DIRECTIONS = [
    Direction.north,
    Direction.north_east,
    Direction.east,
    Direction.south_east,
    Direction.south,
    Direction.south_west,
    Direction.west,
    Direction.north_west,
]


def create_ng_from_dict(ng_dict, global_mesh=False):
    ng = NeighbourGraph()
    ng.neighbour_graph = copy.deepcopy(ng_dict)
    ng._is_global_mesh = global_mesh

    return ng


class TestNeighbourGraph(unittest.TestCase):
    def setUp(self):
        # Neighbour graph of a 3x3 array of cellboxes
        self.ng_dict_3x3 = {
            1: {1: [], 2: [2], 3: [5], 4: [4], -1: [], -2: [], -3: [], -4: []},
            2: {1: [], 2: [3], 3: [6], 4: [5], -1: [4], -2: [1], -3: [], -4: []},
            3: {1: [], 2: [], 3: [], 4: [6], -1: [5], -2: [2], -3: [], -4: []},
            4: {1: [2], 2: [5], 3: [8], 4: [7], -1: [], -2: [], -3: [], -4: [1]},
            5: {1: [3], 2: [6], 3: [9], 4: [8], -1: [7], -2: [4], -3: [1], -4: [2]},
            6: {1: [], 2: [], 3: [], 4: [9], -1: [8], -2: [5], -3: [2], -4: [3]},
            7: {1: [5], 2: [8], 3: [], 4: [], -1: [], -2: [], -3: [], -4: [4]},
            8: {1: [6], 2: [9], 3: [], 4: [], -1: [], -2: [7], -3: [4], -4: [5]},
            9: {1: [], 2: [], 3: [], 4: [], -1: [], -2: [8], -3: [5], -4: [6]},
        }

        # Non-global 3x3 Neighbour graph, "5" in the middle, with the others all surrounding it
        self.neighbour_graph = create_ng_from_dict(self.ng_dict_3x3)

    def test_from_json(self):
        ng = NeighbourGraph.from_json(self.ng_dict_3x3)

        self.assertIsInstance(ng, NeighbourGraph)
        self.assertEqual(ng.neighbour_graph, self.ng_dict_3x3)

    def test_increment_ids(self):
        increment = 10
        ng = create_ng_from_dict(self.ng_dict_3x3)
        ng.increment_ids(10)

        # Add 'increment' to nodes and neighbours stored within the neighbourgraph dict
        # Creates a dict of form {str(node + increment): {direction: [neighbours + increment]}}
        manually_incremented_dict = {
            str(int(node) + increment): {
                direction: [neighbour + increment for neighbour in neighbours]
                for direction, neighbours in dir_map.items()
            }
            for node, dir_map in self.ng_dict_3x3.items()
        }
        manually_incremented_ng = create_ng_from_dict(manually_incremented_dict)

        self.assertEqual(ng.get_graph(), manually_incremented_ng.get_graph())

    def test_get_graph(self):
        ng_dict = self.neighbour_graph.get_graph()
        self.assertEqual(ng_dict, self.ng_dict_3x3)

    def test_update_neighbour(self):
        node_to_update = 1
        direction_to_update = 1
        updated_neighbours = [1, 2, 3, 4, 5]

        ng = create_ng_from_dict(self.ng_dict_3x3)
        ng.update_neighbour(node_to_update, direction_to_update, updated_neighbours)

        manually_updated_ng = copy.deepcopy(self.ng_dict_3x3)
        manually_updated_ng[node_to_update][direction_to_update] = updated_neighbours

        self.assertEqual(ng.get_graph(), manually_updated_ng)

    def test_add_neighbour(self):
        node_to_update = 1
        direction_to_update = 1
        neighbour_to_add = 123

        ng = create_ng_from_dict(self.ng_dict_3x3)
        ng.add_neighbour(node_to_update, direction_to_update, neighbour_to_add)

        manually_added_ng_dict = copy.deepcopy(self.ng_dict_3x3)
        manually_added_ng_dict[node_to_update][direction_to_update].append(
            neighbour_to_add
        )

        self.assertEqual(ng.get_graph(), manually_added_ng_dict)

    def test_remove_node_and_update_neighbours(self):
        # Remove central (i.e. most connected) node for testing
        node_to_remove = 5

        # Create a new neighbourgraph
        ng = create_ng_from_dict(self.ng_dict_3x3)
        # Remove node using ng method
        ng.remove_node_and_update_neighbours(node_to_remove)

        # Reconstruct manually to test method works
        # Create a new neighbour graph
        manually_removed_ng_dict = copy.deepcopy(self.ng_dict_3x3)
        # Remove the central node by popping it out of neighbour lists
        for node, dir_map in manually_removed_ng_dict.items():
            for direction, neighbours in dir_map.items():
                if node_to_remove in neighbours:
                    neighbours.pop(neighbours.index(node_to_remove))
        # Then remove the central node entirely
        manually_removed_ng_dict.pop(node_to_remove)

        self.assertEqual(ng.get_graph(), manually_removed_ng_dict)

    def test_get_neighbours(self):
        for cb_index in self.ng_dict_3x3.keys():
            for direction in ALL_DIRECTIONS:
                ng_neighbours = self.neighbour_graph.get_neighbours(cb_index, direction)
                self.assertEqual(ng_neighbours, self.ng_dict_3x3[cb_index][direction])

    def test_add_node(self):
        index_to_add = "999"
        neighbour_map_to_add = {
            1: [123],
            2: [234],
            3: [345],
            4: [456],
            -1: [567],
            -2: [678],
            -3: [789],
            -4: [890],
        }

        ng = create_ng_from_dict(self.ng_dict_3x3)
        ng.add_node(index_to_add, neighbour_map_to_add)

        manually_added_ng_dict = copy.deepcopy(self.ng_dict_3x3)
        manually_added_ng_dict[index_to_add] = neighbour_map_to_add

        self.assertEqual(ng.get_graph(), manually_added_ng_dict)

    def test_remove_node(self):
        index_to_remove = 5
        ng = create_ng_from_dict(self.ng_dict_3x3)
        ng.remove_node(index_to_remove)

        manually_removed_ng_dict = copy.deepcopy(self.ng_dict_3x3)
        manually_removed_ng_dict.pop(index_to_remove)

        self.assertEqual(ng.get_graph(), manually_removed_ng_dict)

    def test_update_neighbours(self):
        # Initialise a new neighbour graph to modify
        ng = create_ng_from_dict(self.ng_dict_3x3)
        # Initial CB layout that matches ng
        cbs = [
            CellBox(Boundary([2, 3], [0, 1]), 1),
            CellBox(Boundary([2, 3], [1, 2]), 2),
            CellBox(Boundary([2, 3], [2, 3]), 3),
            CellBox(Boundary([1, 2], [0, 1]), 4),
            CellBox(Boundary([1, 2], [1, 2]), 5),
            CellBox(Boundary([1, 2], [2, 3]), 6),
            CellBox(Boundary([0, 1], [0, 1]), 7),
            CellBox(Boundary([0, 1], [1, 2]), 8),
            CellBox(Boundary([0, 1], [2, 3]), 9),
        ]

        # Creates the cellboxes that the centre cellbox would become when split
        split_cbs = [
            CellBox(Boundary([1.5, 2], [1, 1.5]), 51),
            CellBox(Boundary([1.5, 2], [1.5, 2]), 53),
            CellBox(Boundary([1, 1.5], [1, 1.5]), 57),
            CellBox(Boundary([1, 1.5], [1.5, 2]), 59),
        ]

        # Cast to a list so that indexes match up with indexes (using index as key essentially)
        all_cbs = {cb.id: cb for cb in cbs + split_cbs}

        # Original cellbox from neighbour graph
        unsplit_cb_idx = 5

        # Indexes of split cellboxes
        north_split_cb_idxs = [51, 53]
        east_split_cb_idxs = [53, 59]
        south_split_cb_idxs = [57, 59]
        west_split_cb_idxs = [51, 57]

        # Update the neighbourgraph with the new split cellbox ids
        ng.update_neighbours(
            unsplit_cb_idx, north_split_cb_idxs, Direction.north, all_cbs
        )
        ng.update_neighbours(
            unsplit_cb_idx, east_split_cb_idxs, Direction.east, all_cbs
        )
        ng.update_neighbours(
            unsplit_cb_idx, south_split_cb_idxs, Direction.south, all_cbs
        )
        ng.update_neighbours(
            unsplit_cb_idx, west_split_cb_idxs, Direction.west, all_cbs
        )

        # Create this neighbourgraph manually
        manually_adjusted_ng = copy.deepcopy(self.ng_dict_3x3)
        manually_adjusted_ng[2][Direction.south] = north_split_cb_idxs
        manually_adjusted_ng[4][Direction.east] = west_split_cb_idxs
        manually_adjusted_ng[6][Direction.west] = east_split_cb_idxs
        manually_adjusted_ng[8][Direction.north] = south_split_cb_idxs

        # Final neighbourgraph should look like
        #
        #    1 |    2    | 3
        #    --+---------+---
        #      | 51 | 53 |
        #    4 |---------| 6
        #      | 57 | 59 |
        #   ---+---------+---
        #    7 |    8    | 9
        #

        self.assertEqual(ng.get_graph()[2], manually_adjusted_ng[2])
        self.assertEqual(ng.get_graph()[4], manually_adjusted_ng[4])
        self.assertEqual(ng.get_graph()[6], manually_adjusted_ng[6])
        self.assertEqual(ng.get_graph()[8], manually_adjusted_ng[8])

    def test_remove_node_from_neighbours(self):
        # Create a new neighbour graph to edit freely
        ng = create_ng_from_dict(self.ng_dict_3x3)
        # Make a copy of the neighbourgraph to edit freely
        manually_adjusted_ng = copy.deepcopy(self.ng_dict_3x3)

        # In each direction, remove the central node
        for direction in ALL_DIRECTIONS:
            # Remove node using ng method
            ng.remove_node_from_neighbours(5, direction)

            # Manually remove the node
            # Get index of cellbox in direction
            neighbour_in_direction = manually_adjusted_ng[5][direction][0]
            # Get neighbours of that cellbox in the direction of the node to remove (hence the negative direction)
            neighbour_list = manually_adjusted_ng[neighbour_in_direction][-direction]
            # Remove central node
            neighbour_list.pop(neighbour_list.index(5))

            # Compare method copy to manually removed copy
            self.assertEqual(ng.get_graph(), manually_adjusted_ng)

    def test_update_corner_neighbours(self):
        # Arbitrary values that don't alreayd appear in NG
        nw_idx = 111
        ne_idx = 222
        sw_idx = 333
        se_idx = 444

        base_cb_idx = 5
        # Create new neighbourgraph to avoid editing base copy
        ng = create_ng_from_dict(self.ng_dict_3x3)
        # Create updated graph with arbitrary values above
        ng.update_corner_neighbours(base_cb_idx, nw_idx, ne_idx, sw_idx, se_idx)

        # Test to see if the corner values were updated
        self.assertEqual(ng.neighbour_graph[1][-Direction.north_west], [nw_idx])
        self.assertEqual(ng.neighbour_graph[3][-Direction.north_east], [ne_idx])
        self.assertEqual(ng.neighbour_graph[7][-Direction.south_west], [sw_idx])
        self.assertEqual(ng.neighbour_graph[9][-Direction.south_east], [se_idx])

    def test_get_neighbour_case_bounds(self):
        # Set base boundary
        lat_range = [-10, 10]
        long_range = [-10, 10]

        base_bounds = Boundary(lat_range, long_range)

        # Initialise a neighbourgraph object to get access to get_neighbour_case_bounds()
        ng = NeighbourGraph()

        for direction in ALL_DIRECTIONS:
            lat_offset = 0
            long_offset = 0

            # Offset a second boundary object depending on which direction is being tested
            if direction in NORTHERN_DIRECTIONS:
                lat_offset = 20
            elif direction in SOUTHERN_DIRECTIONS:
                lat_offset = -20

            if direction in EASTERN_DIRECTIONS:
                long_offset = 20
            elif direction in WESTERN_DIRECTIONS:
                long_offset = -20

            # Add offsets to base boundary and create new boundary object
            offset_lat_range = [lat + lat_offset for lat in lat_range]
            offset_long_range = [long + long_offset for long in long_range]

            offset_bounds = Boundary(offset_lat_range, offset_long_range)

            # Make sure it returns the correct case
            self.assertEqual(
                ng.get_neighbour_case_bounds(base_bounds, offset_bounds), direction
            )

        # Final test: make sure that two boundaries that don't touch return an invalid direction (0)
        lat_offset = 50
        long_offset = 50
        # Add offsets to base boundary and create new boundary object
        offset_lat_range = [lat + lat_offset for lat in lat_range]
        offset_long_range = [long + long_offset for long in long_range]

        offset_bounds = Boundary(offset_lat_range, offset_long_range)

        # Make sure it returns the correct case
        self.assertEqual(ng.get_neighbour_case_bounds(base_bounds, offset_bounds), 0)

    def test_get_neighbour_case(self):
        # Not testing global boundary case here because that's tested in
        # test_get_global_mesh_neighbour_case

        # Set base boundary
        lat_range = [-10, 10]
        long_range = [-10, 10]

        base_bounds = Boundary(lat_range, long_range)
        base_cellbox = CellBox(base_bounds, 0)

        # Initialise a neighbourgraph object to get access to get_neighbour_case_bounds()
        ng = NeighbourGraph()

        for direction in ALL_DIRECTIONS:
            lat_offset = 0
            long_offset = 0
            # Offset a second boundary object depending on which direction is being tested
            if direction in NORTHERN_DIRECTIONS:
                lat_offset = 20
            elif direction in SOUTHERN_DIRECTIONS:
                lat_offset = -20

            if direction in EASTERN_DIRECTIONS:
                long_offset = 20
            elif direction in WESTERN_DIRECTIONS:
                long_offset = -20

            # Add offsets to base boundary and create new boundary object
            offset_lat_range = [lat + lat_offset for lat in lat_range]
            offset_long_range = [long + long_offset for long in long_range]

            offset_bounds = Boundary(offset_lat_range, offset_long_range)
            offset_cellbox = CellBox(offset_bounds, 1)

            # Make sure it returns the correct case
            self.assertEqual(
                ng.get_neighbour_case(base_cellbox, offset_cellbox), direction
            )

        # Final test: make sure that two boundaries that don't touch return an invalid direction (0)
        lat_offset = 50
        long_offset = 50
        # Add offsets to base boundary and create new boundary object
        offset_lat_range = [lat + lat_offset for lat in lat_range]
        offset_long_range = [long + long_offset for long in long_range]

        offset_bounds = Boundary(offset_lat_range, offset_long_range)
        offset_cellbox = CellBox(offset_bounds, 1)

        # Make sure it returns the correct case
        self.assertEqual(ng.get_neighbour_case(base_cellbox, offset_cellbox), 0)

    def test_get_global_mesh_neighbour_case(self):
        # Set base boundary
        lat_range = [-10, 10]

        # Initialise a neighbourgraph object to get access to get_neighbour_case_bounds()
        ng = NeighbourGraph()

        for direction in ALL_DIRECTIONS:
            lat_offset = 0
            long_offset = 0

            # If in purely N/S direction, then don't need to test
            if direction in [Direction.north, Direction.south]:
                continue

            # Offset a second boundary object depending on which direction is being tested
            if direction in NORTHERN_DIRECTIONS:
                lat_offset = 20
            elif direction in SOUTHERN_DIRECTIONS:
                lat_offset = -20

            # If on positive side of antimeridian, have to test neighbours to the east
            if direction in EASTERN_DIRECTIONS:
                long_range = [160, 180]
                base_bounds = Boundary(lat_range, long_range)
                base_cellbox = CellBox(base_bounds, 0)
                long_offset = 20
            elif direction in WESTERN_DIRECTIONS:
                long_range = [-180, -160]
                base_bounds = Boundary(lat_range, long_range)
                base_cellbox = CellBox(base_bounds, 0)
                long_offset = -20

            # Add offsets to base boundary and create new boundary object
            offset_lat_range = [lat + lat_offset for lat in lat_range]
            offset_long_range = [
                longitude_domain(long + long_offset) for long in long_range
            ]

            offset_bounds = Boundary(offset_lat_range, offset_long_range)
            offset_cellbox = CellBox(offset_bounds, 1)

            # Make sure it returns the correct case
            self.assertEqual(
                ng.get_global_mesh_neighbour_case(base_cellbox, offset_cellbox),
                direction,
            )

        # Final test: make sure that two boundaries that don't touch return an invalid direction (0)
        base_bounds = Boundary(lat_range, [160, 180])
        base_cellbox = CellBox(base_bounds, 0)
        offset_bounds = Boundary(lat_range, [0, 20])
        offset_cellbox = CellBox(offset_bounds, 1)
        # Make sure it returns the correct case
        self.assertEqual(
            ng.get_global_mesh_neighbour_case(base_cellbox, offset_cellbox), 0
        )

    def test_remove_neighbour(self):
        # Create a new neighbourgraph to edit freely
        ng = create_ng_from_dict(self.ng_dict_3x3)
        # Remove element 3 from the NE direction of cb 5 in the neighbourgraph
        ng.remove_neighbour(5, Direction.north_east, 3)

        # Do this again by manually editing the neighbourgraph
        manually_adjusted_ng = copy.deepcopy(self.ng_dict_3x3)
        manually_adjusted_ng[5][Direction.north_east] = []

        self.assertEqual(ng.get_graph(), manually_adjusted_ng)

    def test_initialise_neighbour_graph(self):
        # Initialise a new neighbour graph to modify
        ng = NeighbourGraph()
        # Initial CB layout
        cbs = [
            CellBox(Boundary([2, 3], [0, 1]), 1),
            CellBox(Boundary([2, 3], [1, 2]), 2),
            CellBox(Boundary([2, 3], [2, 3]), 3),
            CellBox(Boundary([1, 2], [0, 1]), 4),
            CellBox(Boundary([1, 2], [1, 2]), 5),
            CellBox(Boundary([1, 2], [2, 3]), 6),
            CellBox(Boundary([0, 1], [0, 1]), 7),
            CellBox(Boundary([0, 1], [1, 2]), 8),
            CellBox(Boundary([0, 1], [2, 3]), 9),
        ]
        # Create neighbourgraph based on cb list
        ng.initialise_neighbour_graph(cbs, 3)

        # Manually define what the output should be
        reference_neighbour_graph = {
            0: {1: [4], 2: [1], 3: [], 4: [], -1: [], -2: [], -3: [], -4: [3]},
            1: {1: [5], 2: [2], 3: [], 4: [], -1: [], -2: [0], -3: [3], -4: [4]},
            2: {1: [], 2: [], 3: [], 4: [], -1: [], -2: [1], -3: [4], -4: [5]},
            3: {1: [7], 2: [4], 3: [1], 4: [0], -1: [], -2: [], -3: [], -4: [6]},
            4: {1: [8], 2: [5], 3: [2], 4: [1], -1: [0], -2: [3], -3: [6], -4: [7]},
            5: {1: [], 2: [], 3: [], 4: [2], -1: [1], -2: [4], -3: [7], -4: [8]},
            6: {1: [], 2: [7], 3: [4], 4: [3], -1: [], -2: [], -3: [], -4: []},
            7: {1: [], 2: [8], 3: [5], 4: [4], -1: [3], -2: [6], -3: [], -4: []},
            8: {1: [], 2: [], 3: [], 4: [5], -1: [4], -2: [7], -3: [], -4: []},
        }

        self.assertEqual(ng.get_graph(), reference_neighbour_graph)

    def test_initialise_map(self):
        # Initialise a new neighbour graph to modify
        ng = NeighbourGraph()
        # Initial CB layout
        cbs = [
            CellBox(Boundary([2, 3], [0, 1]), 1),
            CellBox(Boundary([2, 3], [1, 2]), 2),
            CellBox(Boundary([2, 3], [2, 3]), 3),
            CellBox(Boundary([1, 2], [0, 1]), 4),
            CellBox(Boundary([1, 2], [1, 2]), 5),
            CellBox(Boundary([1, 2], [2, 3]), 6),
            CellBox(Boundary([0, 1], [0, 1]), 7),
            CellBox(Boundary([0, 1], [1, 2]), 8),
            CellBox(Boundary([0, 1], [2, 3]), 9),
        ]

        # Manually define what the output should be
        reference_neighbour_graph = {
            0: {1: [4], 2: [1], 3: [], 4: [], -1: [], -2: [], -3: [], -4: [3]},
            1: {1: [5], 2: [2], 3: [], 4: [], -1: [], -2: [0], -3: [3], -4: [4]},
            2: {1: [], 2: [], 3: [], 4: [], -1: [], -2: [1], -3: [4], -4: [5]},
            3: {1: [7], 2: [4], 3: [1], 4: [0], -1: [], -2: [], -3: [], -4: [6]},
            4: {1: [8], 2: [5], 3: [2], 4: [1], -1: [0], -2: [3], -3: [6], -4: [7]},
            5: {1: [], 2: [], 3: [], 4: [2], -1: [1], -2: [4], -3: [7], -4: [8]},
            6: {1: [], 2: [7], 3: [4], 4: [3], -1: [], -2: [], -3: [], -4: []},
            7: {1: [], 2: [8], 3: [5], 4: [4], -1: [3], -2: [6], -3: [], -4: []},
            8: {1: [], 2: [], 3: [], 4: [5], -1: [4], -2: [7], -3: [], -4: []},
        }

        # Run through each cellbox and create the neighbour map
        for cb in cbs:
            cb_idx = cbs.index(cb)
            neighbour_map = ng.initialise_map(cb_idx, 3, 9)

            self.assertEqual(neighbour_map, reference_neighbour_graph[cb_idx])

    def test_set_global_mesh(self):
        global_ng = create_ng_from_dict(self.ng_dict_3x3, global_mesh=True)
        nonglobal_ng = create_ng_from_dict(self.ng_dict_3x3, global_mesh=False)

        self.assertTrue(global_ng._is_global_mesh)
        self.assertFalse(nonglobal_ng._is_global_mesh)

    def test_is_global_mesh(self):
        global_ng = create_ng_from_dict(self.ng_dict_3x3, global_mesh=True)
        nonglobal_ng = create_ng_from_dict(self.ng_dict_3x3, global_mesh=False)

        self.assertTrue(global_ng.is_global_mesh())
        self.assertFalse(nonglobal_ng.is_global_mesh())

    def test_get_neighbour_map(self):
        ng = create_ng_from_dict(self.ng_dict_3x3)

        self.assertEqual(ng.get_neighbour_map(1), self.ng_dict_3x3[1])
