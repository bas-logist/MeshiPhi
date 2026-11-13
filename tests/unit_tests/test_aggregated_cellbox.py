"""
AggregatedCellBox class tests.
"""

import numpy as np
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


def test_from_json_restores_nan_for_null_values():
    """Null values produced by JSON serialization should be restored as NaN."""
    agg_cb_json = {
        "geometry": "POLYGON ((-175 49, -175 51.5, -170 51.5, -170 49, -175 49))",
        "cx": -172.5,
        "cy": 50.25,
        "dcx": 2.5,
        "dcy": 1.25,
        "uC": None,
        "vC": None,
        "id": "1",
    }

    agg_cb = AggregatedCellBox.from_json(agg_cb_json)

    assert np.isnan(agg_cb.agg_data["uC"])
    assert np.isnan(agg_cb.agg_data["vC"])


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

def test_aggregated_cellbox_serialises_generic_nan_fields_to_none():
    boundary = Boundary([0.0, 1.0], [0.0, 1.0])
    cell = AggregatedCellBox(boundary, {"some_other_field": np.nan, "other_value": 2.5}, "cell-1")

    serialized = cell.to_json()

    assert serialized["some_other_field"] is None
    assert serialized["other_value"] == 2.5

def test_aggregated_cellbox_serialises_speed_limit_fields_to_none_when_undefined():
    boundary = Boundary([0.0, 1.0], [0.0, 1.0])
    cell = AggregatedCellBox(
        boundary,
        {"protected_area_speed_limit": np.nan, "speed_limit": 7.5},
        "cell-2",
    )

    serialized = cell.to_json()

    assert serialized["protected_area_speed_limit"] is None
    assert serialized["speed_limit"] == 7.5
