import unittest
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.boundary import Boundary


class TestAggregatedCellBox(unittest.TestCase):
    """Tests for AggregatedCellBox class"""

    def setUp(self):
        """Set up test aggregated cellboxes"""
        arbitrary_agg_data = {'dummy_data': 1}

        self.dummy_agg_cb = AggregatedCellBox(Boundary([45, 60], [45, 60]), arbitrary_agg_data, '0')
        self.arbitrary_agg_cb = AggregatedCellBox(Boundary([45, 60], [45, 60]), arbitrary_agg_data, '1')
        self.equatorial_agg_cb = AggregatedCellBox(Boundary([-10, 10], [45, 60]), arbitrary_agg_data, '2')
        self.meridian_agg_cb = AggregatedCellBox(Boundary([45, 60], [-10, 10]), arbitrary_agg_data, '3')
        self.antimeridian_agg_cb = AggregatedCellBox(Boundary([45, 60], [170, -170]), arbitrary_agg_data, '4')

    def test_from_json(self):
        """Test creating aggregated cellbox from JSON"""
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
            "id": "1"
        }

        agg_cb_from_json = AggregatedCellBox.from_json(agg_cb_json)
        agg_cb_boundary = Boundary.from_poly_string(agg_cb_json['geometry'])
        
        data_keys = ['elevation', 'SIC', 'thickness', 'density']
        agg_cb_data = {k: agg_cb_json[k] for k in data_keys if k in agg_cb_json}
        agg_cb_id = agg_cb_json['id']

        agg_cb_initialised_normally = AggregatedCellBox(agg_cb_boundary, agg_cb_data, agg_cb_id)
        
        self.assertEqual(agg_cb_from_json, agg_cb_initialised_normally)

    def test_getter_setter_pairs(self):
        """Test getter and setter method pairs"""
        test_cases = [
            ('boundary', Boundary([10, 20], [30, 40]), 'get_bounds', 'set_bounds'),
            ('id', '123', 'get_id', 'set_id'),
            ('agg_data', {'dummy_data': '456'}, 'get_agg_data', 'set_agg_data'),
        ]
        
        for attr, test_value, getter, setter in test_cases:
            with self.subTest(attribute=attr):
                # Test setter
                getattr(self.dummy_agg_cb, setter)(test_value)
                self.assertEqual(getattr(self.dummy_agg_cb, attr), test_value)
                
                # Test getter
                setattr(self.dummy_agg_cb, attr, test_value)
                self.assertEqual(getattr(self.dummy_agg_cb, getter)(), test_value)

    def test_to_json(self):
        """Test converting aggregated cellbox to JSON"""
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
            "id": "1"
        }
        agg_cb_boundary = Boundary.from_poly_string(agg_cb_json['geometry'])
        
        data_keys = ['elevation', 'SIC', 'thickness', 'density']
        agg_cb_data = {k: agg_cb_json[k] for k in data_keys if k in agg_cb_json}
        agg_cb_id = agg_cb_json['id']

        agg_cb = AggregatedCellBox(agg_cb_boundary, agg_cb_data, agg_cb_id)

        self.assertEqual(agg_cb.to_json(), agg_cb_json)
    
    def test_contains_point(self):
        """Test point containment check"""
        test_cases = [
            (self.arbitrary_agg_cb, 50, 50, True),
            (self.equatorial_agg_cb, 0, 50, True),
            (self.meridian_agg_cb, 50, 0, True),
            (self.antimeridian_agg_cb, 50, 179, True),
        ]
        
        for cellbox, lat, lon, expected in test_cases:
            with self.subTest(lat=lat, lon=lon):
                self.assertEqual(cellbox.contains_point(lat, lon), expected)