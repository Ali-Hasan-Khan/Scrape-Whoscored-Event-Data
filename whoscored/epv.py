"""Expected Possession Value (EPV) helpers.

The model and pre-generated grid are taken from Laurie Shaw's
`Expected Possession Value <http://eightyfivepoints.blogspot.com/>`_ work,
which was originally bundled with this project.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

_BUNDLED_GRID = os.path.join(os.path.dirname(__file__), "data", "EPV_grid.csv")
_LEGACY_GRID = os.path.join(os.path.dirname(__file__), "..", "EPV_grid.csv")


def load_epv_grid(fname: str | None = None) -> np.ndarray:
    """Load the pre-generated EPV surface from a CSV file.

    Parameters
    ----------
    fname : str, optional
        Path to the grid file. Defaults to the ``EPV_grid.csv`` bundled with
        the package.

    Returns
    -------
    numpy.ndarray
        The (32, 50) EPV surface.
    """
    if fname is None:
        path = _BUNDLED_GRID if os.path.exists(_BUNDLED_GRID) else _LEGACY_GRID
    else:
        path = fname
    return np.loadtxt(path, delimiter=",")


def get_epv_at_location(
    position: tuple[float, float],
    epv: np.ndarray,
    attack_direction: int = 1,
    field_dimen: tuple[float, float] = (106.0, 68.0),
) -> float:
    """Return the EPV value at a given (x, y) pitch location.

    Parameters
    ----------
    position : tuple[float, float]
        The (x, y) pitch position in metric coordinates (origin at the
        centre circle).
    epv : numpy.ndarray
        The EPV surface (see :func:`load_epv_grid`).
    attack_direction : int, default 1
        Attack direction: ``1`` for left -> right, ``-1`` for right -> left.
    field_dimen : tuple[float, float], default (106, 68)
        Length and width of the pitch in metres.

    Returns
    -------
    float
        EPV value at the position (``0.0`` when off the pitch).
    """
    x, y = position
    if abs(x) > field_dimen[0] / 2.0 or abs(y) > field_dimen[1] / 2.0:
        return 0.0
    grid = np.fliplr(epv) if attack_direction == -1 else epv
    ny, nx = grid.shape
    dx = field_dimen[0] / float(nx)
    dy = field_dimen[1] / float(ny)
    ix = int((x + field_dimen[0] / 2.0 - 0.0001) / dx)
    iy = int((y + field_dimen[1] / 2.0 - 0.0001) / dy)
    ix = min(max(ix, 0), nx - 1)
    iy = min(max(iy, 0), ny - 1)
    return float(grid[iy, ix])


def to_metric_coordinates_from_whoscored(
    data: pd.DataFrame,
    field_dimen: tuple[float, float] = (106.0, 68.0),
) -> pd.DataFrame:
    """Convert Whoscored percentage coordinates to metres (origin at centre).

    Whoscored reports positions as percentages of the pitch (``x``/``y`` and
    ``endX``/``endY`` columns). This converts them to metric coordinates
    centred on the middle of the pitch.

    Parameters
    ----------
    data : pandas.DataFrame
        Events DataFrame containing ``x``, ``y`` (and ``endX``, ``endY``).
    field_dimen : tuple[float, float], default (106, 68)
        Pitch length/width in metres.

    Returns
    -------
    pandas.DataFrame
        A copy with ``*_metrica`` columns added.
    """
    data = data.copy()
    x_columns = [c for c in data.columns if c[-1].lower() == "x"][:2]
    y_columns = [c for c in data.columns if c[-1].lower() == "y"][:2]
    for col in x_columns:
        data[col + "_metrica"] = (data[col] / 100 * field_dimen[0]) - field_dimen[0] / 2
    for col in y_columns:
        data[col + "_metrica"] = (data[col] / 100 * field_dimen[1]) - field_dimen[1] / 2
    return data


def add_epv_to_dataframe(
    data: pd.DataFrame,
    epv: np.ndarray | None = None,
    grid_fname: str | None = None,
) -> pd.DataFrame:
    """Add an ``EPV`` column (difference between end/start EPV) to a DataFrame.

    Only successful passes receive an EPV value; all other rows are ``NaN``.

    Parameters
    ----------
    data : pandas.DataFrame
        Events DataFrame with ``x``/``y`` and ``endX``/``endY`` columns.
    epv : numpy.ndarray, optional
        Pre-loaded EPV grid. Loaded from disk when not provided.
    grid_fname : str, optional
        Override the bundled grid file (see :func:`load_epv_grid`).

    Returns
    -------
    pandas.DataFrame
        The input with an ``EPV`` column appended.
    """
    grid = epv if epv is not None else load_epv_grid(grid_fname)
    data = to_metric_coordinates_from_whoscored(data)

    is_pass = (data["type"] == "Pass") & (data["outcomeType"] == "Successful")
    differences: list[Any] = []

    xs = data["x_metrica"]
    ys = data["y_metrica"]
    exs = data["endX_metrica"]
    eys = data["endY_metrica"]
    for i in data.index:
        if is_pass.loc[i]:
            start = get_epv_at_location((xs.loc[i], ys.loc[i]), grid, attack_direction=1)
            end = get_epv_at_location((exs.loc[i], eys.loc[i]), grid, attack_direction=1)
            differences.append(end - start)
        else:
            differences.append(np.nan)

    data["EPV"] = differences
    return data.drop(
        columns=["x_metrica", "endX_metrica", "y_metrica", "endY_metrica"],
        errors="ignore",
    )
