"""On-device entry points for the Android app.

Tick-label OCR is not bundled. Chaquopy has no Android wheel for
onnxruntime, which RapidOCR and the learned segmenter need, so the reader
types the axis endpoints and series separation stays on the rule-based path.
Geometry and the CSV export are the same Python core as the desktop package.
"""

from __future__ import annotations

import json

from curve2csv.api import extract_with_limits
from curve2csv.errors import InputError
from curve2csv.types import AxisScale


def digitize(
    image_path: str,
    out_dir: str,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    x_log: bool,
    y_log: bool,
) -> str:
    try:
        result = extract_with_limits(
            image_path,
            xmin=float(xmin),
            xmax=float(xmax),
            ymin=float(ymin),
            ymax=float(ymax),
            x_scale=AxisScale.LOG10 if x_log else AxisScale.LINEAR,
            y_scale=AxisScale.LOG10 if y_log else AxisScale.LINEAR,
            out=out_dir,
        )
    except InputError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    stem = result.source.source.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    points = sum(len(series.points) for series in result.series)
    return json.dumps(
        {
            "ok": True,
            "csv": f"{out_dir}/{stem}.csv",
            "overlay": f"{out_dir}/{stem}.overlay.png",
            "n_series": len(result.series),
            "n_points": points,
            "abstain": [item.reason for item in result.abstentions],
        }
    )
