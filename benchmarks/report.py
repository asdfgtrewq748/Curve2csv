"""Render a benchmark JSON file as a Markdown category table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render(report: dict[str, Any]) -> str:
    aggregates = report["aggregates"]
    lines = [
        f"# {report.get('tag')} ({report.get('split')})",
        "",
        f"- dataset: `{report.get('dataset_version')}`",
        f"- seed: `{report.get('global_seed')}`",
        f"- python: `{report.get('python')}`",
        f"- platform: `{report.get('platform')}`",
        f"- n: {report.get('n')}",
        "",
        "| category | n | plot_area_iou (med) | axis_calib_rel_err % (med) | curve_nrmse_range % (med / P90) | x_coverage (med) | false_point_rate % | series_match_acc | scatter_f1@3px | fabrication_count |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    categories = aggregates.get("categories", {})
    # Lead with the chart × degradation × bucket rows. Shape rows follow.
    bucket_rows = []
    shape_rows = []
    for key, row in categories.items():
        parts = str(key).split("/")
        target = bucket_rows if len(parts) == 3 and parts[2] in {"1", "2-3", "4+"} else shape_rows
        target.append((key, row))
    for key, row in bucket_rows + shape_rows:
        nrmse = _fmt(row.get("curve_nrmse_median"))
        p90 = _fmt(row.get("curve_nrmse_p90"))
        err = row.get("axis_calib_rel_err_median")
        err_pct = None if err is None else float(err) * 100.0
        false_rate = row.get("false_point_rate_median")
        false_pct = None if false_rate is None else float(false_rate) * 100.0
        lines.append(
            "| {cat} | {n} | {iou} | {err} | {nrmse} / {p90} | {cov} | {fp} | {match} | {f1} | {fab} |".format(
                cat=key,
                n=row.get("n"),
                iou=_fmt(row.get("plot_area_iou_median")),
                err=_fmt(err_pct),
                nrmse=nrmse,
                p90=p90,
                cov=_fmt(row.get("x_coverage_median")),
                fp=_fmt(false_pct),
                match=_fmt(row.get("series_match_acc")),
                f1=_fmt(row.get("scatter_f1_median")),
                fab=row.get("fabrication_count"),
            )
        )
    lines.extend(
        ["", "## Gates", "", "| gate | measured | op | target | pass |", "|---|---|---|---|---|"]
    )
    for name, gate in report.get("gates", {}).items():
        lines.append(
            f"| {name} | {_fmt(gate.get('measured'), 6)} | {gate.get('op')} | {gate.get('target')} | {'PASS' if gate.get('pass') else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Report-only",
            "",
            f"- flag_auroc: {_fmt(aggregates.get('flag_auroc'), 4)}",
            f"- flag_precision: {_fmt(aggregates.get('flag_precision'), 4)}",
            f"- flag_recall: {_fmt(aggregates.get('flag_recall'), 4)}",
            f"- ece: {_fmt(aggregates.get('ece'), 4)}",
            f"- runtime_s_median: {_fmt(aggregates.get('runtime_s_median'), 4)}",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="benchmarks.report")
    parser.add_argument("result", type=Path)
    args = parser.parse_args(argv)
    report = json.loads(args.result.read_text(encoding="utf-8"))
    print(render(report))


if __name__ == "__main__":
    main()
