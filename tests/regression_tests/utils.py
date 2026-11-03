"""
Utility functions for regression testing.

This module contains helper functions for extracting and comparing mesh components.
"""

from meshiphi.utils import round_to_sigfig
from tests.conftest import SIG_FIG_TOLERANCE


def round_dataframe_values(df):
    """
    Helper function to round float and list-of-float values in a dataframe.

    Args:
        df (DataFrame): Pandas dataframe to round values in

    Returns:
        DataFrame: Modified dataframe with rounded values
    """
    # Round float columns to sig figs
    float_cols = df.select_dtypes(include=float).columns
    for col in float_cols:
        df[col] = round_to_sigfig(df[col].to_numpy(), sigfig=SIG_FIG_TOLERANCE)

    # Round list columns that contain floats
    list_cols = df.select_dtypes(include=list).columns
    for col in list_cols:
        round_col = []
        for val in df[col]:
            if isinstance(val, list) and all(isinstance(x, float) for x in val):
                round_col.append(round_to_sigfig(val, sigfig=SIG_FIG_TOLERANCE))
            else:
                round_col.append(val)
        df[col] = round_col

    return df


def extract_common_boundaries_for_comparison(mesh_a, mesh_b):
    """
    Creates a list of common geometry boundaries between two mesh JSONs.

    Args:
        mesh_a (dict): First mesh JSON to extract boundaries from
        mesh_b (dict): Second mesh JSON to extract boundaries from

    Returns:
        list: List of common cellbox geometries (as strings)
    """
    bounds_a = [cb["geometry"] for cb in mesh_a["cellboxes"]]
    bounds_b = [cb["geometry"] for cb in mesh_b["cellboxes"]]

    return [geom for geom in bounds_a if geom in bounds_b]
