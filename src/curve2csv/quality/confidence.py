"""Series- and image-level confidence. Point confidence is assigned during extraction."""

from __future__ import annotations

from curve2csv.types import AxisCalibration, PlotArea, Series


def score_series(series: list[Series], plot_score: float, calib_residual: float) -> float:
    if not series:
        return 0.0
    series_score = float(sum(item.confidence for item in series) / len(series))
    calib_factor = max(0.0, 1.0 - calib_residual / 0.02)
    return float(
        max(0.0, min(1.0, series_score * (0.5 + 0.5 * plot_score) * (0.7 + 0.3 * calib_factor)))
    )


def calibration_residual(calibration: dict[str, object]) -> float:
    residuals: list[float] = []
    for value in calibration.values():
        if isinstance(value, AxisCalibration):
            residuals.append(value.residual_rel)
    return max(residuals) if residuals else 1.0


def plot_score_of(area: PlotArea | object) -> float:
    if isinstance(area, PlotArea):
        return float(area.score)
    return 0.0
