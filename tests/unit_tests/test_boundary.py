"""
Boundary class tests.
"""

from datetime import datetime, timedelta

import pytest
import shapely

from meshiphi.mesh_generation.boundary import Boundary


def test_load_from_json(temporal_boundary):
    """Test loading boundary from JSON config"""
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
    assert boundary == temporal_boundary


@pytest.mark.parametrize(
    ("boundary_fixture", "poly_string"),
    [
        ("arbitrary_boundary", "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
        ("meridian_boundary", "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
        (
            "antimeridian_boundary",
            "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))",
        ),
        ("equatorial_boundary", "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
    ],
)
def test_from_poly_string(boundary_fixture, poly_string, request):
    """Test creating boundary from polygon strings"""
    expected_boundary = request.getfixturevalue(boundary_fixture)
    assert expected_boundary == Boundary.from_poly_string(poly_string)


@pytest.mark.parametrize(
    ("date_string", "day_offset"), [("TODAY", 0), ("TODAY - 5", -5), ("TODAY + 5", 5)]
)
def test_parse_datetime_relative(date_string, day_offset):
    """Test parsing relative datetime strings"""
    date_format = "%Y-%m-%d"
    expected_datetime = datetime.today() + timedelta(days=day_offset)
    expected_string = expected_datetime.strftime(date_format)
    assert Boundary.parse_datetime(date_string) == expected_string


def test_parse_datetime_absolute():
    """Test parsing absolute datetime strings"""
    test_datestring = "2000-01-01"
    assert Boundary.parse_datetime(test_datestring) == "2000-01-01"


@pytest.mark.parametrize(
    "malformed_date", ["20000101", "01-01-2000", "Jan 01 2000", "1st Jan 2000"]
)
def test_parse_datetime_malformed(malformed_date):
    """Test that malformed dates raise ValueError"""
    with pytest.raises(ValueError, match="Incorrect date format given"):
        Boundary.parse_datetime(malformed_date)


@pytest.mark.parametrize(
    ("lat_range", "long_range", "time_range", "description"),
    [
        ([20, 10], [10, 20], ["2000-01-01", "2000-12-31"], "invalid_lat"),
        ([10, 20], [-190, 190], ["2000-01-01", "2000-12-31"], "invalid_long"),
        ([10, 20], [10, 20], ["2000-12-31", "2000-01-01"], "invalid_time"),
        ([], [10, 20], ["2000-01-01", "2000-12-31"], "empty_lat"),
        ([10, 20], [], ["2000-01-01", "2000-12-31"], "empty_long"),
    ],
)
def test_validate_bounds(lat_range, long_range, time_range, description):
    """Test that invalid bounds raise ValueError"""
    with pytest.raises(ValueError, match="Boundary:"):
        Boundary(lat_range, long_range, time_range)


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_bounds"),
    [
        (
            "arbitrary_boundary",
            [[30.0, 10.0], [30.0, 20.0], [40.0, 20.0], [40.0, 10.0], [30.0, 10.0]],
        ),
        (
            "meridian_boundary",
            [
                [-10.0, -50.0],
                [-10.0, -40.0],
                [10.0, -40.0],
                [10.0, -50.0],
                [-10.0, -50.0],
            ],
        ),
        (
            "antimeridian_boundary",
            [
                [170.0, -50.0],
                [170.0, -40.0],
                [-170.0, -40.0],
                [-170.0, -50.0],
                [170.0, -50.0],
            ],
        ),
        (
            "equatorial_boundary",
            [[30.0, -10.0], [30.0, 10.0], [40.0, 10.0], [40.0, -10.0], [30.0, -10.0]],
        ),
    ],
)
def test_get_bounds(boundary_fixture, expected_bounds, request):
    """Test getting boundary coordinates"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_bounds() == expected_bounds


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_cx"),
    [
        ("arbitrary_boundary", 35),
        ("meridian_boundary", 0),
        ("antimeridian_boundary", 180),
        ("equatorial_boundary", 35),
    ],
)
def test_getcx(boundary_fixture, expected_cx, request):
    """Test getting center x coordinate"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.getcx() == expected_cx


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_cy"),
    [
        ("arbitrary_boundary", 15),
        ("meridian_boundary", -45),
        ("antimeridian_boundary", -45),
        ("equatorial_boundary", 0),
    ],
)
def test_getcy(boundary_fixture, expected_cy, request):
    """Test getting center y coordinate"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.getcy() == expected_cy


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_height"),
    [
        ("arbitrary_boundary", 10),
        ("meridian_boundary", 10),
        ("antimeridian_boundary", 10),
        ("equatorial_boundary", 20),
    ],
)
def test_get_height(boundary_fixture, expected_height, request):
    """Test getting boundary height"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_height() == expected_height


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_width"),
    [
        ("arbitrary_boundary", 10),
        ("meridian_boundary", 20),
        ("antimeridian_boundary", 20),
        ("equatorial_boundary", 10),
    ],
)
def test_get_width(boundary_fixture, expected_width, request):
    """Test getting boundary width"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_width() == expected_width


def test_get_time_range(temporal_boundary):
    """Test getting time range"""
    assert temporal_boundary.get_time_range() == ["1970-01-01", "2021-12-31"]


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_dcx"),
    [
        ("arbitrary_boundary", 5),
        ("meridian_boundary", 10),
        ("antimeridian_boundary", 10),
        ("equatorial_boundary", 5),
    ],
)
def test_getdcx(boundary_fixture, expected_dcx, request):
    """Test getting half-width"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.getdcx() == expected_dcx


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_dcy"),
    [
        ("arbitrary_boundary", 5),
        ("meridian_boundary", 5),
        ("antimeridian_boundary", 5),
        ("equatorial_boundary", 10),
    ],
)
def test_getdcy(boundary_fixture, expected_dcy, request):
    """Test getting half-height"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.getdcy() == expected_dcy


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_min"),
    [
        ("arbitrary_boundary", 10),
        ("meridian_boundary", -50),
        ("antimeridian_boundary", -50),
        ("equatorial_boundary", -10),
    ],
)
def test_get_lat_min(boundary_fixture, expected_min, request):
    """Test getting minimum latitude"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_lat_min() == expected_min


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_max"),
    [
        ("arbitrary_boundary", 20),
        ("meridian_boundary", -40),
        ("antimeridian_boundary", -40),
        ("equatorial_boundary", 10),
    ],
)
def test_get_lat_max(boundary_fixture, expected_max, request):
    """Test getting maximum latitude"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_lat_max() == expected_max


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_min"),
    [
        ("arbitrary_boundary", 30),
        ("meridian_boundary", -10),
        ("antimeridian_boundary", 170),
        ("equatorial_boundary", 30),
    ],
)
def test_get_long_min(boundary_fixture, expected_min, request):
    """Test getting minimum longitude"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_long_min() == expected_min


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_max"),
    [
        ("arbitrary_boundary", 40),
        ("meridian_boundary", 10),
        ("antimeridian_boundary", -170),
        ("equatorial_boundary", 40),
    ],
)
def test_get_long_max(boundary_fixture, expected_max, request):
    """Test getting maximum longitude"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.get_long_max() == expected_max


def test_get_time_min(temporal_boundary):
    """Test getting minimum time"""
    assert temporal_boundary.get_time_min() == "1970-01-01"


def test_get_time_max(temporal_boundary):
    """Test getting maximum time"""
    assert temporal_boundary.get_time_max() == "2021-12-31"


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_size"),
    [
        ("arbitrary_boundary", 1092308.5466932291),
        ("meridian_boundary", 1354908.6430361348),
        ("antimeridian_boundary", 1354908.6430361343),
        ("equatorial_boundary", 1756355.5062820115),
    ],
)
def test_calc_size(boundary_fixture, expected_size, request):
    """Test calculating boundary size"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.calc_size() == pytest.approx(expected_size, rel=1e-5)


@pytest.mark.parametrize(
    ("boundary_fixture", "poly_wkt"),
    [
        ("arbitrary_boundary", "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
        ("meridian_boundary", "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
        (
            "antimeridian_boundary",
            "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))",
        ),
        ("equatorial_boundary", "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
    ],
)
def test_to_polygon(boundary_fixture, poly_wkt, request):
    """Test converting boundary to polygon"""
    boundary = request.getfixturevalue(boundary_fixture)
    expected_polygon = shapely.wkt.loads(poly_wkt)
    assert boundary.to_polygon() == expected_polygon


@pytest.mark.parametrize(
    ("boundary_fixture", "expected_poly_string"),
    [
        ("arbitrary_boundary", "POLYGON ((30 10, 30 20, 40 20, 40 10, 30 10))"),
        ("meridian_boundary", "POLYGON ((-10 -50, -10 -40, 10 -40, 10 -50, -10 -50))"),
        (
            "antimeridian_boundary",
            "MULTIPOLYGON (((170 -50, 170 -40, 180 -40, 180 -50, 170 -50)), ((-180 -50, -180 -40, -170 -40, -170 -50, -180 -50)))",
        ),
        ("equatorial_boundary", "POLYGON ((30 -10, 30 10, 40 10, 40 -10, 30 -10))"),
    ],
)
def test_to_poly_string(boundary_fixture, expected_poly_string, request):
    """Test converting boundary to polygon string"""
    boundary = request.getfixturevalue(boundary_fixture)
    assert boundary.to_poly_string() == expected_poly_string


def test_split_temporal(temporal_boundary):
    """Test splitting temporal boundary into four sub-boundaries"""
    expected_splits = [
        Boundary([10, 15], [30, 35], ["1970-01-01", "2021-12-31"]),
        Boundary([15, 20], [30, 35], ["1970-01-01", "2021-12-31"]),
        Boundary([10, 15], [35, 40], ["1970-01-01", "2021-12-31"]),
        Boundary([15, 20], [35, 40], ["1970-01-01", "2021-12-31"]),
    ]
    assert temporal_boundary.split() == expected_splits


def test_split_arbitrary(arbitrary_boundary):
    """Test splitting arbitrary boundary into four sub-boundaries"""
    expected_splits = [
        Boundary([10, 15], [30, 35]),
        Boundary([15, 20], [30, 35]),
        Boundary([10, 15], [35, 40]),
        Boundary([15, 20], [35, 40]),
    ]
    assert arbitrary_boundary.split() == expected_splits


def test_split_meridian(meridian_boundary):
    """Test splitting meridian boundary into four sub-boundaries"""
    expected_splits = [
        Boundary([-50, -45], [-10, 0]),
        Boundary([-45, -40], [-10, 0]),
        Boundary([-50, -45], [0, 10]),
        Boundary([-45, -40], [0, 10]),
    ]
    assert meridian_boundary.split() == expected_splits


def test_split_antimeridian(antimeridian_boundary):
    """Test splitting antimeridian boundary into four sub-boundaries"""
    expected_splits = [
        Boundary([-50, -45], [170, 180]),
        Boundary([-45, -40], [170, 180]),
        Boundary([-50, -45], [180, -170]),
        Boundary([-45, -40], [180, -170]),
    ]
    assert antimeridian_boundary.split() == expected_splits


def test_split_equatorial(equatorial_boundary):
    """Test splitting equatorial boundary into four sub-boundaries"""
    expected_splits = [
        Boundary([-10, 0], [30, 35]),
        Boundary([0, 10], [30, 35]),
        Boundary([-10, 0], [35, 40]),
        Boundary([0, 10], [35, 40]),
    ]
    assert equatorial_boundary.split() == expected_splits
