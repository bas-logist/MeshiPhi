import datetime
import json
import re
from typing import Any, Union

import jsonschema

from meshiphi.config_validation.mesh_schema import mesh_schema


def flexi_json_input(config: Union[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Allows flexible inputs. If a string is parsed, then assume it's a file path
    and read in as a json. If a dict is parsed, then assume it's already a
    valid loaded json, and return it as is

    Args:
        config (str or dict): Input to translate into a dict.

    Raises:
        TypeError: If input is neither a str nor a dict, then wrong input type

    Returns:
        dict: Dictionary read from JSON
    """
    if isinstance(config, str):
        # If str, assume filename
        with open(config) as fp:
            config_json: dict[str, Any] = json.load(fp)
    elif isinstance(config, dict):
        # If dict, assume it's the config
        config_json = config
    else:
        # Otherwise, can't deal with it
        raise TypeError(f"Expected 'str' or 'dict', instead got '{type(config)}'")

    return config_json


def validate_mesh_config(config: Union[str, dict[str, Any]]) -> None:
    """
    Validates a mesh config

    Args:
        config (str or dict):
            Mesh config to be validated.
            If type 'str', tries to read in as a filename and open file as json
            If type 'dict', assumes it's already read in from a json file

    Raises:
        TypeError: Incorrect config parsed in. Must be 'str' or 'dict'
        FileNotFoundError: Could not read in file if 'str' parsed
        ValidationError: Malformed mesh config
    """

    def assert_valid_time(time_str: str) -> None:
        """
        Checks if the time strings in the config are correctly formatted

        Args:
            time_str (str):
                String from config. Expects 'YYYY-MM-DD' or 'TODAY +- n'
        Raises:
            ValueError: String not in a valid date format
        """
        correctly_formatted = False
        # If relative time is parsed
        if re.match(r"TODAY[+,-]\d+", time_str.replace(" ", "")) or time_str == "TODAY":
            correctly_formatted = True
        # Otherwise check if date is parsed correctly
        else:
            try:
                # Checks if formatted as YYYY-MM-DD with a valid date
                datetime.date.fromisoformat(time_str)
                # If so, then it's correct
                correctly_formatted = True
            except ValueError:
                # Otherwise, keep correctly_formatted = False
                pass
        # If it failed to pass
        if not correctly_formatted:
            raise ValueError(f"{time_str} is not a valid date format!")

    def assert_valid_cellsize(bound_min: float, bound_max: float, cell_size: float) -> None:
        """
        Ensures that the initial cellbox size can evenly divide the initial
        boundary.

        Args:
            bound_min (float): Minimum value of boundary in one axis
            bound_max (float): Maximum value of boundary in the same axis
            cell_size (float): Initial cellbox size in the same axis
        """
        assert ((bound_max - bound_min) % 360 / cell_size) % 1 == 0, (
            f"{bound_max}-{bound_min}={bound_max - bound_min} is not evenly "
            + f"divided by {cell_size}"
        )

    # Deals with flexible input
    config_json = flexi_json_input(config)
    # Validate against the schema to check syntax is correct
    jsonschema.validate(instance=config_json, schema=mesh_schema)

    # Check that the dates in the region are valid
    assert_valid_time(config_json["region"]["start_time"])
    assert_valid_time(config_json["region"]["end_time"])

    # Check that cellbox width and height evenly divide boundary
    assert_valid_cellsize(
        config_json["region"]["lat_min"],
        config_json["region"]["lat_max"],
        config_json["region"]["cell_height"],
    )
    assert_valid_cellsize(
        config_json["region"]["long_min"],
        config_json["region"]["long_max"],
        config_json["region"]["cell_width"],
    )
