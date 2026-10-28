"""Score the frozen OWID set. Dev may be inspected while developing; held-out is reported separately.

python -m benchmarks.real.evaluate --split dev
python -m benchmarks.real.evaluate --split held-out
python -m benchmarks.real.evaluate --split all --out benchmarks/results
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks.real.metrics import score_figure, valid_xy
from curve2csv.api import extract
from curve2csv.types import AxisCalibration, PointFlag

ROOT = Path(__file__).resolve().parents[2]
REAL = Path(__file__).resolve().parent


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _one(gt_path: Path, image_path: Path) -> dict[str, Any]:
    document = json.loads(gt_path.read_text(encoding="utf-8"))
    started = time.perf_counter()
    result = extract(image_path)
    elapsed = time.perf_counter() - started
    x_cal = result.calibration.get("x")
    y_cal = result.calibration.get("y")
    row: dict[str, Any] = {
        "slug": document["slug"],
        "split": document["split"],
        "title": document.get("title"),
        "source_url": document["source_url"],
        "license": document["license"],
        "runtime_s": elapsed,
        "x_scale_gt": document["x_scale"],
        "y_scale_gt": document["y_scale"],
        "x_scale_pred": x_cal.scale.value if isinstance(x_cal, AxisCalibration) else None,
        "y_scale_pred": y_cal.scale.value if isinstance(y_cal, AxisCalibration) else None,
    }
    if not isinstance(x_cal, AxisCalibration) or not isinstance(y_cal, AxisCalibration):
        row.update(
            {
                "correct": False,
                "reason": "no_calibration",
                "n_gt": len(document["series"]),
                "n_pred": 0,
                "worst_nrmse": None,
                "worst_coverage": None,
                "slope_rel_err": None,
                "intercept_err_range": None,
                "bridged_count": 0,
                "with_bridge": {
                    "correct": False,
                    "reason": "no_calibration",
                    "n_gt": len(document["series"]),
                    "n_pred": 0,
                    "worst_nrmse": None,
                    "worst_coverage": None,
                },
            }
        )
        return row
    gt_series = [np.asarray(points, dtype=np.float64) for points in document["series"].values()]
    score_kwargs = {
        "x_scale": document["x_scale"],
        "y_scale": document["y_scale"],
        "x_range": (float(document["x_range"][0]), float(document["x_range"][1])),
        "y_range": (float(document["y_range"][0]), float(document["y_range"][1])),
        "plot_w": float(document["plot_w"]),
    }

    def _pred(include_interpolated: bool) -> list[np.ndarray]:
        return [
            xy
            for xy in (
                valid_xy(series, include_interpolated=include_interpolated)
                for series in result.series
            )
            if xy.shape[0] > 0
        ]

    strict = score_figure(gt_series, _pred(False), **score_kwargs)
    bridged = score_figure(gt_series, _pred(True), **score_kwargs)
    row.update(strict)
    row["bridged_count"] = sum(
        1
        for series in result.series
        for point in series.points
        if PointFlag.INTERPOLATED in point.flags and point.x is not None and point.y is not None
    )
    row["with_bridge"] = {
        "correct": bridged["correct"],
        "reason": bridged["reason"],
        "n_gt": bridged["n_gt"],
        "n_pred": bridged["n_pred"],
        "worst_nrmse": bridged["worst_nrmse"],
        "worst_coverage": bridged["worst_coverage"],
    }
    return row


def _rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    correct = sum(1 for row in rows if row["correct"])
    reasons: dict[str, int] = {}
    for row in rows:
        if not row["correct"]:
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    slopes = [row["slope_rel_err"] for row in rows if row.get("slope_rel_err") is not None]
    intercepts = [
        row["intercept_err_range"] for row in rows if row.get("intercept_err_range") is not None
    ]
    return {
        "n": n,
        "n_correct": correct,
        "accuracy": (correct / n) if n else None,
        "failure_reasons": reasons,
        "n_with_parameter_fit": len(slopes),
        "median_slope_rel_err": float(np.median(slopes)) if slopes else None,
        "median_intercept_err_range": float(np.median(intercepts)) if intercepts else None,
    }


def _bridge_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    viewed: list[dict[str, Any]] = []
    for row in rows:
        bridge = row.get("with_bridge")
        if isinstance(bridge, dict):
            viewed.append({**row, **bridge})
        else:
            viewed.append(row)
    return viewed


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Real-figure results (owid-grapher-v1)",
        "",
        f"Commit `{payload['commit']}`. Python {payload['python']}.",
        "",
        "Strict scoring drops every flagged point, including occlusion bridges. With-bridge scoring keeps points flagged `INTERPOLATED` and still drops every other flag. A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90.",
        "",
        "| split | n | strict | strict accuracy | with-bridge | with-bridge accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("dev", "held-out", "all"):
        block = payload["summary"][name]
        bridged = payload["summary_with_bridge"][name]
        acc = "n/a" if block["accuracy"] is None else f"{block['accuracy'] * 100:.2f}%"
        bacc = "n/a" if bridged["accuracy"] is None else f"{bridged['accuracy'] * 100:.2f}%"
        lines.append(
            f"| {name} | {block['n']} | {block['n_correct']} | {acc} | {bridged['n_correct']} | {bacc} |"
        )
    lines.extend(
        [
            "",
            f"Mean CPU time {payload['runtime_s_mean']:.3f}s/image. Bridged points: {payload['bridged_count']}.",
            "",
            "Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:",
            "",
        ]
    )
    for name in ("dev", "held-out", "all"):
        block = payload["summary"][name]
        lines.append(
            f"- {name}: n_fit={block['n_with_parameter_fit']}, "
            f"median |Δslope|/|slope|={_fmt(block['median_slope_rel_err'])}, "
            f"median |Δintercept|/range={_fmt(block['median_intercept_err_range'])}"
        )
    lines.extend(["", "## Per figure", ""])
    lines.append(
        "| slug | split | strict | reason | bridge | bridge reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | bridge NRMSE % | bridge x-coverage | bridged | license | url |"
    )
    lines.append("|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for row in payload["figures"]:
        bridge = row.get("with_bridge") or {}
        lines.append(
            "| {slug} | {split} | {correct} | {reason} | {bcorrect} | {breason} | {n_gt} | {n_pred} | {nrmse} | {cov} | {bnrmse} | {bcov} | {bridged} | {license} | {url} |".format(
                slug=row["slug"],
                split=row["split"],
                correct="yes" if row["correct"] else "no",
                reason=row["reason"],
                bcorrect="yes" if bridge.get("correct") else "no",
                breason=bridge.get("reason", row["reason"]),
                n_gt=row["n_gt"],
                n_pred=row["n_pred"],
                nrmse=_fmt(row.get("worst_nrmse")),
                cov=_fmt(row.get("worst_coverage")),
                bnrmse=_fmt(bridge.get("worst_nrmse")),
                bcov=_fmt(bridge.get("worst_coverage")),
                bridged=row.get("bridged_count", 0),
                license=row["license"],
                url=row["source_url"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "held-out", "all"), default="all")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args()
    manifest = json.loads((REAL / "manifest.json").read_text(encoding="utf-8"))
    selected = [
        item for item in manifest["figures"] if args.split == "all" or item["split"] == args.split
    ]
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        slug = item["slug"]
        row = _one(REAL / "gt" / f"{slug}.json", REAL / "figures" / f"{slug}.png")
        rows.append(row)
        bridge = row.get("with_bridge") or {}
        print(
            f"{index:3d}/{len(selected)} {row['split']:8s} "
            f"{'OK' if row['correct'] else 'FAIL':4s} {row['reason']:20s} "
            f"bridge={'OK' if bridge.get('correct') else 'FAIL':4s} {bridge.get('reason', ''):20s} {slug}",
            flush=True,
        )
    dev_rows = [row for row in rows if row["split"] == "dev"]
    held_rows = [row for row in rows if row["split"] == "held-out"]
    runtimes = [float(row["runtime_s"]) for row in rows]
    payload = {
        "dataset": manifest["dataset"],
        "commit": _git_sha(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "split_requested": args.split,
        "split_rule": manifest["split_rule"],
        "runtime_s_mean": float(np.mean(runtimes)) if runtimes else None,
        "runtime_s_median": float(np.median(runtimes)) if runtimes else None,
        "bridged_count": int(sum(int(row.get("bridged_count") or 0) for row in rows)),
        "summary": {
            "dev": _rate(dev_rows),
            "held-out": _rate(held_rows),
            "all": _rate(rows),
        },
        "summary_with_bridge": {
            "dev": _rate(_bridge_rows(dev_rows)),
            "held-out": _rate(_bridge_rows(held_rows)),
            "all": _rate(_bridge_rows(rows)),
        },
        "figures": rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    tag = "real-v1" if args.split == "all" else f"real-v1-{args.split}"
    (args.out / f"{tag}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.out / f"{tag}.md").write_text(_markdown(payload), encoding="utf-8")
    summary = payload["summary"]
    print(json.dumps({name: summary[name] for name in summary}, indent=2))


if __name__ == "__main__":
    main()
