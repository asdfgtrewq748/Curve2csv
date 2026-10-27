"""CSV and JSON writers. CSV abstentions are empty fields, never interpolated numbers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from curve2csv.types import (
    SCHEMA_VERSION,
    Abstain,
    AxisCalibration,
    ExtractionResult,
    PlotArea,
    PointFlag,
    flag_names,
)

CSV_COLUMNS = (
    "series_id",
    "series_label",
    "kind",
    "x",
    "y",
    "confidence",
    "flags",
    "px",
    "py",
    "interpolated",
)

DISCLAIMER = "Values digitized from a published figure; not original measurements."


def _num(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return ""
    return format(float(value), ".10g")


def write_csv(result: ExtractionResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(CSV_COLUMNS)]
    for series in result.series:
        label = series.label or ""
        for point in series.points:
            fields = [
                series.series_id,
                label,
                series.kind,
                _num(point.x),
                _num(point.y),
                _num(point.confidence),
                "|".join(flag_names(point.flags)),
                _num(point.px),
                _num(point.py),
                "1" if PointFlag.INTERPOLATED in point.flags else "0",
            ]
            lines.append(",".join(fields))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _calib_dict(cal: AxisCalibration) -> dict[str, object]:
    return {
        "scale": cal.scale.value,
        "inverted": cal.inverted,
        "a": cal.a,
        "b": cal.b,
        "residual_rel": cal.residual_rel,
        "n_ticks_used": cal.n_ticks_used,
        "source": cal.source,
        "dir": [cal.dir_x, cal.dir_y],
    }


def result_document(
    result: ExtractionResult, *, overlay_name: str | None = None
) -> dict[str, object]:
    if isinstance(result.plot_area, PlotArea):
        plot: dict[str, object] | None = {
            "bbox": list(result.plot_area.bbox),
            "x_axis_px": result.plot_area.x_axis_px,
            "y_axis_px": result.plot_area.y_axis_px,
            "score": result.plot_area.score,
        }
    else:
        plot = None
    axes: dict[str, object] = {}
    for name, cal in result.calibration.items():
        if isinstance(cal, AxisCalibration):
            axes[name] = _calib_dict(cal)
        else:
            axes[name] = {"abstain": True, "stage": cal.stage, "reason": cal.reason}
    series_docs: list[dict[str, object]] = []
    for series in result.series:
        series_docs.append(
            {
                "series_id": series.series_id,
                "label": series.label,
                "kind": series.kind,
                "color_hex": series.color_hex,
                "style": series.style,
                "confidence": series.confidence,
                "coverage": series.coverage,
                "gaps": [[lo, hi] for lo, hi in series.gaps],
                "points": [
                    {
                        "x": point.x,
                        "y": point.y,
                        "px": point.px,
                        "py": point.py,
                        "confidence": point.confidence,
                        "flags": flag_names(point.flags),
                        "interpolated": 1 if PointFlag.INTERPOLATED in point.flags else 0,
                    }
                    for point in series.points
                ],
            }
        )
    from curve2csv import __version__

    metrics = result.metrics()
    source_name = Path(result.source.source).name if result.source.source != "memory" else None
    document: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "curve2csv", "version": __version__, "config_hash": result.config_hash},
        "source": {
            "path": result.source.source,
            "sha256": result.source.sha256,
            "page": result.source.page,
            "width": result.source.width,
            "height": result.source.height,
            "dpi": result.source.dpi,
        },
        "data_origin": "digitized_from_figure",
        "disclaimer": DISCLAIMER,
        "plot_area": plot,
        "axes": axes,
        "series": series_docs,
        "image_confidence": result.image_confidence,
        "abstentions": [
            {"stage": item.stage, "reason": item.reason} for item in result.abstentions
        ],
        "qa": {
            "overlay": overlay_name
            or (f"{source_name}.overlay.png" if source_name else "overlay.png"),
            "metrics": metrics,
        },
        "diagnostics": _jsonable(result.diagnostics),
    }
    return document


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value
    if isinstance(value, Abstain):
        return {"stage": value.stage, "reason": value.reason}
    return str(value)


def write_json(result: ExtractionResult, path: Path, *, overlay_name: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = result_document(result, overlay_name=overlay_name)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def write_metrics(result: ExtractionResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.metrics()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def export_all(result: ExtractionResult, out_dir: Path, stem: str | None = None) -> dict[str, Path]:
    """Write the four artifacts: CSV, JSON, overlay PNG, and metrics JSON."""

    out_dir.mkdir(parents=True, exist_ok=True)
    if stem is None:
        source = Path(result.source.source)
        stem = source.stem if result.source.source != "memory" else "extraction"
    csv_path = out_dir / f"{stem}.csv"
    json_path = out_dir / f"{stem}.json"
    overlay_path = out_dir / f"{stem}.overlay.png"
    metrics_path = out_dir / f"{stem}.metrics.json"
    write_csv(result, csv_path)
    write_json(result, json_path, overlay_name=overlay_path.name)
    result.overlay(overlay_path)
    write_metrics(result, metrics_path)
    return {"csv": csv_path, "json": json_path, "overlay": overlay_path, "metrics": metrics_path}
