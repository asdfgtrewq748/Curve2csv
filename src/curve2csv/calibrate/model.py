"""Axis geometry: 1D fits and a 2D pixel ↔ data map built from those fits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from curve2csv.config import PipelineConfig
from curve2csv.types import Abstain, AxisCalibration, AxisScale


def fit_axis_1d(
    px: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    axis: str,
    scale: AxisScale,
    source: str,
    config: PipelineConfig | None = None,
    dir_x: float = 1.0,
    dir_y: float = 0.0,
) -> AxisCalibration | Abstain:
    """Least-squares fit ``target = a * px + b`` (``target`` is value or log10(value))."""

    cfg = config or PipelineConfig()
    px_arr = np.asarray(px, dtype=np.float64).reshape(-1)
    val_arr = np.asarray(values, dtype=np.float64).reshape(-1)
    if px_arr.size < 2 or val_arr.size != px_arr.size:
        return Abstain("calibrate", "too_few_ticks")
    if scale is AxisScale.LOG10:
        if np.any(val_arr <= 0):
            return Abstain("calibrate", "nonpositive_log")
        target = np.log10(val_arr)
    else:
        target = val_arr
    span = float(np.max(target) - np.min(target))
    if span <= 0.0 or not np.isfinite(span):
        return Abstain("calibrate", "zero_span")
    design = np.column_stack([px_arr, np.ones(px_arr.size)])
    coef, _, _, _ = np.linalg.lstsq(design, target, rcond=None)
    a = float(coef[0])
    b = float(coef[1])
    if not np.isfinite(a) or not np.isfinite(b) or abs(a) < 1e-15:
        return Abstain("calibrate", "degenerate_axis")
    predicted = a * px_arr + b
    residual_rel = float(np.max(np.abs(predicted - target)) / span)
    if residual_rel > cfg.max_calib_residual:
        return Abstain("calibrate", "residual_too_high")
    # x increases to the right; y parameter increases downward. A negative y slope
    # is the conventional (upward) orientation and is not flagged as inverted.
    if axis == "y":
        inverted = a > 0.0
    else:
        inverted = a < 0.0
    norm = float(np.hypot(dir_x, dir_y))
    if norm == 0.0:
        dir_x, dir_y, norm = 1.0, 0.0, 1.0
    return AxisCalibration(
        axis=axis,
        scale=scale,
        a=a,
        b=b,
        inverted=inverted,
        residual_rel=residual_rel,
        n_ticks_used=int(px_arr.size),
        source=source,
        dir_x=float(dir_x / norm),
        dir_y=float(dir_y / norm),
    )


@dataclass(frozen=True)
class PlaneMap:
    """Pixel ↔ data map. Parameters are projections onto the axis directions.

    ``t = col * x_dir_x + row * x_dir_y`` and likewise for ``u``. For an upright
    chart the directions are ``(1, 0)`` and ``(0, 1)``, so ``t`` is the column
    and ``u`` is the row.
    """

    x: AxisCalibration
    y: AxisCalibration

    def pixel_to_data(self, col: float, row: float) -> tuple[float, float]:
        t = col * self.x.dir_x + row * self.x.dir_y
        u = col * self.y.dir_x + row * self.y.dir_y
        dx = float(self.x.px_to_data(np.asarray([t], dtype=np.float64))[0])
        dy = float(self.y.px_to_data(np.asarray([u], dtype=np.float64))[0])
        return dx, dy

    def data_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        t = float(self.x.data_to_px(np.asarray([x], dtype=np.float64))[0])
        u = float(self.y.data_to_px(np.asarray([y], dtype=np.float64))[0])
        matrix = np.array(
            [[self.x.dir_x, self.x.dir_y], [self.y.dir_x, self.y.dir_y]],
            dtype=np.float64,
        )
        try:
            col, row = np.linalg.solve(matrix, np.array([t, u], dtype=np.float64))
        except np.linalg.LinAlgError:
            return float("nan"), float("nan")
        return float(col), float(row)

    @property
    def residual_rel(self) -> float:
        return max(self.x.residual_rel, self.y.residual_rel)

    def is_axis_aligned(self, tol_deg: float = 0.2) -> bool:
        def _ang(dx: float, dy: float) -> float:
            return abs(float(np.degrees(np.arctan2(dy, dx)))) % 180.0

        ax = min(_ang(self.x.dir_x, self.x.dir_y), 180.0 - _ang(self.x.dir_x, self.x.dir_y))
        ay = abs(_ang(self.y.dir_x, self.y.dir_y) - 90.0)
        return ax <= tol_deg and ay <= tol_deg
