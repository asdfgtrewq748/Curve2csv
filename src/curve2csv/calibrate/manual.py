"""Calibration from sidecar or user-supplied ``(pixel, value)`` tick pairs."""

from __future__ import annotations

import numpy as np

from curve2csv.calibrate.model import PlaneMap, fit_axis_1d
from curve2csv.config import PipelineConfig
from curve2csv.types import Abstain, AxesOverride, AxisCalibration, AxisScale, TickInput


def _as_points(ticks: tuple[TickInput, ...], *, vertical: bool) -> np.ndarray | None:
    if len(ticks) < 2:
        return None
    rows: list[list[float]] = []
    for tick in ticks:
        if tick.py is None:
            if vertical:
                rows.append([0.0, tick.px, tick.value])
            else:
                rows.append([tick.px, 0.0, tick.value])
        else:
            rows.append([tick.px, tick.py, tick.value])
    return np.asarray(rows, dtype=np.float64)


def _axis_direction(points: np.ndarray, *, vertical: bool) -> tuple[float, float] | None:
    coords = points[:, :2]
    if coords.shape[0] < 2:
        return None
    centered = coords - coords.mean(axis=0)
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    direction = vh[0]
    if vertical:
        if direction[1] < 0.0:
            direction = -direction
    elif direction[0] < 0.0:
        direction = -direction
    norm = float(np.hypot(direction[0], direction[1]))
    if norm < 1e-9:
        return None
    return float(direction[0] / norm), float(direction[1] / norm)


def _parameter(points: np.ndarray, direction: tuple[float, float]) -> np.ndarray:
    return points[:, 0] * direction[0] + points[:, 1] * direction[1]


def calibrate_manual(
    axes: AxesOverride,
    config: PipelineConfig | None = None,
) -> tuple[dict[str, AxisCalibration | Abstain], PlaneMap | None]:
    """Fit x and y from tick pairs. A bad axis is an :class:`Abstain`, not an exception."""

    cfg = config or PipelineConfig()
    result: dict[str, AxisCalibration | Abstain] = {}
    fitted: dict[str, AxisCalibration] = {}
    for name, ticks, scale, vertical in (
        ("x", axes.x_ticks, axes.x_scale, False),
        ("y", axes.y_ticks, axes.y_scale, True),
    ):
        pts = _as_points(ticks, vertical=vertical)
        if pts is None:
            result[name] = Abstain("calibrate", "too_few_ticks")
            continue
        direction = _axis_direction(pts, vertical=vertical)
        if direction is None:
            result[name] = Abstain("calibrate", "degenerate_axis")
            continue
        # When the caller only passed a 1D coordinate, force the conventional direction
        # so the parameter equals that coordinate.
        if all(tick.py is None for tick in ticks):
            direction = (0.0, 1.0) if vertical else (1.0, 0.0)
        parameter = _parameter(pts, direction)
        fitted_axis = fit_axis_1d(
            parameter,
            pts[:, 2],
            axis=name,
            scale=scale if isinstance(scale, AxisScale) else AxisScale(scale),
            source=axes.source,
            config=cfg,
            dir_x=direction[0],
            dir_y=direction[1],
        )
        result[name] = fitted_axis
        if isinstance(fitted_axis, AxisCalibration):
            fitted[name] = fitted_axis
    plane = PlaneMap(x=fitted["x"], y=fitted["y"]) if "x" in fitted and "y" in fitted else None
    return result, plane
