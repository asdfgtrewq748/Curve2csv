"""Benchmark metrics from BENCHMARK.md §5.

Missing predictions are coverage failures. They are not filled in, and they are
not counted as point error. ``fabrication_count`` counts only unflagged,
high-confidence points that land in a ground-truth gap or outside the plot.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree

from curve2csv.types import Abstain, ExtractionResult, PlotArea, PointFlag

UNMATCHED = 100.0


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    union = max(0, ax1 - ax0) * max(0, ay1 - ay0) + max(0, bx1 - bx0) * max(0, by1 - by0) - inter
    return float(inter / union) if union else 0.0


def _affine_from_probes(probes: list[dict[str, float]]) -> tuple[np.ndarray, np.ndarray] | None:
    if len(probes) < 4:
        return None
    design = np.array([[p["px"], p["py"], 1.0] for p in probes], dtype=np.float64)
    target_x = np.array([p["x"] for p in probes], dtype=np.float64)
    target_y = np.array([p["y"] for p in probes], dtype=np.float64)
    coef_x, _, _, _ = np.linalg.lstsq(design, target_x, rcond=None)
    coef_y, _, _, _ = np.linalg.lstsq(design, target_y, rcond=None)
    return coef_x, coef_y


def axis_calib_rel_err(gt: dict[str, Any], result: ExtractionResult) -> float:
    """Max relative error of an 11×11 grid against the probe affine map."""

    probes = gt.get("probes") or []
    fit = _affine_from_probes(probes)
    area = result.plot_area
    mapper = result.mapper
    if fit is None or mapper is None or isinstance(area, Abstain):
        return 1.0
    coef_x, coef_y = fit
    x0, y0, x1, y1 = area.bbox
    if x1 <= x0 or y1 <= y0:
        return 1.0
    cols = np.linspace(x0 + 0.5, x1 - 0.5, 11)
    rows = np.linspace(y0 + 0.5, y1 - 0.5, 11)
    rx = float(gt.get("R_x") or 0.0)
    ry = float(gt.get("R_y") or 0.0)
    if rx <= 0 or ry <= 0:
        return 1.0
    worst = 0.0
    for row in rows:
        for col in cols:
            pred = mapper.pixel_to_data(float(col), float(row))
            if pred is None:
                return 1.0
            gx = float(coef_x[0] * col + coef_x[1] * row + coef_x[2])
            gy = float(coef_y[0] * col + coef_y[1] * row + coef_y[2])
            worst = max(worst, abs(pred[0] - gx) / rx, abs(pred[1] - gy) / ry)
    return float(worst)


def _sample_visible_x(
    gt_series: dict[str, Any], n: int = 200
) -> tuple[np.ndarray, np.ndarray] | None:
    ranges = gt_series.get("visible_ranges") or []
    xs = np.asarray(gt_series.get("x") or [], dtype=np.float64)
    ys = np.asarray(gt_series.get("y") or [], dtype=np.float64)
    visible = np.asarray(gt_series.get("visible") or [], dtype=np.int8)
    if xs.size < 2 or ys.size != xs.size or not ranges:
        return None
    if visible.size == xs.size:
        keep = visible.astype(bool)
        xs, ys = xs[keep], ys[keep]
    if xs.size < 2:
        return None
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    # Drop duplicate x so interpolation is defined.
    unique_x, unique_idx = np.unique(xs, return_index=True)
    unique_y = ys[unique_idx]
    if unique_x.size < 2:
        return None
    span = sum(float(hi) - float(lo) for lo, hi in ranges)
    if span <= 0:
        return None
    chunks: list[np.ndarray] = []
    for lo, hi in ranges:
        width = float(hi) - float(lo)
        if width <= 0:
            continue
        count = max(1, int(round(n * width / span)))
        chunks.append(np.linspace(float(lo), float(hi), count, endpoint=False))
    if not chunks:
        return None
    sampled_x = np.concatenate(chunks)
    sampled_y = np.interp(sampled_x, unique_x, unique_y)
    return sampled_x, sampled_y


def curve_pair_metrics(
    gt_series: dict[str, Any],
    pred_xy: np.ndarray,
    *,
    rx: float,
    ry: float,
    plot_w: float,
) -> tuple[float | None, float]:
    """Return ``(nrmse percent, x_coverage)``. NRMSE is None when nothing aligns."""

    sampled = _sample_visible_x(gt_series)
    if sampled is None or ry <= 0 or pred_xy.size == 0:
        return None, 0.0
    sampled_x, sampled_y = sampled
    order = np.argsort(pred_xy[:, 0])
    px = pred_xy[order, 0]
    py = pred_xy[order, 1]
    if px.size == 0:
        return None, 0.0
    index = np.searchsorted(px, sampled_x, side="left")
    index = np.clip(index, 1, px.size - 1)
    left = index - 1
    take_right = np.abs(px[index] - sampled_x) < np.abs(px[left] - sampled_x)
    nearest = np.where(take_right, index, left)
    tol = rx / max(plot_w, 1.0)
    aligned = np.abs(px[nearest] - sampled_x) <= tol
    coverage = np.zeros(sampled_x.shape, dtype=bool)
    if np.any(aligned):
        y_err = np.abs(py[nearest][aligned] - sampled_y[aligned])
        coverage[aligned] = y_err <= 0.02 * ry
        nrmse = float(np.sqrt(np.mean(np.square(y_err / ry)))) * 100.0
    else:
        nrmse = None
    return nrmse, float(coverage.mean())


def _polyline_distance(points: np.ndarray, polyline: np.ndarray) -> np.ndarray:
    if points.size == 0:
        return np.zeros(0, dtype=np.float64)
    if polyline.shape[0] == 0:
        return np.full(points.shape[0], 1e6)
    tree = cKDTree(polyline)
    _dist, index = tree.query(points, k=1)
    dist = np.asarray(_dist, dtype=np.float64)
    if polyline.shape[0] < 2:
        return dist
    index = np.asarray(index, dtype=np.int64)
    for shift in (0, -1):
        start = np.clip(index + shift, 0, polyline.shape[0] - 2)
        a = polyline[start]
        b = polyline[start + 1]
        edge = b - a
        length2 = np.maximum(np.sum(edge * edge, axis=1), 1e-12)
        t = np.clip(np.sum((points - a) * edge, axis=1) / length2, 0.0, 1.0)
        proj = a + t[:, None] * edge
        dist = np.minimum(dist, np.hypot(points[:, 0] - proj[:, 0], points[:, 1] - proj[:, 1]))
    return dist


def _f1_counts(gt_xy: np.ndarray, pred_xy: np.ndarray, tol: float) -> tuple[int, int, int]:
    if gt_xy.size == 0 and pred_xy.size == 0:
        return 0, 0, 0
    if gt_xy.size == 0:
        return 0, int(pred_xy.shape[0]), 0
    if pred_xy.size == 0:
        return 0, 0, int(gt_xy.shape[0])
    diff = gt_xy[:, None, :] - pred_xy[None, :, :]
    cost = np.hypot(diff[:, :, 0], diff[:, :, 1])
    rows, cols = linear_sum_assignment(cost)
    matched = int(np.sum(cost[rows, cols] <= tol))
    return matched, int(pred_xy.shape[0]) - matched, int(gt_xy.shape[0]) - matched


def _f1(tp: int, fp: int, fn: int) -> float:
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    if prec + rec == 0:
        return 0.0
    return float(2 * prec * rec / (prec + rec))


def _pred_arrays(result: ExtractionResult) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for item in result.series:
        xy = []
        pix = []
        flags = []
        conf = []
        for point in item.points:
            if point.x is None or point.y is None:
                continue
            xy.append((point.x, point.y))
            pix.append((point.px, point.py))
            flags.append(int(point.flags.value))
            conf.append(point.confidence)
        series.append(
            {
                "kind": item.kind,
                "xy": np.asarray(xy, dtype=np.float64).reshape(-1, 2),
                "pix": np.asarray(pix, dtype=np.float64).reshape(-1, 2),
                "flags": np.asarray(flags, dtype=np.int32),
                "conf": np.asarray(conf, dtype=np.float64),
                "flagged": np.asarray([f != 0 for f in flags], dtype=bool),
            }
        )
    return series


def _assign(cost: np.ndarray) -> list[tuple[int, int, float]]:
    if cost.size == 0:
        return []
    rows, cols = linear_sum_assignment(cost)
    return [(int(r), int(c), float(cost[r, c])) for r, c in zip(rows, cols, strict=True)]


def score_sample(gt: dict[str, Any], result: ExtractionResult, runtime_s: float) -> dict[str, Any]:
    """Score one generated figure. Higher-is-better fields are noted in the report."""

    area = result.plot_area
    gt_bbox = tuple(int(v) for v in gt["plot_area"]["bbox"])
    if isinstance(area, PlotArea):
        iou = _iou(area.bbox, gt_bbox)  # type: ignore[arg-type]
        plot_w = max(1, area.bbox[2] - area.bbox[0])
        bbox = area.bbox
    else:
        iou = 0.0
        plot_w = max(1, gt_bbox[2] - gt_bbox[0])
        bbox = gt_bbox
    rx = float(gt["R_x"])
    ry = float(gt["R_y"])
    preds = _pred_arrays(result)
    gt_series = list(gt.get("series") or [])
    chart = str(gt.get("chart_type"))
    n_pred = len(preds)
    n_gt = len(gt_series)

    pair_nrmse: list[list[float]] = [[UNMATCHED for _ in gt_series] for _ in preds]
    pair_cov: list[list[float]] = [[0.0 for _ in gt_series] for _ in preds]
    if chart in {"line", "line+marker"}:
        for i, pred in enumerate(preds):
            for j, series in enumerate(gt_series):
                nrmse, coverage = curve_pair_metrics(
                    series, pred["xy"], rx=rx, ry=ry, plot_w=float(plot_w)
                )
                pair_cov[i][j] = coverage
                if nrmse is not None:
                    pair_nrmse[i][j] = nrmse
        cost = np.asarray(pair_nrmse, dtype=np.float64) if preds and gt_series else np.zeros((0, 0))
    else:
        cost = np.full((n_pred, n_gt), UNMATCHED, dtype=np.float64)
        for i, pred in enumerate(preds):
            for j, series in enumerate(gt_series):
                gt_pix = _gt_points(series)
                tp, fp, fn = _f1_counts(gt_pix, pred["pix"], 3.0)
                f1 = _f1(tp, fp, fn)
                # Cost is on the same percent scale as curve NRMSE.
                cost[i, j] = (1.0 - f1) * 100.0

    assignment = _assign(cost) if cost.size else []
    matched = [(i, j, c) for i, j, c in assignment if c <= 10.0]
    series_match_acc = (len(matched) / max(n_pred, n_gt)) if max(n_pred, n_gt) else 1.0
    matched_gt = {j for _i, j, _c in matched}
    if chart in {"line", "line+marker"} and gt_series:
        coverages = []
        nrmses = []
        for j, _series in enumerate(gt_series):
            owner = next((i for i, jj, _c in matched if jj == j), None)
            if owner is None:
                coverages.append(0.0)
            else:
                coverages.append(pair_cov[owner][j])
                nrmses.append(pair_nrmse[owner][j])
        x_coverage = float(np.mean(coverages))
        curve_nrmse = float(np.mean(nrmses)) if nrmses else None
    else:
        x_coverage = None
        curve_nrmse = None

    # False points: distance to any ground-truth ink polyline / marker / bar top.
    gt_pix_all = []
    gt_poly = []
    for series in gt_series:
        poly = np.asarray(series.get("polyline") or [], dtype=np.float64).reshape(-1, 2)
        if poly.size:
            gt_poly.append(poly)
        pts = _gt_points(series)
        if pts.size:
            gt_pix_all.append(pts)
    confs: list[np.ndarray] = []
    error_flags: list[np.ndarray] = []
    flagged_parts: list[np.ndarray] = []
    n_emitted = 0
    n_false = 0
    for pred in preds:
        if pred["pix"].size == 0:
            continue
        dist = np.full(pred["pix"].shape[0], 1e6)
        for poly in gt_poly:
            dist = np.minimum(dist, _polyline_distance(pred["pix"], poly))
        for pts in gt_pix_all:
            if pts.shape[0] == 0:
                continue
            tree = cKDTree(pts)
            d, _ = tree.query(pred["pix"], k=1)
            dist = np.minimum(dist, np.asarray(d, dtype=np.float64))
        is_false = dist > 3.0
        n_emitted += int(is_false.size)
        n_false += int(is_false.sum())
        confs.append(pred["conf"])
        error_flags.append(is_false)
        flagged_parts.append(pred["flagged"])
    false_point_rate = float(n_false / n_emitted) if n_emitted else 0.0

    fabrication = 0
    bridged = 0
    for item in result.series:
        for point in item.points:
            if (
                PointFlag.INTERPOLATED in point.flags
                and point.x is not None
                and point.y is not None
                and np.isfinite(point.x)
                and np.isfinite(point.y)
            ):
                bridged += 1
    for i, j, _c in matched:
        series = gt_series[j]
        invisible = series.get("invisible_ranges") or []
        pred = preds[i]
        for k in range(pred["xy"].shape[0]):
            if pred["flags"][k] != 0 or pred["conf"][k] < 0.5:
                continue
            x_val = float(pred["xy"][k, 0])
            px, py = float(pred["pix"][k, 0]), float(pred["pix"][k, 1])
            outside = px < bbox[0] or py < bbox[1] or px >= bbox[2] or py >= bbox[3]
            in_gap = any(float(lo) <= x_val <= float(hi) for lo, hi in invisible)
            if outside or in_gap:
                fabrication += 1

    scatter_f1 = _image_scatter_f1(gt_series, preds) if chart == "scatter" else None
    bar_rel = _image_bar_rel(gt_series, preds, ry) if chart == "bar" else None

    point_conf = np.concatenate(confs) if confs else np.zeros(0)
    point_err = np.concatenate(error_flags) if error_flags else np.zeros(0, dtype=bool)
    point_flagged = np.concatenate(flagged_parts) if flagged_parts else np.zeros(0, dtype=bool)

    return {
        "id": gt.get("id"),
        "chart_type": chart,
        "degradation": gt.get("degradation"),
        "series_bucket": gt.get("series_bucket"),
        "color_mode": gt.get("color_mode"),
        "domain_shape": gt.get("domain_shape"),
        "occluded": bool(gt.get("occluded")),
        "markers_overlap": bool(gt.get("markers_overlap")),
        "width": int(gt.get("width") or 0),
        "height": int(gt.get("height") or 0),
        "n_series_gt": n_gt,
        "n_series_pred": n_pred,
        "plot_area_iou": iou,
        "axis_calib_rel_err": axis_calib_rel_err(gt, result),
        "curve_nrmse_range": curve_nrmse,
        "x_coverage": x_coverage,
        "false_point_rate": false_point_rate,
        "series_match_acc": float(series_match_acc),
        "scatter_f1": scatter_f1,
        "bar_rel_err": bar_rel,
        "fabrication_count": int(fabrication),
        "bridged_count": int(bridged),
        "runtime_s": float(runtime_s),
        "n_points": int(point_conf.size),
        "point_confidence": point_conf,
        "point_error": point_err.astype(bool),
        "point_flagged": point_flagged,
        "matched_gt": len(matched_gt),
    }


def _gt_points(series: dict[str, Any]) -> np.ndarray:
    if series.get("markers"):
        return np.asarray([[m["px"], m["py"]] for m in series["markers"]], dtype=np.float64)
    if series.get("bars"):
        return np.asarray([[b["px"], b["py"]] for b in series["bars"]], dtype=np.float64)
    poly = series.get("polyline") or []
    return np.asarray(poly, dtype=np.float64).reshape(-1, 2)


def _image_scatter_f1(gt_series: list[dict[str, Any]], preds: list[dict[str, Any]]) -> float:
    if not gt_series and not preds:
        return 1.0
    cost = np.ones((max(len(preds), 1), max(len(gt_series), 1)))
    counts: list[list[tuple[int, int, int]]] = [[(0, 0, 0) for _ in gt_series] for _ in preds]
    for i, pred in enumerate(preds):
        for j, series in enumerate(gt_series):
            tp, fp, fn = _f1_counts(_gt_points(series), pred["pix"], 3.0)
            counts[i][j] = (tp, fp, fn)
            cost[i, j] = 1.0 - _f1(tp, fp, fn)
    if not preds or not gt_series:
        gt_n = sum(_gt_points(s).shape[0] for s in gt_series)
        pr_n = sum(p["pix"].shape[0] for p in preds)
        return _f1(0, pr_n, gt_n)
    rows, cols = linear_sum_assignment(cost[: len(preds), : len(gt_series)])
    used_gt: set[int] = set()
    tp = fp = fn = 0
    for r, c in zip(rows, cols, strict=True):
        used_gt.add(int(c))
        t, f_p, f_n = counts[int(r)][int(c)]
        tp += t
        fp += f_p
        fn += f_n
    for j, series in enumerate(gt_series):
        if j not in used_gt:
            fn += int(_gt_points(series).shape[0])
    return _f1(tp, fp, fn)


def _image_bar_rel(
    gt_series: list[dict[str, Any]], preds: list[dict[str, Any]], ry: float
) -> float | None:
    gt_bars = []
    for series in gt_series:
        for bar in series.get("bars") or []:
            gt_bars.append((float(bar["x"]), float(bar["y"])))
    pred_bars = []
    for pred in preds:
        if pred["kind"] != "bar":
            continue
        for x_val, y_val in pred["xy"]:
            pred_bars.append((float(x_val), float(y_val)))
    if not gt_bars:
        return None
    if not pred_bars or ry <= 0:
        return 1.0
    gt_arr = np.asarray(gt_bars, dtype=np.float64)
    pr_arr = np.asarray(pred_bars, dtype=np.float64)
    cost = np.abs(gt_arr[:, 0][:, None] - pr_arr[:, 0][None, :])
    rows, cols = linear_sum_assignment(cost)
    errors = []
    for r, c in zip(rows, cols, strict=True):
        if cost[r, c] <= 0.35:
            errors.append(abs(float(gt_arr[r, 1] - pr_arr[c, 1])) / ry)
    if len(errors) < 0.5 * len(gt_bars):
        return 1.0
    return float(np.median(errors))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.median(np.asarray(values, dtype=np.float64)))


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def _subset(rows: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    if name == "all":
        return rows
    if name == "line/clean":
        return [r for r in rows if r["chart_type"] == "line" and r["degradation"] == "clean"]
    if name == "line/light":
        return [r for r in rows if r["chart_type"] == "line" and r["degradation"] == "light"]
    if name == "line/clean/unoccluded":
        return [
            r
            for r in rows
            if r["chart_type"] == "line" and r["degradation"] == "clean" and not r["occluded"]
        ]
    if name == "line/all":
        return [r for r in rows if r["chart_type"] in {"line", "line+marker"}]
    if name == "multi/tab10":
        return [
            r
            for r in rows
            if r["chart_type"] in {"line", "line+marker"}
            and r["color_mode"] == "tab10"
            and int(r["n_series_gt"]) >= 2
        ]
    if name == "scatter/nonoverlap":
        return [r for r in rows if r["chart_type"] == "scatter" and not r["markers_overlap"]]
    if name == "bar":
        return [r for r in rows if r["chart_type"] == "bar"]
    if name == "size_ok":
        return [r for r in rows if int(r["width"]) <= 1600 and int(r["height"]) <= 1200]
    return rows


def _auroc(confidence: np.ndarray, is_error: np.ndarray) -> float | None:
    if confidence.size == 0 or not np.any(is_error) or np.all(is_error):
        return None
    # Score "predicted error" as 1 - confidence. Rank-based AUROC.
    scores = 1.0 - confidence
    order = np.argsort(scores)
    ranks = np.empty(scores.size, dtype=np.float64)
    ranks[order] = np.arange(1, scores.size + 1)
    n_pos = float(np.sum(is_error))
    n_neg = float(scores.size) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    sum_ranks = float(ranks[is_error].sum())
    return (sum_ranks - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _ece(confidence: np.ndarray, is_error: np.ndarray, bins: int = 10) -> float | None:
    if confidence.size == 0:
        return None
    correct = ~is_error
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = confidence.size
    error = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (confidence >= lo) & (confidence < hi if hi < 1 else confidence <= hi)
        if not np.any(mask):
            continue
        acc = float(correct[mask].mean())
        conf = float(confidence[mask].mean())
        error += (mask.sum() / total) * abs(acc - conf)
    return float(error)


def _flag_rates(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    flagged = [
        r["point_flagged"]
        for r in rows
        if r.get("point_flagged") is not None and r["point_flagged"].size
    ]
    errors = [
        r["point_error"] for r in rows if r.get("point_error") is not None and r["point_error"].size
    ]
    if not flagged or not errors:
        return {"flag_precision": None, "flag_recall": None}
    pred = np.concatenate(flagged)
    truth = np.concatenate(errors)
    if pred.shape != truth.shape:
        return {"flag_precision": None, "flag_recall": None}
    tp = int(np.sum(pred & truth))
    fp = int(np.sum(pred & ~truth))
    fn = int(np.sum(~pred & truth))
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {"flag_precision": precision, "flag_recall": recall}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Category medians plus the scalars the gates read."""

    def col(subset: list[dict[str, Any]], key: str) -> list[float]:
        values = []
        for row in subset:
            value = row.get(key)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            values.append(float(value))
        return values

    clean = _subset(rows, "line/clean")
    conf = (
        np.concatenate([r["point_confidence"] for r in rows if r["point_confidence"].size])
        if rows
        else np.zeros(0)
    )
    err = (
        np.concatenate([r["point_error"] for r in rows if r["point_error"].size])
        if rows
        else np.zeros(0, dtype=bool)
    )
    # Flag precision/recall need the flag bit. Approximate with confidence < 0.9 as "flagged"
    # is wrong. The evaluate step passes flag arrays separately when present.
    summary = {
        "n": len(rows),
        "plot_area_iou_median": _median(col(rows, "plot_area_iou")),
        "axis_calib_rel_err_median": _median(col(rows, "axis_calib_rel_err")),
        "curve_nrmse_clean_median": _median(col(clean, "curve_nrmse_range")),
        "curve_nrmse_clean_p90": _percentile(col(clean, "curve_nrmse_range"), 90),
        "curve_nrmse_light_median": _median(col(_subset(rows, "line/light"), "curve_nrmse_range")),
        "x_coverage_clean_unoccluded_median": _median(
            col(_subset(rows, "line/clean/unoccluded"), "x_coverage")
        ),
        "x_coverage_median": _median(col(_subset(rows, "line/all"), "x_coverage")),
        "false_point_rate_median": _median(col(_subset(rows, "line/all"), "false_point_rate")),
        "series_match_acc": (
            float(np.mean(col(_subset(rows, "multi/tab10"), "series_match_acc")))
            if col(_subset(rows, "multi/tab10"), "series_match_acc")
            else None
        ),
        "scatter_f1_median": _median(col(_subset(rows, "scatter/nonoverlap"), "scatter_f1")),
        "bar_rel_err_median": _median(col(_subset(rows, "bar"), "bar_rel_err")),
        "fabrication_count": int(sum(int(r["fabrication_count"]) for r in rows)),
        "bridged_count": int(sum(int(r.get("bridged_count") or 0) for r in rows)),
        "completeness": _median(col(rows, "completeness"))
        if any("completeness" in r for r in rows)
        else 1.0,
        "runtime_s_median": _median(col(_subset(rows, "size_ok"), "runtime_s")),
        "curve_nrmse_range_median": _median(col(_subset(rows, "line/all"), "curve_nrmse_range")),
        "flag_auroc": _auroc(conf, err) if conf.size else None,
        "ece": _ece(conf, err) if conf.size else None,
    }
    summary.update(_flag_rates(rows))
    categories: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = f"{row['chart_type']}/{row['degradation']}/{row['series_bucket']}"
        groups.setdefault(key, []).append(row)
        shape_key = f"{row['chart_type']}/{row['degradation']}/{row['domain_shape']}"
        groups.setdefault(shape_key, []).append(row)
    for key, group in sorted(groups.items()):
        categories[key] = {
            "n": len(group),
            "plot_area_iou_median": _median(col(group, "plot_area_iou")),
            "axis_calib_rel_err_median": _median(col(group, "axis_calib_rel_err")),
            "curve_nrmse_median": _median(col(group, "curve_nrmse_range")),
            "curve_nrmse_p90": _percentile(col(group, "curve_nrmse_range"), 90),
            "x_coverage_median": _median(col(group, "x_coverage")),
            "false_point_rate_median": _median(col(group, "false_point_rate")),
            "series_match_acc": float(np.mean(col(group, "series_match_acc"))) if group else None,
            "scatter_f1_median": _median(col(group, "scatter_f1")),
            "bar_rel_err_median": _median(col(group, "bar_rel_err")),
            "fabrication_count": int(sum(int(r["fabrication_count"]) for r in group)),
        }
    summary["categories"] = categories
    return summary


def evaluate_gates(summary: dict[str, Any], gates: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for name, spec in gates.items():
        measured = summary.get(name)
        target = float(spec["value"])
        op = str(spec["op"])
        if measured is None:
            ok = False
        elif op == ">=":
            ok = float(measured) >= target
        elif op == "<=":
            ok = float(measured) <= target
        elif op == "==":
            ok = float(measured) == target
        else:
            ok = False
        results[name] = {
            "measured": measured,
            "op": op,
            "target": target,
            "subset": spec.get("subset"),
            "pass": bool(ok),
            "hard": bool(spec.get("hard", False)),
        }
    return results


def regression_failures(
    current: dict[str, Any],
    baseline: dict[str, Any],
    *,
    metrics: list[str],
    relative: float,
    margin_fraction: float,
    gates: dict[str, Any],
) -> list[str]:
    """Return human-readable failures. Empty means the smoke run holds."""

    higher = {"x_coverage_median", "series_match_acc", "scatter_f1_median"}
    failures: list[str] = []
    base_metrics = baseline.get("metrics", baseline)
    for name in metrics:
        old = base_metrics.get(name)
        new = current.get(name)
        if old is None or new is None:
            continue
        old_f, new_f = float(old), float(new)
        if name in higher:
            drop = old_f - new_f
            scale = abs(old_f) if old_f else 1.0
        else:
            drop = new_f - old_f
            scale = abs(old_f) if old_f else 1.0
        gate = gates.get(name) or {}
        target = gate.get("value")
        margin = abs(old_f - float(target)) if target is not None else 0.0
        relative_hit = drop > relative * scale and drop > 0
        absolute_hit = margin > 0 and drop > margin_fraction * margin
        if relative_hit or absolute_hit:
            failures.append(f"{name} moved from {old_f:.6g} to {new_f:.6g} (drop {drop:.6g})")
    return failures
