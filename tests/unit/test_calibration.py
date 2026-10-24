"""Calibration fit, round-trip, and abstain behavior."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from curve2csv.calibrate.manual import calibrate_manual
from curve2csv.calibrate.model import fit_axis_1d
from curve2csv.config import PipelineConfig
from curve2csv.types import Abstain, AxesOverride, AxisScale, TickInput


def test_exact_line_residual_is_numerical_noise() -> None:
    px = np.array([10.0, 40.0, 70.0, 100.0])
    values = 0.25 * px - 3.0
    fitted = fit_axis_1d(px, values, axis="x", scale=AxisScale.LINEAR, source="test")
    assert isinstance(fitted, Abstain) is False
    assert fitted.residual_rel <= 1e-9
    recovered = fitted.px_to_data(px)
    assert np.max(np.abs(recovered - values)) <= 1e-9


def test_too_few_ticks_and_high_residual_abstain() -> None:
    one = fit_axis_1d(
        np.array([1.0]), np.array([2.0]), axis="x", scale=AxisScale.LINEAR, source="test"
    )
    assert isinstance(one, Abstain)
    assert one.reason == "too_few_ticks"
    px = np.array([0.0, 10.0, 20.0, 30.0])
    values = np.array([0.0, 0.0, 10.0, 10.0])
    noisy = fit_axis_1d(
        px,
        values,
        axis="x",
        scale=AxisScale.LINEAR,
        source="test",
        config=PipelineConfig(max_calib_residual=0.02),
    )
    assert isinstance(noisy, Abstain)
    assert noisy.reason == "residual_too_high"


def test_manual_abstains_without_two_ticks() -> None:
    axes = AxesOverride(x_ticks=(TickInput(px=1.0, py=2.0, value=0.0),), y_ticks=())
    calibration, plane = calibrate_manual(axes)
    assert plane is None
    assert isinstance(calibration["x"], Abstain)
    assert isinstance(calibration["y"], Abstain)


@settings(max_examples=30, deadline=None)
@given(
    slope=st.floats(min_value=0.05, max_value=4.0, allow_nan=False, allow_infinity=False),
    intercept=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    raw=st.lists(
        st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=6,
        unique=True,
    ),
)
def test_pixel_value_roundtrip(slope: float, intercept: float, raw: list[float]) -> None:
    px = np.asarray(sorted(raw), dtype=np.float64)
    if float(px[-1] - px[0]) < 1.0:
        pytest.skip("degenerate span")
    values = slope * px + intercept
    fitted = fit_axis_1d(px, values, axis="x", scale=AxisScale.LINEAR, source="hypothesis")
    assert not isinstance(fitted, Abstain)
    assert np.max(np.abs(fitted.px_to_data(px) - values)) <= 1e-6
    assert np.max(np.abs(fitted.data_to_px(values) - px)) <= 1e-6
