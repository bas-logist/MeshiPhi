"""
AggregatedCellBox class tests.
"""

import pytest
from meshiphi.mesh_generation.aggregated_cellbox import AggregatedCellBox
from meshiphi.mesh_generation.boundary import Boundary


def test_from_json():
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

    assert agg_cb_from_json == agg_cb_initialised_normally


@pytest.mark.parametrize(
    "attr,test_value,getter,setter",
    [
        ("boundary", Boundary([10, 20], [30, 40]), "get_bounds", "set_bounds"),
        ("id", "123", "get_id", "set_id"),
        ("agg_data", {"dummy_data": "456"}, "get_agg_data", "set_agg_data"),
    ],
)
def test_getter_setter_pairs(dummy_agg_cellbox, attr, test_value, getter, setter):
    """Test getter and setter method pairs"""
    # Test setter
    getattr(dummy_agg_cellbox, setter)(test_value)
    assert getattr(dummy_agg_cellbox, attr) == test_value

    # Test getter
    setattr(dummy_agg_cellbox, attr, test_value)
    assert getattr(dummy_agg_cellbox, getter)() == test_value


def test_to_json():
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
        "id": "1",
    }
    agg_cb_boundary = Boundary.from_poly_string(agg_cb_json["geometry"])

    data_keys = ["elevation", "SIC", "thickness", "density"]
    agg_cb_data = {k: agg_cb_json[k] for k in data_keys if k in agg_cb_json}
    agg_cb_id = agg_cb_json["id"]

    agg_cb = AggregatedCellBox(agg_cb_boundary, agg_cb_data, agg_cb_id)

    assert agg_cb.to_json() == agg_cb_json


@pytest.mark.parametrize(
    "cellbox_fixture,lat,lon,expected",
    [
        ("arbitrary_agg_cellbox", 50, 50, True),
        ("equatorial_agg_cellbox", 0, 50, True),
        ("meridian_agg_cellbox", 50, 0, True),
        ("antimeridian_agg_cellbox", 50, 179, True),
    ],
)
def test_contains_point(cellbox_fixture, lat, lon, expected, request):
    """Test point containment check"""
    cellbox = request.getfixturevalue(cellbox_fixture)
    assert cellbox.contains_point(lat, lon) == expected
