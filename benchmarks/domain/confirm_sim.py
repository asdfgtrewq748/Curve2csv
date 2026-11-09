"""Simulate light human confirmation on failing figures (W3/W4).

Supports both domain and real (OWID) benchmark sets.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks.real.metrics import score_figure
from curve2csv.api import clear_range, extract, extract_with_limits, pick_series, trace_stroke
from curve2csv.types import AxisCalibration, AxisScale, ExtractionResult, PointFlag, Series

HERE = Path(__file__).resolve().parent
CLICK_S = 2.0
TYPE_S = 4.0
REVIEW_S = 10.0


def _valid_xy_sim(series: Series) -> np.ndarray:
    rows: list[list[float]] = []
    for point in series.points:
        if (
            point.x is None
            or point.y is None
            or not np.isfinite(point.x)
            or not np.isfinite(point.y)
        ):
            continue
        if (point.flags & ~PointFlag.MANUAL) != PointFlag.NONE:
            continue
        rows.append([float(point.x), float(point.y)])
    if not rows:
        return np.zeros((0, 2), dtype=np.float64)
    return np.asarray(rows, dtype=np.float64)


def _score(result: ExtractionResult, gt: dict[str, Any]) -> dict[str, Any]:
    series = [np.asarray(v, dtype=np.float64) for v in gt["series"].values()]
    pred = [xy for xy in (_valid_xy_sim(s) for s in result.series) if xy.shape[0] > 0]
    return score_figure(
        series,
        pred,
        x_scale=gt["x_scale"],
        y_scale=gt["y_scale"],
        x_range=(float(gt["x_range"][0]), float(gt["x_range"][1])),
        y_range=(float(gt["y_range"][0]), float(gt["y_range"][1])),
        plot_w=float(gt["plot_w"]),
    )


def _fwd(value: float, scale: str) -> float:
    return math.log10(value) if scale == "log10" else value


def _to_pixel(
    result: ExtractionResult, gt: dict[str, Any], x: float, y: float
) -> tuple[float, float] | None:
    if "plot_box_px" in gt:
        x0, y0, x1, y1 = gt["plot_box_px"]
        xa, xb = (_fwd(v, gt["x_scale"]) for v in gt["x_range"])
        ya, yb = (_fwd(v, gt["y_scale"]) for v in gt["y_range"])
        px = x0 + (_fwd(x, gt["x_scale"]) - xa) / (xb - xa) * (x1 - x0)
        py = y1 - (_fwd(y, gt["y_scale"]) - ya) / (yb - ya) * (y1 - y0)
        return float(px), float(py)
    if result.mapper is not None:
        try:
            return result.mapper.data_to_pixel(x, y)
        except Exception:
            pass
    x_cal = result.calibration.get("x")
    y_cal = result.calibration.get("y")
    if isinstance(x_cal, AxisCalibration) and isinstance(y_cal, AxisCalibration):
        try:
            px = float(x_cal.data_to_px(np.asarray([x], dtype=np.float64))[0])
            py = float(y_cal.data_to_px(np.asarray([y], dtype=np.float64))[0])
            return float(px), float(py)
        except Exception:
            pass
    return None


def _pick(result: ExtractionResult, gt: dict[str, Any]) -> ExtractionResult:
    gt_midpoints = []
    for curve in gt["series"].values():
        pts = np.asarray(curve, dtype=np.float64)
        mid = pts[len(pts) // 2]
        pix = _to_pixel(result, gt, mid[0], mid[1])
        if pix is not None:
            gt_midpoints.append(pix)
    if not gt_midpoints:
        return result
    try:
        return pick_series(result, gt_midpoints, radius=12.0)
    except Exception:
        return result


def _wrong_ranges(result: ExtractionResult, gt: dict[str, Any]) -> list[tuple[float, float]]:
    ry = abs(_fwd(gt["y_range"][1], gt["y_scale"]) - _fwd(gt["y_range"][0], gt["y_scale"]))
    span = abs(gt["x_range"][1] - gt["x_range"][0])
    gt_curves = [np.asarray(v, dtype=np.float64) for v in gt["series"].values() if len(v) >= 2]
    if not gt_curves:
        return []

    bad: list[float] = []
    for series in result.series:
        xy = _valid_xy_sim(series)
        for x, y in xy:
            errs = []
            for pts in gt_curves:
                if pts[0, 0] <= x <= pts[-1, 0]:
                    ref = float(np.interp(x, pts[:, 0], pts[:, 1]))
                    errs.append(abs(_fwd(y, gt["y_scale"]) - _fwd(ref, gt["y_scale"])))
            if errs and min(errs) > 0.05 * ry:
                bad.append(float(x))

    if not bad:
        return []
    bad.sort()
    ranges: list[list[float]] = [[bad[0], bad[0]]]
    for x in bad[1:]:
        if x - ranges[-1][1] <= 0.02 * span:
            ranges[-1][1] = x
        else:
            ranges.append([x, x])
    ranges.sort(key=lambda r: r[1] - r[0], reverse=True)
    pad = 0.005 * span
    return [(r[0] - pad, r[1] + pad) for r in ranges[:2]]


def _missing_pairs(
    result: ExtractionResult, gt: dict[str, Any]
) -> list[tuple[str, str, float, float]]:
    s = _score(result, gt)
    gt_keys = list(gt["series"].keys())
    missing = []
    span = abs(gt["x_range"][1] - gt["x_range"][0])
    plot_w = float(gt.get("plot_w", 500))
    tol = span / max(plot_w, 1.0) * 2.0

    for pair in s.get("pairs", []):
        if pair["x_coverage"] < 0.90:
            pred_idx = pair["pred"]
            gt_idx = pair["gt"]
            if pred_idx >= len(result.series) or gt_idx >= len(gt_keys):
                continue
            pred_s = result.series[pred_idx]
            gt_name = gt_keys[gt_idx]
            gt_pts = np.asarray(gt["series"][gt_name], dtype=np.float64)
            pred_xy = _valid_xy_sim(pred_s)
            pred_xs = pred_xy[:, 0] if pred_xy.shape[0] > 0 else np.zeros(0, dtype=np.float64)
            uncovered = [
                float(x)
                for x in gt_pts[:, 0]
                if pred_xs.size == 0 or np.min(np.abs(pred_xs - x)) > tol
            ]
            if len(uncovered) >= 2:
                missing.append((pred_s.series_id, gt_name, min(uncovered), max(uncovered)))
    return missing


def simulate(slug: str, root: Path = HERE) -> dict[str, Any]:
    gt = json.loads((root / "gt" / f"{slug}.json").read_text(encoding="utf-8"))
    image = root / "figures" / f"{slug}.png"
    result = extract(image)
    log: list[dict[str, Any]] = []
    clicks = typed = 0
    auto = _score(result, gt)
    if auto["correct"]:
        return {"slug": slug, "auto": True, "passed": True, "clicks": 0, "typed": 0, "steps": log}

    def record(step: str, res: ExtractionResult) -> dict[str, Any]:
        s = _score(res, gt)
        log.append(
            {
                "step": step,
                "clicks": clicks,
                "typed": typed,
                "correct": s["correct"],
                "reason": s["reason"],
                "n_pred": s["n_pred"],
                "worst_nrmse": s["worst_nrmse"],
                "worst_coverage": s["worst_coverage"],
            }
        )
        return s

    if len(result.series) > len(gt["series"]):
        res_pick = _pick(result, gt)
        if len(res_pick.series) < len(result.series):
            result = res_pick
            clicks += len(gt["series"])
            if record("pick", result)["correct"]:
                return _done(slug, log, clicks, typed, True)

    scale = {"linear": AxisScale.LINEAR, "log10": AxisScale.LOG10}
    box = gt.get("plot_box_px")
    plot_box_tuple = None
    if box is not None:
        shifted_box = [v + d for v, d in zip(box, (1.0, -1.0, -1.0, 1.0), strict=False)]
        plot_box_tuple = tuple(int(round(v)) for v in shifted_box)

    try:
        res_limits = extract_with_limits(
            image,
            xmin=gt["x_range"][0],
            xmax=gt["x_range"][1],
            ymin=gt["y_range"][0],
            ymax=gt["y_range"][1],
            x_scale=scale[gt["x_scale"]],
            y_scale=scale[gt["y_scale"]],
            plot_box=plot_box_tuple,
        )
        clicks += 2 if plot_box_tuple else 0
        typed += 4
        result = res_limits
        if record("box+limits", result)["correct"]:
            return _done(slug, log, clicks, typed, True)
    except Exception:
        pass

    if len(result.series) > len(gt["series"]):
        res_pick = _pick(result, gt)
        if len(res_pick.series) < len(result.series):
            result = res_pick
            clicks += len(gt["series"])
            if record("box+limits+pick", result)["correct"]:
                return _done(slug, log, clicks, typed, True)

    for lo, hi in _wrong_ranges(result, gt):
        try:
            result = clear_range(result, lo, hi)
            clicks += 2
            if record(f"clear[{lo:.4g},{hi:.4g}]", result)["correct"]:
                return _done(slug, log, clicks, typed, True)
        except Exception:
            pass

    # Semi-automatic trace_stroke for missing coverage
    for s_id, gt_name, m_lo, m_hi in _missing_pairs(result, gt):
        pts = np.asarray(gt["series"][gt_name], dtype=np.float64)
        m_mid = (m_lo + m_hi) / 2.0
        y_lo = float(np.interp(m_lo, pts[:, 0], pts[:, 1]))
        y_mid = float(np.interp(m_mid, pts[:, 0], pts[:, 1]))
        y_hi = float(np.interp(m_hi, pts[:, 0], pts[:, 1]))
        p0 = _to_pixel(result, gt, m_lo, y_lo)
        p1 = _to_pixel(result, gt, m_mid, y_mid)
        p2 = _to_pixel(result, gt, m_hi, y_hi)
        if p0 and p1 and p2:
            stroke = [p0, p1, p2]
            try:
                result = trace_stroke(result, stroke, series_id=s_id, radius=12.0, bridge=True)
                clicks += 2
                if record(f"trace[{gt_name}:{m_lo:.4g},{m_hi:.4g}]", result)["correct"]:
                    return _done(slug, log, clicks, typed, True)
            except Exception:
                pass

    return _done(slug, log, clicks, typed, False)


def _done(
    slug: str, log: list[dict[str, Any]], clicks: int, typed: int, ok: bool
) -> dict[str, Any]:
    return {
        "slug": slug,
        "auto": False,
        "passed": ok,
        "clicks": clicks,
        "typed": typed,
        "steps": log,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=HERE)
    parser.add_argument("--split", choices=("dev", "held-out", "all"), default="held-out")
    parser.add_argument("--out", type=Path, default=HERE.parents[0] / "results")
    args = parser.parse_args()
    manifest = json.loads((args.root / "manifest.json").read_text(encoding="utf-8"))
    slugs = [
        f["slug"] for f in manifest["figures"] if args.split == "all" or f["split"] == args.split
    ]
    rows = []
    for slug in slugs:
        row = simulate(slug, root=args.root)
        row["est_seconds"] = REVIEW_S + CLICK_S * row["clicks"] + TYPE_S * row["typed"]
        rows.append(row)
        print(
            f"{slug:28s} auto={row['auto']!s:5s} passed={row['passed']!s:5s} clicks={row['clicks']} typed={row['typed']} "
            f"~{row['est_seconds']:.0f}s {[s['step'] + ':' + s['reason'] for s in row['steps']]}",
            flush=True,
        )
    summary = {
        "n": len(rows),
        "auto_pass": sum(r["auto"] for r in rows),
        "pass_after_confirm": sum(r["passed"] for r in rows),
        "confirmed_figures": sum(not r["auto"] for r in rows),
        "mean_clicks_failing": float(np.mean([r["clicks"] for r in rows if not r["auto"]]))
        if any(not r["auto"] for r in rows)
        else 0.0,
        "mean_typed_failing": float(np.mean([r["typed"] for r in rows if not r["auto"]]))
        if any(not r["auto"] for r in rows)
        else 0.0,
        "mean_est_seconds_all": float(np.mean([r["est_seconds"] for r in rows])) if rows else 0.0,
        "timing_model": {
            "click_s": CLICK_S,
            "typed_value_s": TYPE_S,
            "review_s_per_figure": REVIEW_S,
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    dataset_name = args.root.name
    (args.out / f"{dataset_name}-v1-confirm-{args.split}.json").write_text(
        json.dumps({"summary": summary, "figures": rows}, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
