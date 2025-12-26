import unittest
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.boundary import Boundary


class TestAggregatedCellBox(unittest.TestCase):
    def setUp(self):
        arbitrary_agg_data = {"dummy_data": 1}

        self.dummy_agg_cb = AggregatedCellBox(
            Boundary([45, 60], [45, 60]), arbitrary_agg_data, "0"
        )
        self.arbitrary_agg_cb = AggregatedCellBox(
            Boundary([45, 60], [45, 60]), arbitrary_agg_data, "1"
        )
        self.equatorial_agg_cb = AggregatedCellBox(
            Boundary([-10, 10], [45, 60]), arbitrary_agg_data, "2"
        )
        self.meridian_agg_cb = AggregatedCellBox(
            Boundary([45, 60], [-10, 10]), arbitrary_agg_data, "3"
        )
        self.antimeridian_agg_cb = AggregatedCellBox(
            Boundary([45, 60], [170, -170]), arbitrary_agg_data, "4"
        )

    def test_from_json(self):
        agg_cb_json = {
            "geometry": "POLYGON ((-175 49, -175 51.5, -170 51.5, -170 49, -175 49))",
            "cx": -172.5,
            "cy": 50.25,
            "dcx": 2.5,
            "dcy": 1.25,
            "elevation": -3270.0,
            "SIC": 0.0,
            "thickness": 0.82,
            "density": 900.0,
            "id": "1",
        }

        agg_cb_from_json = AggregatedCellBox.from_json(agg_cb_json)

        agg_cb_boundary = Boundary.from_poly_string(agg_cb_json["geometry"])

        data_keys = ["elevation", "SIC", "thickness", "density"]
        agg_cb_data = {k: agg_cb_json[k] for k in data_keys if k in agg_cb_json}

        agg_cb_id = agg_cb_json["id"]

        agg_cb_initialised_normally = AggregatedCellBox(
            agg_cb_boundary, agg_cb_data, agg_cb_id
        )

        self.assertEqual(agg_cb_from_json, agg_cb_initialised_normally)

    def test_set_bounds(self):
        dummy_bounds = Boundary([10, 20], [30, 40])
        self.dummy_agg_cb.set_bounds(dummy_bounds)
        self.assertEqual(self.dummy_agg_cb.boundary, dummy_bounds)

    def test_get_bounds(self):
        dummy_bounds = Boundary([45, 60], [45, 60])
        self.dummy_agg_cb.boundary = dummy_bounds
        self.assertEqual(dummy_bounds, self.arbitrary_agg_cb.get_bounds())

    def test_set_id(self):
        dummy_id = "123"
        self.dummy_agg_cb.set_id(dummy_id)
        self.assertEqual(self.dummy_agg_cb.id, dummy_id)

    def test_get_id(self):
        dummy_id = "321"
        self.dummy_agg_cb.id = dummy_id
        self.assertEqual(self.dummy_agg_cb.get_id(), dummy_id)

    def test_set_agg_data(self):
        dummy_agg_data = {"dummy_data": "123"}
        self.dummy_agg_cb.set_agg_data(dummy_agg_data)
        self.assertEqual(self.dummy_agg_cb.agg_data, dummy_agg_data)

    def test_get_agg_data(self):
        dummy_agg_data = {"dummy_data": "321"}
        self.dummy_agg_cb.agg_data = dummy_agg_data
        self.assertEqual(self.dummy_agg_cb.get_agg_data(), dummy_agg_data)

    def test_to_json(self):
        agg_cb_json = {
            "geometry": "POLYGON ((-175 49, -175 51.5, -170 51.5, -170 49, -175 49))",
            "cx": -172.5,
            "cy": 50.25,
            "dcx": 2.5,
            "dcy": 1.25,
            "elevation": -3270.0,
            "SIC": 0.0,
            "thickness": 0.82,
            "density": 900.0,
            "id": "1",
        }
        agg_cb_boundary = Boundary.from_poly_string(agg_cb_json["geometry"])

        data_keys = ["elevation", "SIC", "thickness", "density"]
        agg_cb_data = {k: agg_cb_json[k] for k in data_keys if k in agg_cb_json}

        agg_cb_id = agg_cb_json["id"]

        agg_cb = AggregatedCellBox(agg_cb_boundary, agg_cb_data, agg_cb_id)

        self.assertEqual(agg_cb.to_json(), agg_cb_json)

    def test_contains_point(self):
        self.assertTrue(self.arbitrary_agg_cb.contains_point(50, 50))
        self.assertTrue(self.equatorial_agg_cb.contains_point(0, 50))
        self.assertTrue(self.meridian_agg_cb.contains_point(50, 0))
        self.assertTrue(self.antimeridian_agg_cb.contains_point(50, 179))
