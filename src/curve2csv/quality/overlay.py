"""QA overlay: desaturated source, extracted marks, gaps, and a short status bar."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from curve2csv.types import (
    Abstain,
    AxisCalibration,
    ExtractionResult,
    PlotArea,
    PointFlag,
)


def render_overlay(result: ExtractionResult) -> np.ndarray:
    rgb = result.source.rgb
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] *= 0.35
    faded = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    white = np.full_like(faded, 255)
    base = cv2.addWeighted(faded, 0.6, white, 0.4, 0.0)
    canvas = base.copy()
    if isinstance(result.plot_area, PlotArea):
        x0, y0, x1, y1 = result.plot_area.bbox
        cv2.rectangle(canvas, (x0, y0), (x1, y1), (20, 20, 20), 1)
    from curve2csv import __version__

    palette = (
        (31, 119, 180),
        (255, 127, 14),
        (44, 160, 44),
        (214, 39, 40),
        (148, 103, 189),
        (140, 86, 75),
    )
    for index, series in enumerate(result.series):
        color = palette[index % len(palette)]
        previous: tuple[float, float] | None = None
        for point in series.points:
            cx, cy = int(round(point.px)), int(round(point.py))
            emitted = (
                point.x is not None
                and point.y is not None
                and PointFlag.LOW_CONFIDENCE not in point.flags
            )
            bridged = PointFlag.INTERPOLATED in point.flags
            if bridged and emitted:
                if (
                    previous is not None
                    and abs(point.px - previous[0]) <= 3.5
                    and int(round(point.px)) % 2 == 0
                ):
                    cv2.line(
                        canvas,
                        (int(round(previous[0])), int(round(previous[1]))),
                        (cx, cy),
                        (170, 20, 170),
                        1,
                        cv2.LINE_AA,
                    )
                cv2.rectangle(canvas, (cx - 3, cy - 3), (cx + 3, cy + 3), (170, 20, 170), 1)
                previous = (point.px, point.py)
                continue
            if (
                series.kind == "line"
                and emitted
                and previous is not None
                and abs(point.px - previous[0]) <= 3.5
            ):
                cv2.line(
                    canvas,
                    (int(round(previous[0])), int(round(previous[1]))),
                    (cx, cy),
                    color,
                    1,
                    cv2.LINE_AA,
                )
            if emitted:
                cv2.circle(canvas, (cx, cy), 2, color, -1, cv2.LINE_AA)
                previous = (point.px, point.py)
            else:
                cv2.circle(canvas, (cx, cy), 3, (220, 30, 30), 1, cv2.LINE_AA)
                previous = None
        if isinstance(result.plot_area, PlotArea) and series.kind == "line":
            x_cal = result.calibration.get("x")
            y0b = result.plot_area.bbox[3]
            if isinstance(x_cal, AxisCalibration):
                for lo, hi in series.gaps:
                    c0 = float(x_cal.data_to_px(np.asarray([lo], dtype=np.float64))[0])
                    c1 = float(x_cal.data_to_px(np.asarray([hi], dtype=np.float64))[0])
                    a, b = sorted((int(round(c0)), int(round(c1))))
                    cv2.line(canvas, (a, y0b + 4), (b, y0b + 4), (220, 30, 30), 2)
    bar_h = 64
    bar = np.full((bar_h, canvas.shape[1], 3), 250, np.uint8)
    lines = [
        f"curve2csv {__version__}  series={len(result.series)}  conf={result.image_confidence:.2f}",
    ]
    for key in ("x", "y"):
        cal = result.calibration.get(key)
        if isinstance(cal, AxisCalibration):
            lines.append(
                f"{key}: residual {cal.residual_rel:.2e} n={cal.n_ticks_used} src={cal.source}"
            )
        elif isinstance(cal, Abstain):
            lines.append(f"{key}: abstain {cal.reason}")
    for series in result.series[:3]:
        lines.append(
            f"{series.series_id} {series.kind} {series.color_hex or ''} cov={series.coverage:.2f} conf={series.confidence:.2f}"
        )
    y_text = 16
    for line in lines[:4]:
        cv2.putText(
            bar,
            line[:110],
            (8, y_text),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
        y_text += 14
    return np.vstack([canvas, bar])


def write_overlay(result: ExtractionResult, path: Path) -> None:
    image = render_overlay(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(path), bgr)
    if not ok:
        raise OSError(f"could not write overlay: {path}")
