"""Tests for trajectory metric functions."""

import numpy as np
import pytest

from metrics import end_variance, jerk, rmse


def test_rmse_zero_on_constant():
    actions = np.ones((100, 7))
    assert rmse(actions) == pytest.approx(0.0)


def test_jerk_zero_on_linear():
    # Linear ramp -> constant 1st diff -> zero 2nd diff -> zero 3rd diff.
    actions = np.linspace(0, 1, 100).reshape(-1, 1) * np.ones((1, 7))
    assert jerk(actions) == pytest.approx(0.0, abs=1e-9)


def test_end_variance_zero_on_constant():
    actions = np.ones((100, 7))
    assert end_variance(actions) == pytest.approx(0.0)
