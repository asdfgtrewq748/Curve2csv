"""Simulate light human confirmation on failing domain figures (W3).

For every figure that fails strict scoring automatically, apply the cheapest
confirm steps in order and stop at the first pass:

1. ``pick``: one click on the curve when more than one series was returned.
2. ``box+limits``: two clicks on opposite plot-frame corners plus four typed
   axis-end tick labels (``extract_with_limits``), then ``pick`` if needed.
3. ``clear``: up to two ``clear_range`` drags (two clicks each) over x-ranges
   where the overlay visibly leaves the drawn curve.

What a human would read: frame corners and end tick labels come from the
rendered frame (``plot_box_px`` with a +/-1 px click jitter, ``x_range`` /
``y_range`` are the labeled end ticks). Proxies that touch truth: the pick
click is placed on the drawn curve (the pixel of the middle GT point, which
is exactly the drawn ink), and the "visibly wrong" ranges for ``clear`` are
found by comparing to GT (a stand-in for the human eye on the QA overlay).
No predicted point is moved or added by any step.

    python -m benchmarks.domain.confirm_sim --split held-out
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks.real.metrics import score_figure, valid_xy
from curve2csv.api import clear_range, extract, extract_with_limits, pick_series
from curve2csv.types import AxisScale, ExtractionResult

HERE = Path(__file__).resolve().parent
CLICK_S = 2.0
TYPE_S = 4.0
REVIEW_S = 10.0


def _score(result: ExtractionResult, gt: dict[str, Any]) -> dict[str, Any]:
    series = [np.asarray(v, dtype=np.float64) for v in gt["series"].values()]
    pred = [xy for xy in (valid_xy(s) for s in result.series) if xy.shape[0] > 0]
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


def _gt_pixel(gt: dict[str, Any], x: float, y: float) -> tuple[float, float]:
    x0, y0, x1, y1 = gt["plot_box_px"]
    xa, xb = (_fwd(v, gt["x_scale"]) for v in gt["x_range"])
    ya, yb = (_fwd(v, gt["y_scale"]) for v in gt["y_range"])
    px = x0 + (_fwd(x, gt["x_scale"]) - xa) / (xb - xa) * (x1 - x0)
    py = y1 - (_fwd(y, gt["y_scale"]) - ya) / (yb - ya) * (y1 - y0)
    return px, py


def _pick(result: ExtractionResult, gt: dict[str, Any]) -> ExtractionResult:
    pts = gt["series"]["curve"]
    mid = pts[len(pts) // 2]
    return pick_series(result, _gt_pixel(gt, mid[0], mid[1]), radius=8.0)


def _wrong_ranges(result: ExtractionResult, gt: dict[str, Any]) -> list[tuple[float, float]]:
    pts = np.asarray(gt["series"]["curve"], dtype=np.float64)
    ry = abs(_fwd(gt["y_range"][1], gt["y_scale"]) - _fwd(gt["y_range"][0], gt["y_scale"]))
    bad: list[float] = []
    for series in result.series:
        xy = valid_xy(series)
        for x, y in xy:
            if not (pts[0, 0] <= x <= pts[-1, 0]):
                bad.append(float(x))
                continue
            ref = float(np.interp(x, pts[:, 0], pts[:, 1]))
            if abs(_fwd(y, gt["y_scale"]) - _fwd(ref, gt["y_scale"])) > 0.02 * ry:
                bad.append(float(x))
    if not bad:
        return []
    bad.sort()
    span = abs(gt["x_range"][1] - gt["x_range"][0])
    ranges: list[list[float]] = [[bad[0], bad[0]]]
    for x in bad[1:]:
        if x - ranges[-1][1] <= 0.02 * span:
            ranges[-1][1] = x
        else:
            ranges.append([x, x])
    ranges.sort(key=lambda r: r[1] - r[0], reverse=True)
    pad = 0.005 * span
    return [(r[0] - pad, r[1] + pad) for r in ranges[:2]]


def simulate(slug: str) -> dict[str, Any]:
    gt = json.loads((HERE / "gt" / f"{slug}.json").read_text(encoding="utf-8"))
    image = HERE / "figures" / f"{slug}.png"
    result = extract(image)
    log: list[dict[str, Any]] = []
    clicks = typed = 0
    auto = _score(result, gt)
    if auto["correct"]:
        return {"slug": slug, "auto": True, "passed": True, "clicks": 0, "typed": 0, "steps": log}

    def record(step: str, res: ExtractionResult) -> dict[str, Any]:
        s = _score(res, gt)
        log.append({"step": step, "clicks": clicks, "typed": typed, "correct": s["correct"],
                    "reason": s["reason"], "n_pred": s["n_pred"],
                    "worst_nrmse": s["worst_nrmse"], "worst_coverage": s["worst_coverage"]})
        return s

    if len(result.series) > 1:
        result = _pick(result, gt)
        clicks += 1
        if record("pick", result)["correct"]:
            return _done(slug, log, clicks, typed, True)
    box = [v + d for v, d in zip(gt["plot_box_px"], (1.0, -1.0, -1.0, 1.0), strict=False)]
    scale = {"linear": AxisScale.LINEAR, "log10": AxisScale.LOG10}
    result = extract_with_limits(
        image,
        xmin=gt["x_range"][0], xmax=gt["x_range"][1],
        ymin=gt["y_range"][0], ymax=gt["y_range"][1],
        x_scale=scale[gt["x_scale"]], y_scale=scale[gt["y_scale"]],
        plot_box=tuple(int(round(v)) for v in box),  # type: ignore[arg-type]
    )
    clicks += 2
    typed += 4
    if record("box+limits", result)["correct"]:
        return _done(slug, log, clicks, typed, True)
    if len(result.series) > 1:
        result = _pick(result, gt)
        clicks += 1
        if record("box+limits+pick", result)["correct"]:
            return _done(slug, log, clicks, typed, True)
    for lo, hi in _wrong_ranges(result, gt):
        result = clear_range(result, lo, hi)
        clicks += 2
        if record(f"clear[{lo:.4g},{hi:.4g}]", result)["correct"]:
            return _done(slug, log, clicks, typed, True)
    return _done(slug, log, clicks, typed, False)


def _done(slug: str, log: list[dict[str, Any]], clicks: int, typed: int, ok: bool) -> dict[str, Any]:
    return {"slug": slug, "auto": False, "passed": ok, "clicks": clicks, "typed": typed, "steps": log}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "held-out", "all"), default="held-out")
    parser.add_argument("--out", type=Path, default=HERE.parents[0] / "results")
    args = parser.parse_args()
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    slugs = [f["slug"] for f in manifest["figures"] if args.split == "all" or f["split"] == args.split]
    rows = []
    for slug in slugs:
        row = simulate(slug)
        row["est_seconds"] = REVIEW_S + CLICK_S * row["clicks"] + TYPE_S * row["typed"]
        rows.append(row)
        print(f"{slug:28s} auto={row['auto']!s:5s} passed={row['passed']!s:5s} clicks={row['clicks']} typed={row['typed']} "
              f"~{row['est_seconds']:.0f}s {[s['step'] + ':' + s['reason'] for s in row['steps']]}", flush=True)
    summary = {
        "n": len(rows),
        "auto_pass": sum(r["auto"] for r in rows),
        "pass_after_confirm": sum(r["passed"] for r in rows),
        "confirmed_figures": sum(not r["auto"] for r in rows),
        "mean_clicks_failing": float(np.mean([r["clicks"] for r in rows if not r["auto"]])) if any(not r["auto"] for r in rows) else 0.0,
        "mean_typed_failing": float(np.mean([r["typed"] for r in rows if not r["auto"]])) if any(not r["auto"] for r in rows) else 0.0,
        "mean_est_seconds_all": float(np.mean([r["est_seconds"] for r in rows])) if rows else 0.0,
        "timing_model": {"click_s": CLICK_S, "typed_value_s": TYPE_S, "review_s_per_figure": REVIEW_S},
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"domain-v1-confirm-{args.split}.json").write_text(
        json.dumps({"summary": summary, "figures": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
