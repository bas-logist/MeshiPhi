"""
Miscellaneous utility functions that may be of use throughout MeshiPhi
"""

from __future__ import annotations

import logging
import time
import tracemalloc
from calendar import monthrange
from datetime import datetime, timedelta
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Generator, TypeVar, cast, overload

import numpy as np
import numpy.typing as npt

try:
    from scipy.fft import fftshift
except ImportError:
    from scipy.fftpack import fftshift

if TYPE_CHECKING:
    from meshiphi.mesh_generation.boundary import Boundary

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@overload
def longitude_domain(long: float) -> float: ...


@overload
def longitude_domain(long: list[float]) -> list[float]: ...


@overload
def longitude_domain(long: npt.NDArray[np.floating[Any]]) -> npt.NDArray[np.floating[Any]]: ...


def longitude_domain(
    long: float | list[float] | npt.NDArray[np.floating[Any]],
) -> float | list[float] | npt.NDArray[np.floating[Any]]:
    """
    Converts any longitude degree value into one between -180:180
    """
    # Allow input type to be list or ndarray
    if isinstance(long, list):
        return [longitude_domain(x) for x in long]
    if isinstance(long, np.ndarray):
        return np.array([longitude_domain(x) for x in long])
    # Return same format as input at antimeridian
    if long in [-180, 180]:
        return long
    # Otherwise convert it to be within domain
    return (long + 180) % 360 - 180


def longitude_distance(long_a: float, long_b: float) -> float:
    """
    Calculates the angular distance between two longitude values
    """

    long_dist = float(np.abs(longitude_domain(long_b) - longitude_domain(long_a)))
    long_dist = float(np.mod(long_dist, 360))

    if long_dist > 180:
        return 360 - long_dist
    return long_dist


def frac_of_month(
    year: int, month: int, start_date: datetime | None = None, end_date: datetime | None = None
) -> float:
    # Determine the number of days in the month specified
    days_in_month = monthrange(year, month)[1]
    # If not specified, default to beginning/end of month
    if start_date is None:
        start_date = str_to_datetime(f"{year}-{month}-01")
    if end_date is None:
        end_date = str_to_datetime(f"{year}-{month}-{days_in_month}")

    # Ensure that input to fn was valid
    assert start_date.month == month, "Start date not in same month!"
    assert end_date.month == month, "End date not in same month!"
    # Determine overlap from dates (inclusive)
    days_overlap = (end_date - start_date).days + 1
    # Return fraction
    return days_overlap / days_in_month


def boundary_to_coords(bounds: Boundary) -> tuple[tuple[float, float], tuple[float, float]]:
    min_coords = (bounds.get_lat_min(), bounds.get_long_min())
    max_coords = (bounds.get_lat_max(), bounds.get_long_max())
    return min_coords, max_coords


def str_to_datetime(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def date_range(start_date: datetime, end_date: datetime) -> Generator[datetime, None, None]:
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def convert_decimal_days(decimal_days: float, mins: bool = False) -> str:
    """
    Convert decimal days to more readable Days, Hours and (optionally) Minutes
    Args:
        decimal_days (float): Number of days as a decimal
        mins (bool): Determines whether to return minutes or decimal hours
    Returns:
        new_time (str): The time in the new format
    """
    frac_d, days = np.modf(decimal_days)
    hours = frac_d * 24.0

    if mins:
        frac_h, hours = np.modf(hours)
        minutes = round(frac_h * 60.0)
        if days:
            new_time = f"{round(days)} days {round(hours)} hours {minutes} minutes"
        elif hours:
            new_time = f"{round(hours)} hours {minutes} minutes"
        else:
            new_time = f"{minutes} minutes"
    else:
        hours = round(hours, 2)
        new_time = f"{round(days)} days {hours} hours" if days else f"{hours} hours"

    return new_time


@overload
def round_to_sigfig(x: int, sigfig: int = 5) -> int: ...


@overload
def round_to_sigfig(x: float, sigfig: int = 5) -> float: ...


@overload
def round_to_sigfig(x: list[float], sigfig: int = 5) -> list[float]: ...


@overload
def round_to_sigfig(
    x: npt.NDArray[np.floating[Any]], sigfig: int = 5
) -> npt.NDArray[np.floating[Any]]: ...


def round_to_sigfig(
    x: int | float | list[float] | npt.NDArray[np.floating[Any]], sigfig: int = 5
) -> int | float | list[float] | npt.NDArray[np.floating[Any]]:
    """
    Rounds numbers to some number of significant figures

    Args:
        x (float or np.array): Value(s) to round to sig figs
        sigfig (int): Number of significant figures desired

    Returns:
        np.array:
            Values rounded to the desired number of significant figures
    """
    # Save original type of data so can be returned as input
    orig_type = type(x)
    if orig_type not in [list, float, int, np.ndarray, np.float64]:
        raise ValueError(f"Cannot round {type(x)} to sig figs!")

    # Convert to 1-d array - np.atleast_1d handles scalars, lists, and arrays uniformly
    # For scalars, creates shape (1,); for lists/arrays, ensures at least 1-d
    # Convert to float for calculations (log10 requires float), but preserve original type info
    x_array = np.atleast_1d(np.asarray(x, dtype=np.float64))
    # Create a mask disabling any values of inf or zero being passed to log10
    loggable_idxs = ([x_array != 0] & np.isfinite(x_array))[0]
    # Determine number of decimal places to round each number to
    # np.abs because can't find log of negative number
    # np.log10 to get position of most significant digit
    #   where x is finite and non-zero, avoiding overflow from log10
    #   out = 0, setting default value where x=0 or inf
    # np.floor to round to position of most significant digit
    # np.array.astype(int) to enable np.around to work later
    dec_pl = (
        sigfig
        - np.floor(
            np.log10(np.abs(x_array), where=loggable_idxs, out=np.zeros_like(x_array))
        ).astype(int)
        - 1
    )
    # Round to sig figs
    rounded = np.array([np.around(x_array[i], decimals=dec_pl[i]) for i in range(len(x_array))])
    # Return as single value if input that way
    if orig_type in [int, float, np.float64]:
        result = rounded.item()
        # Convert back to int if original was int (to preserve type)
        if orig_type is int:
            return cast("int | float", int(result))
        return cast("int | float", result)
    # Return as python list
    if orig_type is list:
        return cast("list[float]", rounded.tolist())
    # Otherwise, return np.array
    return cast("npt.NDArray[np.floating[Any]]", rounded)


def divergence(flow: npt.NDArray[np.floating[Any]]) -> npt.NDArray[np.floating[Any]]:
    flow = np.swapaxes(flow, 0, 1)
    Fx, Fy = flow[:, :, 0], flow[:, :, 1]
    dFx_dx = np.gradient(Fx, axis=0)
    dFy_dy = np.gradient(Fy, axis=1)
    return cast("npt.NDArray[np.floating[Any]]", dFx_dx + dFy_dy)


def curl(flow: npt.NDArray[np.floating[Any]]) -> npt.NDArray[np.floating[Any]]:
    flow = np.swapaxes(flow, 0, 1)
    Fx, Fy = flow[:, :, 0], flow[:, :, 1]
    dFx_dy = np.gradient(Fx, axis=1)
    dFy_dx = np.gradient(Fy, axis=0)
    return cast("npt.NDArray[np.floating[Any]]", dFy_dx - dFx_dy)


# GRF functions
def fftind(size: int) -> npt.NDArray[np.int_]:
    """
    Creates a numpy array of shifted Fourier coordinates.

    Args:
        size (int):
            The size of the coordinate array to create

    Returns:
        np.array:
            Numpy array of shifted Fourier coordinates (k_x, k_y).
            Has shape (2, size, size), with:\n
            array[0,:,:] = k_x components\n
            array[1,:,:] = k_y components
    """
    # Create array
    k_ind = np.mgrid[:size, :size] - int((size + 1) / 2)
    # Fourier shift
    return cast("npt.NDArray[np.int_]", fftshift(k_ind))


def gaussian_random_field(size: int, alpha: float) -> npt.NDArray[np.floating[Any]]:
    """
    Creates a gaussian random field with normal (circular) distribution
    Code from https://github.com/bsciolla/gaussian-random-fields/blob/master/gaussian_random_fields.py

    Args:
        size (int):
           Default = 512;
           The number of datapoints created per axis in the GRF
        alpha (float):
            Default = 3.0;
            The power of the power-law momentum distribution

    Returns:
        np.array:
            2D Array of datapoints, shape (size, size)
    """

    # Defines momentum indices
    k_idx = fftind(size)

    # Defines the amplitude as a power law 1/|k|^(alpha/2)
    amplitude = np.power(k_idx[0] ** 2 + k_idx[1] ** 2 + 1e-10, -alpha / 4.0)
    amplitude[0, 0] = 0

    # Draws a complex gaussian random noise with normal
    # (circular) distribution
    noise = np.random.normal(size=(size, size)) + 1j * np.random.normal(size=(size, size))

    # To real space
    grf = np.fft.ifft2(noise * amplitude).real

    # Normalise the GRF:
    grf = grf - np.min(grf)
    return grf / (np.max(grf) - np.min(grf))


def memory_trace(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracemalloc.start(20)
        res = func(*args, **kwargs)
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("traceback")

        stat = top_stats[0]
        logging.info(f"{stat.count} memory blocks: {stat.size / 1024:.1f} KiB")
        logging.info("\n".join(stat.traceback.format()))
        return res

    return wrapper  # type: ignore[return-value]


def timed_call(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        res = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f"Timed call to {func.__name__} took {end - start:02f} seconds")
        return res

    return wrapper  # type: ignore[return-value]


# CLI utilities
def setup_logging(
    func: F, log_format: str = "[%(asctime)-17s :%(levelname)-8s] - %(message)s"
) -> F:
    """Wraps a CLI endpoint and sets up logging for it

    This is probably not the smoothest implementation, but it's an educational
    one for people who aren't aware of decorators and how they're implemented.
    In addition, it supports a nice pattern for CLI endpoints

    TODO: start handling level configuration from logging yaml config

    :param func:
    :param log_format:
    :return:
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        parsed_args = func(*args, **kwargs)
        level = logging.INFO

        if hasattr(parsed_args, "verbose") and parsed_args.verbose:
            level = logging.DEBUG

        logging.basicConfig(
            level=level,
            format=log_format,
            datefmt="%d-%m-%y %T",
        )

        logging.getLogger("cdsapi").setLevel(logging.WARNING)
        logging.getLogger("matplotlib").setLevel(logging.WARNING)
        logging.getLogger("matplotlib.pyplot").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("tensorflow").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        return parsed_args

    return wrapper  # type: ignore[return-value]
