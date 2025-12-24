import unittest
import pytest
import shapely
from datetime import datetime, timedelta

from meshiphi.mesh_generation.boundary import Boundary


class TestBoundary(unittest.TestCase):
    """Tests for Boundary class"""
    
    def setUp(self):
        """Set up boundaries that are interesting test cases"""
        self.temporal_boundary = Boundary([10, 20], [30, 40], ['1970-01-01', '2021-12-31'])
        self.arbitrary_boundary = Boundary([10, 20], [30, 40])
        self.meridian_boundary = Boundary([-50, -40], [-10, 10])
        self.antimeridian_boundary = Boundary([-50, -40], [170, -170])
        self.equatorial_boundary = Boundary([-10, 10], [30, 40])

        # Mapping for parametric tests
        self.boundaries = {
            'arbitrary': self.arbitrary_boundary,
            'meridian': self.meridian_boundary,
            'antimeridian': self.antimeridian_boundary,
            'equatorial': self.equatorial_boundary,
            'temporal': self.temporal_boundary
        }

    def test_load_from_json(self):
        """Test loading boundary from JSON config"""
        boundary_config = {
            "region": {
                "lat_min": 10,
                "lat_max": 20,
                "long_min": 30,
                "long_max": 40,
                "start_time": "1970-01-01",
                "end_time": "2021-12-31"
            }
        }
        boundary = Boundary.from_json(boundary_config)
        self.assertEqual(boundary, self.arbitrary_boundary)

    def test_from_poly_string(self):
        """Test creating boundary from polygon strings"""
        test_cases = [
            (self.arbitrary_boundary, "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
            (self.meridian_boundary, "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
            (self.antimeridian_boundary, "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"),
            (self.equatorial_boundary, "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
        ]
        
        for expected_boundary, poly_string in test_cases:
            with self.subTest(poly_string=poly_string):
                self.assertEqual(expected_boundary, Boundary.from_poly_string(poly_string))

    def test_parse_datetime_relative(self):
        """Test parsing relative datetime strings"""
        date_format = '%Y-%m-%d'
        
        test_cases = [
            ('TODAY', 0),
            ('TODAY - 5', -5),
            ('TODAY + 5', 5)
        ]
        
        for date_string, day_offset in test_cases:
            with self.subTest(date_string=date_string):
                expected_datetime = datetime.today() + timedelta(days=day_offset)
                expected_string = expected_datetime.strftime(date_format)
                self.assertEqual(Boundary.parse_datetime(date_string), expected_string)

    def test_parse_datetime_absolute(self):
        """Test parsing absolute datetime strings"""
        test_datestring = '2000-01-01'
        self.assertEqual(Boundary.parse_datetime(test_datestring), '2000-01-01')

    def test_parse_datetime_malformed(self):
        """Test that malformed dates raise ValueError"""
        malformed_dates = ['20000101', '01-01-2000', 'Jan 01 2000', '1st Jan 2000']
        
        for malformed_date in malformed_dates:
            with self.subTest(malformed_date=malformed_date):
                self.assertRaises(ValueError, Boundary.parse_datetime, malformed_date)

    def test_validate_bounds(self):
        """Test that invalid bounds raise ValueError"""
        valid_lat_range = [10, 20]
        valid_long_range = [10, 20]
        valid_time_range = ['2000-01-01', '2000-12-31']

        invalid_cases = [
            ([20, 10], valid_long_range, valid_time_range, "invalid_lat"),
            (valid_lat_range, [-190, 190], valid_time_range, "invalid_long"),
            (valid_lat_range, valid_long_range, ['2000-12-31', '2000-01-01'], "invalid_time"),
            ([], valid_long_range, valid_time_range, "empty_lat"),
            (valid_lat_range, [], valid_time_range, "empty_long"),
        ]
        
        for lat_range, long_range, time_range, description in invalid_cases:
            with self.subTest(case=description):
                self.assertRaises(ValueError, Boundary, lat_range, long_range, time_range)

    def test_get_bounds(self):
        """Test getting boundary coordinates"""
        test_cases = [
            ('arbitrary', [[30.0, 10.0], [30.0, 20.0], [40.0, 20.0], [40.0, 10.0], [30.0, 10.0]]),
            ('meridian', [[-10.0, -50.0], [-10.0, -40.0], [10.0, -40.0], [10.0, -50.0], [-10.0, -50.0]]),
            ('antimeridian', [[170.0, -50.0], [170.0, -40.0], [-170.0, -40.0], [-170.0, -50.0], [170.0, -50.0]]),
            ('equatorial', [[30.0, -10.0], [30.0, 10.0], [40.0, 10.0], [40.0, -10.0], [30.0, -10.0]]),
        ]
        
        for boundary_name, expected_bounds in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_bounds(), expected_bounds)

    def test_getcx(self):
        """Test getting center x coordinate"""
        test_cases = [('arbitrary', 35), ('meridian', 0), ('antimeridian', 180), ('equatorial', 35)]
        
        for boundary_name, expected_cx in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].getcx(), expected_cx)

    def test_getcy(self):
        """Test getting center y coordinate"""
        test_cases = [('arbitrary', 15), ('meridian', -45), ('antimeridian', -45), ('equatorial', 0)]
        
        for boundary_name, expected_cy in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].getcy(), expected_cy)

    def test_get_height(self):
        """Test getting boundary height"""
        test_cases = [('arbitrary', 10), ('meridian', 10), ('antimeridian', 10), ('equatorial', 20)]
        
        for boundary_name, expected_height in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_height(), expected_height)

    def test_get_width(self):
        """Test getting boundary width"""
        test_cases = [('arbitrary', 10), ('meridian', 20), ('antimeridian', 20), ('equatorial', 10)]
        
        for boundary_name, expected_width in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_width(), expected_width)

    def test_get_time_range(self):
        """Test getting time range"""
        self.assertEqual(self.temporal_boundary.get_time_range(), ['1970-01-01', '2021-12-31'])

    def test_getdcx(self):
        """Test getting half-width"""
        test_cases = [('arbitrary', 5), ('meridian', 10), ('antimeridian', 10), ('equatorial', 5)]
        
        for boundary_name, expected_dcx in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].getdcx(), expected_dcx)

    def test_getdcy(self):
        """Test getting half-height"""
        test_cases = [('arbitrary', 5), ('meridian', 5), ('antimeridian', 5), ('equatorial', 10)]
        
        for boundary_name, expected_dcy in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].getdcy(), expected_dcy)

    def test_get_lat_min(self):
        """Test getting minimum latitude"""
        test_cases = [('arbitrary', 10), ('meridian', -50), ('antimeridian', -50), ('equatorial', -10)]
        
        for boundary_name, expected_min in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_lat_min(), expected_min)

    def test_get_lat_max(self):
        """Test getting maximum latitude"""
        test_cases = [('arbitrary', 20), ('meridian', -40), ('antimeridian', -40), ('equatorial', 10)]
        
        for boundary_name, expected_max in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_lat_max(), expected_max)

    def test_get_long_min(self):
        """Test getting minimum longitude"""
        test_cases = [('arbitrary', 30), ('meridian', -10), ('antimeridian', 170), ('equatorial', 30)]
        
        for boundary_name, expected_min in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_long_min(), expected_min)

    def test_get_long_max(self):
        """Test getting maximum longitude"""
        test_cases = [('arbitrary', 40), ('meridian', 10), ('antimeridian', -170), ('equatorial', 40)]
        
        for boundary_name, expected_max in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].get_long_max(), expected_max)

    def test_get_time_min(self):
        """Test getting minimum time"""
        self.assertEqual(self.temporal_boundary.get_time_min(), '1970-01-01')

    def test_get_time_max(self):
        """Test getting maximum time"""
        self.assertEqual(self.temporal_boundary.get_time_max(), '2021-12-31')

    def test_calc_size(self):
        """Test calculating boundary size"""
        test_cases = [
            ('arbitrary', 1092308.5466932291),
            ('meridian', 1354908.6430361348),
            ('antimeridian', 1354908.6430361343),
            ('equatorial', 1756355.5062820115),
        ]
        
        for boundary_name, expected_size in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertAlmostEqual(self.boundaries[boundary_name].calc_size(), expected_size, 5)

    def test_to_polygon(self):
        """Test converting boundary to polygon"""
        test_cases = [
            ('arbitrary', "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
            ('meridian', "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
            ('antimeridian', "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"),
            ('equatorial', "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
        ]
        
        for boundary_name, poly_wkt in test_cases:
            with self.subTest(boundary=boundary_name):
                expected_polygon = shapely.wkt.loads(poly_wkt)
                self.assertEqual(self.boundaries[boundary_name].to_polygon(), expected_polygon)

    def test_to_poly_string(self):
        """Test converting boundary to polygon string"""
        test_cases = [
            ('arbitrary', "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
            ('meridian', "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
            ('antimeridian', "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"),
            ('equatorial', "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
        ]
        
        for boundary_name, expected_poly_string in test_cases:
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].to_poly_string(), expected_poly_string)

    def test_split(self):
        """Test splitting boundary into four sub-boundaries"""
        test_cases = {
            'temporal': [
                Boundary([10, 15], [30, 35], ['1970-01-01', '2021-12-31']),
                Boundary([15, 20], [30, 35], ['1970-01-01', '2021-12-31']),
                Boundary([10, 15], [35, 40], ['1970-01-01', '2021-12-31']),
                Boundary([15, 20], [35, 40], ['1970-01-01', '2021-12-31'])
            ],
            'arbitrary': [
                Boundary([10, 15], [30, 35]),
                Boundary([15, 20], [30, 35]),
                Boundary([10, 15], [35, 40]),
                Boundary([15, 20], [35, 40])
            ],
            'meridian': [
                Boundary([-50, -45], [-10, 0]),
                Boundary([-45, -40], [-10, 0]),
                Boundary([-50, -45], [0, 10]),
                Boundary([-45, -40], [0, 10])
            ],
            'antimeridian': [
                Boundary([-50, -45], [170, 180]),
                Boundary([-45, -40], [170, 180]),
                Boundary([-50, -45], [180, -170]),
                Boundary([-45, -40], [180, -170])
            ],
            'equatorial': [
                Boundary([-10, 0], [30, 35]),
                Boundary([0, 10], [30, 35]),
                Boundary([-10, 0], [35, 40]),
                Boundary([0, 10], [35, 40])
            ],
        }
        
        for boundary_name, expected_splits in test_cases.items():
            with self.subTest(boundary=boundary_name):
                self.assertEqual(self.boundaries[boundary_name].split(), expected_splits)