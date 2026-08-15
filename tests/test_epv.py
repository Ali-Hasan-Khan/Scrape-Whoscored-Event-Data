"""Tests for EPV helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from whoscored.epv import (
    add_epv_to_dataframe,
    get_epv_at_location,
    load_epv_grid,
    to_metric_coordinates_from_whoscored,
)


def test_load_epv_grid_shape():
    grid = load_epv_grid()
    assert grid.shape == (32, 50)
    assert np.isfinite(grid).all()


def test_get_epv_at_location_off_pitch():
    grid = load_epv_grid()
    assert get_epv_at_location((1000, 1000), grid, attack_direction=1) == 0.0


def test_get_epv_at_location_center_is_zeroish():
    grid = load_epv_grid()
    value = get_epv_at_location((0, 0), grid, attack_direction=1)
    assert 0.0 <= value <= 1.0


def test_get_epv_at_location_opposite_direction_mirrors():
    grid = load_epv_grid()
    fwd = get_epv_at_location((30, 0), grid, attack_direction=1)
    rev = get_epv_at_location((-30, 0), grid, attack_direction=-1)
    assert fwd == pytest.approx(rev)


def test_to_metric_coordinates(events_df):
    converted = to_metric_coordinates_from_whoscored(events_df)
    for col in ("x_metrica", "y_metrica", "endX_metrica", "endY_metrica"):
        assert col in converted.columns
    assert converted["x_metrica"].between(-53, 53).all()
    assert converted["y_metrica"].between(-34, 34).all()


def test_add_epv_to_dataframe(events_df):
    enriched = add_epv_to_dataframe(events_df)
    assert "EPV" in enriched.columns
    passes = enriched[(enriched["type"] == "Pass") & (enriched["outcomeType"] == "Successful")]
    assert passes["EPV"].notna().all()
    # only successful passes carry an EPV value
    expected_nan = len(enriched) - len(passes)
    assert enriched["EPV"].isna().sum() == expected_nan
    # metric columns are dropped again
    assert not any(c.endswith("_metrica") for c in enriched.columns)
