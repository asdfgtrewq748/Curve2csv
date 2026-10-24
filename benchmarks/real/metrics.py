"""Score one chart against published series.

A figure is correct when the predicted series count equals the ground-truth
count and every matched series has NRMSE ≤ 2% of the axis range and
x-coverage ≥ 0.90. Flagged or null points are removed first: they shrink
coverage and do not enter the error. Log axes are scored in log10 space.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment

from curve2csv.types import PointFlag, Series

NRMSE_MAX = 2.0
COVERAGE_MIN = 0.90
_UNMATCHED = 1.0e6


def valid_xy(series: Series) -> np.ndarray:
    """Unflagged finite points, shape (N, 2)."""

    rows: list[list[float]] = []
    for point in series.points:
        if point.flags != PointFlag.NONE or point.x is None or point.y is None:
            continue
        if not np.isfinite(point.x) or not np.isfinite(point.y):
            continue
        rows.append([float(point.x), float(point.y)])
    if not rows:
        return np.zeros((0, 2), dtype=np.float64)
    return np.asarray(rows, dtype=np.float64)


def _to_space(values: np.ndarray, scale: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if scale != "log10":
        return arr
    out = np.full(arr.shape, np.nan, dtype=np.float64)
    ok = arr > 0
    out[ok] = np.log10(arr[ok])
    return out


def pair_metrics(
    gt_xy: np.ndarray,
    pred_xy: np.ndarray,
    *,
    x_scale: str,
    y_scale: str,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    plot_w: float,
    n_samples: int = 200,
) -> tuple[float | None, float]:
    """Return ``(nrmse percent, x_coverage)`` for one series pair."""

    if gt_xy.shape[0] < 2 or plot_w <= 0:
        return None, 0.0
    gx = _to_space(gt_xy[:, 0], x_scale)
    gy = _to_space(gt_xy[:, 1], y_scale)
    order = np.argsort(gx)
    gx = gx[order]
    gy = gy[order]
    unique_x, unique_index = np.unique(gx, return_index=True)
    unique_y = gy[unique_index]
    if unique_x.size < 2:
        return None, 0.0
    rx = abs(
        _to_space(np.asarray(x_range), x_scale)[1] - _to_space(np.asarray(x_range), x_scale)[0]
    )
    ry = abs(
        _to_space(np.asarray(y_range), y_scale)[1] - _to_space(np.asarray(y_range), y_scale)[0]
    )
    if rx <= 0 or ry <= 0 or not np.isfinite(rx) or not np.isfinite(ry):
        return None, 0.0
    sampled_x = np.linspace(float(unique_x[0]), float(unique_x[-1]), n_samples)
    sampled_y = np.interp(sampled_x, unique_x, unique_y)
    if pred_xy.shape[0] == 0:
        return None, 0.0
    px = _to_space(pred_xy[:, 0], x_scale)
    py = _to_space(pred_xy[:, 1], y_scale)
    finite = np.isfinite(px) & np.isfinite(py)
    px = px[finite]
    py = py[finite]
    if px.size == 0:
        return None, 0.0
    order = np.argsort(px)
    px = px[order]
    py = py[order]
    index = np.clip(np.searchsorted(px, sampled_x, side="left"), 1, px.size - 1)
    left = index - 1
    take_right = np.abs(px[index] - sampled_x) < np.abs(px[left] - sampled_x)
    nearest = np.where(take_right, index, left)
    aligned = np.abs(px[nearest] - sampled_x) <= (rx / plot_w)
    coverage = np.zeros(sampled_x.shape, dtype=bool)
    if not np.any(aligned):
        return None, 0.0
    y_err = np.abs(py[nearest][aligned] - sampled_y[aligned])
    coverage[aligned] = y_err <= 0.02 * ry
    nrmse = float(np.sqrt(np.mean(np.square(y_err / ry)))) * 100.0
    return nrmse, float(coverage.mean())


def parameter_error(
    gt_xy: np.ndarray,
    pred_xy: np.ndarray,
    *,
    x_scale: str,
    y_scale: str,
    y_range: tuple[float, float],
) -> tuple[float, float] | None:
    """Slope relative error and intercept error as a fraction of the y range.

    Returned only when a straight line fits the ground truth with R² ≥ 0.98.
    """

    if gt_xy.shape[0] < 8 or pred_xy.shape[0] < 8:
        return None
    gx = _to_space(gt_xy[:, 0], x_scale)
    gy = _to_space(gt_xy[:, 1], y_scale)
    if float(np.max(gx) - np.min(gx)) <= 0:
        return None
    slope, intercept = np.polyfit(gx, gy, 1)
    fitted = slope * gx + intercept
    ss_res = float(np.sum(np.square(gy - fitted)))
    ss_tot = float(np.sum(np.square(gy - gy.mean())))
    if ss_tot <= 0 or 1.0 - ss_res / ss_tot < 0.98:
        return None
    px = _to_space(pred_xy[:, 0], x_scale)
    py = _to_space(pred_xy[:, 1], y_scale)
    inside = (
        (px >= float(np.min(gx))) & (px <= float(np.max(gx))) & np.isfinite(px) & np.isfinite(py)
    )
    if int(inside.sum()) < 8:
        return None
    pslope, pintercept = np.polyfit(px[inside], py[inside], 1)
    ry = abs(
        _to_space(np.asarray(y_range), y_scale)[1] - _to_space(np.asarray(y_range), y_scale)[0]
    )
    if ry <= 0:
        return None
    slope_rel = (
        abs(float(pslope - slope)) / abs(float(slope))
        if abs(float(slope)) > 1e-9
        else abs(float(pslope - slope))
    )
    intercept_range = abs(float(pintercept - intercept)) / ry
    return float(slope_rel), float(intercept_range)


def score_figure(
    gt_series: list[np.ndarray],
    pred_series: list[np.ndarray],
    *,
    x_scale: str,
    y_scale: str,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    plot_w: float,
) -> dict[str, Any]:
    """Match series and decide whether the figure meets the accuracy rule."""

    n_gt = len(gt_series)
    n_pred = len(pred_series)
    if n_gt == 0:
        return {
            "correct": False,
            "reason": "no_ground_truth",
            "n_gt": 0,
            "n_pred": n_pred,
            "worst_nrmse": None,
            "worst_coverage": None,
            "pairs": [],
            "slope_rel_err": None,
            "intercept_err_range": None,
        }
    if n_pred == 0:
        return {
            "correct": False,
            "reason": "no_series",
            "n_gt": n_gt,
            "n_pred": 0,
            "worst_nrmse": None,
            "worst_coverage": 0.0,
            "pairs": [],
            "slope_rel_err": None,
            "intercept_err_range": None,
        }
    cost = np.full((n_pred, n_gt), _UNMATCHED, dtype=np.float64)
    detail: list[list[tuple[float | None, float]]] = [
        [(None, 0.0) for _ in range(n_gt)] for _ in range(n_pred)
    ]
    for i, pred in enumerate(pred_series):
        for j, gt in enumerate(gt_series):
            nrmse, coverage = pair_metrics(
                gt,
                pred,
                x_scale=x_scale,
                y_scale=y_scale,
                x_range=x_range,
                y_range=y_range,
                plot_w=plot_w,
            )
            detail[i][j] = (nrmse, coverage)
            if nrmse is not None:
                cost[i, j] = nrmse
    rows, cols = linear_sum_assignment(cost)
    pairs: list[dict[str, Any]] = []
    worst_nrmse: float | None = None
    worst_coverage: float | None = None
    slope_errors: list[float] = []
    intercept_errors: list[float] = []
    for i, j in zip(rows, cols, strict=True):
        nrmse, coverage = detail[int(i)][int(j)]
        if cost[int(i), int(j)] >= _UNMATCHED:
            nrmse, coverage = None, 0.0
        pairs.append({"pred": int(i), "gt": int(j), "nrmse": nrmse, "x_coverage": coverage})
        if nrmse is not None and (worst_nrmse is None or nrmse > worst_nrmse):
            worst_nrmse = nrmse
        if worst_coverage is None or coverage < worst_coverage:
            worst_coverage = coverage
        if nrmse is not None:
            param = parameter_error(
                gt_series[int(j)],
                pred_series[int(i)],
                x_scale=x_scale,
                y_scale=y_scale,
                y_range=y_range,
            )
            if param is not None:
                slope_errors.append(param[0])
                intercept_errors.append(param[1])
    reason = "ok"
    if n_pred != n_gt:
        reason = "series_count"
    else:
        for pair in pairs:
            nrmse = pair["nrmse"]
            coverage = pair["x_coverage"]
            bad_n = nrmse is None or nrmse > NRMSE_MAX
            bad_c = coverage < COVERAGE_MIN
            if bad_n and bad_c:
                reason = "nrmse_and_coverage"
                break
            if bad_n:
                reason = "nrmse"
                break
            if bad_c:
                reason = "x_coverage"
                break
    return {
        "correct": reason == "ok",
        "reason": reason,
        "n_gt": n_gt,
        "n_pred": n_pred,
        "worst_nrmse": worst_nrmse,
        "worst_coverage": worst_coverage,
        "pairs": pairs,
        "slope_rel_err": max(slope_errors) if slope_errors else None,
        "intercept_err_range": max(intercept_errors) if intercept_errors else None,
    }
