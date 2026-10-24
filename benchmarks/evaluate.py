"""Run the pipeline on a generated split and write gate results."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import time
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from benchmarks.metrics import aggregate, evaluate_gates, regression_failures, score_sample
from curve2csv.api import extract
from curve2csv.types import AxesOverride, TickInput


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid config: {path}")
    return payload


def _axes(document: dict[str, Any]) -> AxesOverride:
    axes = document["axes"]

    def ticks(name: str) -> tuple[TickInput, ...]:
        return tuple(
            TickInput(px=float(item["px"]), py=float(item["py"]), value=float(item["value"]))
            for item in axes[name]["ticks"]
        )

    return AxesOverride(x_ticks=ticks("x"), y_ticks=ticks("y"), source="sidecar")


def _schema() -> dict[str, Any]:
    import curve2csv

    path = Path(curve2csv.__file__).resolve().parent / "schema" / "result.schema.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("result schema is not an object")
    return payload


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in row.items():
        if key in {"point_confidence", "point_error", "point_flagged"}:
            continue
        if hasattr(value, "item"):
            clean[key] = value.item()
        else:
            clean[key] = value
    return clean


def _summary_jsonable(summary: dict[str, Any]) -> dict[str, Any]:
    encoded = json.loads(json.dumps(summary, default=_default))
    if not isinstance(encoded, dict):
        raise SystemExit("summary was not a dict")
    return encoded


def _default(value: object) -> object:
    if hasattr(value, "item"):
        return value.item()  # type: ignore[no-any-return]
    raise TypeError(type(value).__name__)


def evaluate_split(
    config: dict[str, Any],
    data_root: Path,
    split: str,
    out_dir: Path,
    tag: str,
) -> dict[str, Any]:
    count = int(config["splits"][split])
    schema = _schema()
    rows: list[dict[str, Any]] = []
    failures_dir = out_dir / f"{tag}_failures"
    failures_dir.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        sample_dir = data_root / split / f"{index:05d}"
        document = json.loads((sample_dir / "gt.json").read_text(encoding="utf-8"))
        started = time.perf_counter()
        result = extract(sample_dir / "img.png", axes=_axes(document), out=sample_dir / "pred")
        elapsed = time.perf_counter() - started
        row = score_sample(document, result, elapsed)
        pred_dir = sample_dir / "pred"
        files = [
            pred_dir / name
            for name in ("img.csv", "img.json", "img.overlay.png", "img.metrics.json")
        ]
        complete = all(path.is_file() and path.stat().st_size > 0 for path in files)
        if complete:
            try:
                payload = json.loads(files[1].read_text(encoding="utf-8"))
                jsonschema.validate(payload, schema)
            except (json.JSONDecodeError, jsonschema.ValidationError):
                complete = False
        row["completeness"] = 1.0 if complete else 0.0
        rows.append(row)
        if (index + 1) % 25 == 0 or index + 1 == count:
            print(f"evaluated {split} {index + 1}/{count}", flush=True)
    summary = aggregate(rows)
    gates = evaluate_gates(summary, config.get("gates", {}))
    # Keep the worst line samples' overlays for the report.
    ranked = sorted(
        rows,
        key=lambda row: float(
            row["curve_nrmse_range"] if row["curve_nrmse_range"] is not None else -1.0
        ),
        reverse=True,
    )
    copied = 0
    for row in ranked:
        if copied >= 20:
            break
        if row["chart_type"] not in {"line", "line+marker"}:
            continue
        sample_id = str(row["id"])
        # id is "{split}_{index:05d}"
        index = int(sample_id.split("_")[-1])
        overlay = data_root / split / f"{index:05d}" / "pred" / "img.overlay.png"
        if overlay.is_file():
            shutil.copyfile(overlay, failures_dir / f"{sample_id}.overlay.png")
            copied += 1
    public_rows = [_jsonable(row) for row in rows]
    public_summary = _summary_jsonable(summary)
    # Drop numpy-heavy category values already encoded.
    report = {
        "tag": tag,
        "split": split,
        "dataset_version": config.get("dataset_version"),
        "global_seed": config.get("global_seed"),
        "n": count,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "aggregates": public_summary,
        "gates": gates,
        "per_sample": public_rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{tag}.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
    hard_fail = [name for name, gate in gates.items() if gate.get("hard") and not gate.get("pass")]
    if hard_fail:
        print("HARD GATE FAIL:", ", ".join(hard_fail))
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="benchmarks.evaluate")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--write-baseline", type=Path, default=None)
    args = parser.parse_args(argv)
    config = _load_yaml(args.config)
    report = evaluate_split(config, args.data, args.split, args.out, args.tag)
    summary = report["aggregates"]
    if args.write_baseline is not None:
        metrics = config.get("regression", {}).get("metrics", [])
        payload = {"split": args.split, "metrics": {name: summary.get(name) for name in metrics}}
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote baseline {args.write_baseline}")
    failed = False
    for name, gate in report["gates"].items():
        if gate.get("hard") and not gate.get("pass"):
            failed = True
            print(f"FAIL {name}: measured {gate.get('measured')}")
    if args.baseline is not None and args.baseline.is_file():
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        regression = config.get("regression", {})
        problems = regression_failures(
            summary,
            baseline,
            metrics=list(regression.get("metrics", [])),
            relative=float(regression.get("relative", 0.10)),
            margin_fraction=float(regression.get("margin_fraction", 0.50)),
            gates=config.get("gates", {}),
        )
        for problem in problems:
            print("REGRESSION", problem)
            failed = True
        if not problems:
            print("smoke regression: ok")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
