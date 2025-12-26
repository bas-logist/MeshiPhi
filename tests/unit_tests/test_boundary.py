import unittest
import shapely
from datetime import datetime
from datetime import timedelta

from meshiphi.mesh_generation.boundary import Boundary


class TestBoundary(unittest.TestCase):
    def setUp(self):
        # Set up boundaries that are interesting test cases
        # Note that these aren't used in all the tests
        self.temporal_boundary = Boundary(
            [10, 20], [30, 40], ["1970-01-01", "2021-12-31"]
        )
        self.arbitrary_boundary = Boundary([10, 20], [30, 40])
        self.meridian_boundary = Boundary([-50, -40], [-10, 10])
        self.antimeridian_boundary = Boundary([-50, -40], [170, -170])
        self.equatorial_boundary = Boundary([-10, 10], [30, 40])

    def test_load_from_json(self):
        # Create a dict in same format as expected JSON inputs
        # Dict/JSON using same bounds as self.arbitrary_boundary
        boundary_config = {
            "region": {
                "lat_min": 10,
                "lat_max": 20,
                "long_min": 30,
                "long_max": 40,
                "start_time": "1970-01-01",
                "end_time": "2021-12-31",
            }
        }

        boundary = Boundary.from_json(boundary_config)
        self.assertEqual(boundary, self.arbitrary_boundary)

    def test_from_poly_string(self):
        arbitrary_poly_string = "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"
        self.assertEqual(
            self.arbitrary_boundary, Boundary.from_poly_string(arbitrary_poly_string)
        )

        meridian_poly_string = "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"
        self.assertEqual(
            self.meridian_boundary, Boundary.from_poly_string(meridian_poly_string)
        )

        antimeridian_poly_string = "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"
        self.assertEqual(
            self.antimeridian_boundary,
            Boundary.from_poly_string(antimeridian_poly_string),
        )

        equatorial_poly_string = "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"
        self.assertEqual(
            self.equatorial_boundary, Boundary.from_poly_string(equatorial_poly_string)
        )

    def test_parse_datetime(self):
        desired_date_format = "%Y-%m-%d"

        test_current_datestring = "TODAY"
        soln_current_datetime = datetime.today()
        soln_current_datestring = soln_current_datetime.strftime(desired_date_format)
        self.assertEqual(
            Boundary.parse_datetime(test_current_datestring), soln_current_datestring
        )

        test_past_datestring = "TODAY - 5"
        soln_past_datetime = datetime.today() - timedelta(days=5)
        soln_past_datestring = soln_past_datetime.strftime(desired_date_format)
        self.assertEqual(
            Boundary.parse_datetime(test_past_datestring), soln_past_datestring
        )

        test_future_datestring = "TODAY + 5"
        soln_future_datetime = datetime.today() + timedelta(days=5)
        soln_future_datestring = soln_future_datetime.strftime(desired_date_format)
        self.assertEqual(
            Boundary.parse_datetime(test_future_datestring), soln_future_datestring
        )

        test_absolute_datestring = "2000-01-01"
        soln_absolute_datestring = "2000-01-01"
        self.assertEqual(
            Boundary.parse_datetime(test_absolute_datestring), soln_absolute_datestring
        )

        malformed_datestring_1 = "20000101"
        malformed_datestring_2 = "01-01-2000"
        malformed_datestring_3 = "Jan 01 2000"
        malformed_datestring_4 = "1st Jan 2000"

        self.assertRaises(ValueError, Boundary.parse_datetime, malformed_datestring_1)
        self.assertRaises(ValueError, Boundary.parse_datetime, malformed_datestring_2)
        self.assertRaises(ValueError, Boundary.parse_datetime, malformed_datestring_3)
        self.assertRaises(ValueError, Boundary.parse_datetime, malformed_datestring_4)

    def test_validate_bounds(self):
        # Set up constants for later legibility
        valid_lat_range = [10, 20]
        valid_long_range = [10, 20]
        valid_time_range = ["2000-01-01", "2000-12-31"]

        invalid_lat_range = [20, 10]
        invalid_long_range = [-190, 190]
        invalid_time_range = ["2000-12-31", "2000-01-01"]

        empty_range = []

        self.assertRaises(
            ValueError, Boundary, invalid_lat_range, valid_long_range, valid_time_range
        )
        self.assertRaises(
            ValueError, Boundary, valid_lat_range, invalid_long_range, valid_time_range
        )
        self.assertRaises(
            ValueError, Boundary, valid_lat_range, valid_long_range, invalid_time_range
        )

        self.assertRaises(
            ValueError, Boundary, empty_range, valid_long_range, valid_time_range
        )
        self.assertRaises(
            ValueError, Boundary, valid_lat_range, empty_range, valid_time_range
        )
        # Empty time_range is valid, so won't raise an error

    def test_get_bounds(self):
        arbitrary_bounds = [
            [30.0, 10.0],
            [30.0, 20.0],
            [40.0, 20.0],
            [40.0, 10.0],
            [30.0, 10.0],
        ]
        self.assertEqual(arbitrary_bounds, self.arbitrary_boundary.get_bounds())

        meridian_bounds = [
            [-10.0, -50.0],
            [-10.0, -40.0],
            [10.0, -40.0],
            [10.0, -50.0],
            [-10.0, -50.0],
        ]
        self.assertEqual(meridian_bounds, self.meridian_boundary.get_bounds())

        antimeridian_bounds = [
            [170.0, -50.0],
            [170.0, -40.0],
            [-170.0, -40.0],
            [-170.0, -50.0],
            [170.0, -50.0],
        ]
        self.assertEqual(antimeridian_bounds, self.antimeridian_boundary.get_bounds())

        equatorial_bounds = [
            [30.0, -10.0],
            [30.0, 10.0],
            [40.0, 10.0],
            [40.0, -10.0],
            [30.0, -10.0],
        ]
        self.assertEqual(equatorial_bounds, self.equatorial_boundary.get_bounds())

    def test_getcx(self):
        self.assertEqual(35, self.arbitrary_boundary.getcx())
        self.assertEqual(0, self.meridian_boundary.getcx())
        self.assertEqual(180, self.antimeridian_boundary.getcx())
        self.assertEqual(35, self.equatorial_boundary.getcx())

    def test_getcy(self):
        self.assertEqual(15, self.arbitrary_boundary.getcy())
        self.assertEqual(-45, self.meridian_boundary.getcy())
        self.assertEqual(-45, self.antimeridian_boundary.getcy())
        self.assertEqual(0, self.equatorial_boundary.getcy())

    def test_get_height(self):
        self.assertEqual(10, self.arbitrary_boundary.get_height())
        self.assertEqual(10, self.meridian_boundary.get_height())
        self.assertEqual(10, self.antimeridian_boundary.get_height())
        self.assertEqual(20, self.equatorial_boundary.get_height())

    def test_get_width(self):
        self.assertEqual(10, self.arbitrary_boundary.get_width())
        self.assertEqual(20, self.meridian_boundary.get_width())
        self.assertEqual(20, self.antimeridian_boundary.get_width())
        self.assertEqual(10, self.equatorial_boundary.get_width())

    def test_get_time_range(self):
        self.assertEqual(
            ["1970-01-01", "2021-12-31"], self.temporal_boundary.get_time_range()
        )

    def test_getdcx(self):
        self.assertEqual(5, self.arbitrary_boundary.getdcx())
        self.assertEqual(10, self.meridian_boundary.getdcx())
        self.assertEqual(10, self.antimeridian_boundary.getdcx())
        self.assertEqual(5, self.equatorial_boundary.getdcx())

    def test_getdcy(self):
        self.assertEqual(5, self.arbitrary_boundary.getdcy())
        self.assertEqual(5, self.meridian_boundary.getdcy())
        self.assertEqual(5, self.antimeridian_boundary.getdcy())
        self.assertEqual(10, self.equatorial_boundary.getdcy())

    def test_get_lat_min(self):
        self.assertEqual(10, self.arbitrary_boundary.get_lat_min())
        self.assertEqual(-50, self.meridian_boundary.get_lat_min())
        self.assertEqual(-50, self.antimeridian_boundary.get_lat_min())
        self.assertEqual(-10, self.equatorial_boundary.get_lat_min())

    def test_get_lat_max(self):
        self.assertEqual(20, self.arbitrary_boundary.get_lat_max())
        self.assertEqual(-40, self.meridian_boundary.get_lat_max())
        self.assertEqual(-40, self.antimeridian_boundary.get_lat_max())
        self.assertEqual(10, self.equatorial_boundary.get_lat_max())

    def test_get_long_min(self):
        self.assertEqual(30, self.arbitrary_boundary.get_long_min())
        self.assertEqual(-10, self.meridian_boundary.get_long_min())
        self.assertEqual(170, self.antimeridian_boundary.get_long_min())
        self.assertEqual(30, self.equatorial_boundary.get_long_min())

    def test_get_long_max(self):
        self.assertEqual(40, self.arbitrary_boundary.get_long_max())
        self.assertEqual(10, self.meridian_boundary.get_long_max())
        self.assertEqual(-170, self.antimeridian_boundary.get_long_max())
        self.assertEqual(40, self.equatorial_boundary.get_long_max())

    def test_get_time_min(self):
        self.assertEqual("1970-01-01", self.temporal_boundary.get_time_min())

    def test_get_time_max(self):
        self.assertEqual("2021-12-31", self.temporal_boundary.get_time_max())

    def test_calc_size(self):
        # Calculate accurately to 5 decimal places
        self.assertAlmostEqual(
            1092308.5466932291, self.arbitrary_boundary.calc_size(), 5
        )
        self.assertAlmostEqual(
            1354908.6430361348, self.meridian_boundary.calc_size(), 5
        )
        self.assertAlmostEqual(
            1354908.6430361343, self.antimeridian_boundary.calc_size(), 5
        )
        self.assertAlmostEqual(
            1756355.5062820115, self.equatorial_boundary.calc_size(), 5
        )

    def test_to_polygon(self):
        arbitrary_polygon = shapely.wkt.loads(
            "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"
        )
        self.assertEqual(self.arbitrary_boundary.to_polygon(), arbitrary_polygon)

        meridian_polygon = shapely.wkt.loads(
            "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"
        )
        self.assertEqual(self.meridian_boundary.to_polygon(), meridian_polygon)

        antimeridian_polygon = shapely.wkt.loads(
            "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"
        )
        self.assertEqual(self.antimeridian_boundary.to_polygon(), antimeridian_polygon)

        equatorial_polygon = shapely.wkt.loads(
            "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"
        )
        self.assertEqual(self.equatorial_boundary.to_polygon(), equatorial_polygon)

    def test_to_poly_string(self):
        arbitrary_poly_string = "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"
        self.assertEqual(
            self.arbitrary_boundary.to_poly_string(), arbitrary_poly_string
        )

        meridian_poly_string = "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"
        self.assertEqual(self.meridian_boundary.to_poly_string(), meridian_poly_string)

        antimeridian_poly_string = "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))"
        self.assertEqual(
            self.antimeridian_boundary.to_poly_string(), antimeridian_poly_string
        )

        equatorial_poly_string = "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"
        self.assertEqual(
            self.equatorial_boundary.to_poly_string(), equatorial_poly_string
        )

    def test_split(self):
        temporal_split_boundaries = [
            Boundary([10, 15], [30, 35], ["1970-01-01", "2021-12-31"]),
            Boundary([15, 20], [30, 35], ["1970-01-01", "2021-12-31"]),
            Boundary([10, 15], [35, 40], ["1970-01-01", "2021-12-31"]),
            Boundary([15, 20], [35, 40], ["1970-01-01", "2021-12-31"]),
        ]

        arbitrary_split_boundaries = [
            Boundary([10, 15], [30, 35]),
            Boundary([15, 20], [30, 35]),
            Boundary([10, 15], [35, 40]),
            Boundary([15, 20], [35, 40]),
        ]

        meridian_split_boundaries = [
            Boundary([-50, -45], [-10, 0]),
            Boundary([-45, -40], [-10, 0]),
            Boundary([-50, -45], [0, 10]),
            Boundary([-45, -40], [0, 10]),
        ]

        antimeridian_split_boundaries = [
            Boundary([-50, -45], [170, 180]),
            Boundary([-45, -40], [170, 180]),
            Boundary([-50, -45], [180, -170]),
            Boundary([-45, -40], [180, -170]),
        ]

        equatorial_split_boundaries = [
            Boundary([-10, 0], [30, 35]),
            Boundary([0, 10], [30, 35]),
            Boundary([-10, 0], [35, 40]),
            Boundary([0, 10], [35, 40]),
        ]

        self.assertEqual(temporal_split_boundaries, self.temporal_boundary.split())

        self.assertEqual(arbitrary_split_boundaries, self.arbitrary_boundary.split())

        self.assertEqual(meridian_split_boundaries, self.meridian_boundary.split())

        self.assertEqual(
            antimeridian_split_boundaries, self.antimeridian_boundary.split()
        )

        self.assertEqual(equatorial_split_boundaries, self.equatorial_boundary.split())
