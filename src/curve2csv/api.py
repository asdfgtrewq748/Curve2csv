"""Public ``extract`` entry point and small human-confirm operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

from curve2csv.calibrate.limits import axes_from_box
from curve2csv.config import PipelineConfig
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.errors import InputError
from curve2csv.io.export import export_all
from curve2csv.io.image import load_image
from curve2csv.pipeline import run_pipeline
from curve2csv.quality.coverage import series_coverage
from curve2csv.quality.flags import assign_segment_ids
from curve2csv.types import (
    Abstain,
    AxesOverride,
    AxisCalibration,
    AxisScale,
    BBox,
    ExtractionResult,
    PlotArea,
    PointFlag,
    Series,
)


def _manual_area(bbox: BBox | tuple[float, float, float, float], *, source: str) -> PlotArea:
    x0, y0, x1, y1 = (int(round(float(value))) for value in bbox)
    if x1 <= x0 or y1 <= y0:
        raise InputError("plot box needs x1 > x0 and y1 > y0")
    if x0 < 0 or y0 < 0:
        raise InputError("plot box starts outside the image")
    return PlotArea(
        bbox=(x0, y0, x1, y1),
        x_axis_px=float(y1),
        y_axis_px=float(x0),
        score=1.0,
        corners=(
            (float(x0), float(y0)),
            (float(x1), float(y0)),
            (float(x1), float(y1)),
            (float(x0), float(y1)),
        ),
        source=source,
    )


def _export(result: ExtractionResult, out: str | Path | None) -> ExtractionResult:
    if out is not None:
        export_all(result, Path(out))
    return result


def _calibrated(result: ExtractionResult) -> bool:
    return all(isinstance(result.calibration.get(name), AxisCalibration) for name in ("x", "y"))


def extract(
    src: str | Path | NDArray[np.uint8],
    *,
    axes: AxesOverride | None = None,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
    plot_box: BBox | None = None,
) -> ExtractionResult:
    """Digitize one figure.

    When ``out`` is set, CSV, JSON, an overlay PNG, and a metrics file are written
    together. Passing no ``axes`` abstains from calibration (M1 does not read tick
    labels) and returns an empty series list rather than guessing values.
    ``plot_box`` confirms the plot rectangle manually and skips spine detection.
    """

    loaded = load_image(src)
    area = _manual_area(plot_box, source="manual:plot_box") if plot_box is not None else None
    result = run_pipeline(loaded, axes=axes, config=config, plot_area_override=area)
    return _export(result, out)


def extract_with_limits(
    src: str | Path | NDArray[np.uint8],
    *,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    x_scale: AxisScale = AxisScale.LINEAR,
    y_scale: AxisScale = AxisScale.LINEAR,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
    plot_box: BBox | None = None,
) -> ExtractionResult:
    """Digitize using the detected (or confirmed) plot box and typed axis endpoints."""

    loaded = load_image(src)
    area = (
        _manual_area(plot_box, source="manual:plot_box")
        if plot_box is not None
        else detect_plot_area(loaded.rgb, config)
    )
    if isinstance(area, Abstain):
        raise InputError(f"plot area: {area.reason}")
    axes = axes_from_box(
        area.bbox,
        xmin=xmin,
        xmax=xmax,
        ymin=ymin,
        ymax=ymax,
        x_scale=x_scale,
        y_scale=y_scale,
    )
    result = run_pipeline(loaded, axes=axes, config=config, plot_area_override=area)
    return _export(result, out)


def confirm_plot_box(
    result: ExtractionResult,
    bbox: BBox | tuple[float, float, float, float],
    *,
    axes: AxesOverride | None = None,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Re-extract with a confirmed plot rectangle.

    A calibrated ``result`` keeps its x/y calibration unless ``axes`` is given,
    so confirming a box does not silently change the axis values. The new
    plot-area source is recorded as ``manual:plot_box``.
    """

    area = _manual_area(bbox, source="manual:plot_box")
    if area.bbox[2] > result.source.width or area.bbox[3] > result.source.height:
        raise InputError("plot box ends outside the image")
    calibration = None
    if axes is None and _calibrated(result):
        calibration = dict(result.calibration)
    rerun = run_pipeline(
        result.source,
        axes=axes,
        config=config,
        plot_area_override=area,
        calibration_override=calibration,
    )
    return _export(rerun, out)


def confirm_axis_calibration(
    result: ExtractionResult,
    axes: AxesOverride,
    *,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Re-extract with confirmed tick pairs, keeping a confirmed plot box."""

    area = result.plot_area if isinstance(result.plot_area, PlotArea) else None
    rerun = run_pipeline(
        result.source,
        axes=axes,
        config=config,
        plot_area_override=area,
    )
    return _export(rerun, out)


def pick_series(
    result: ExtractionResult,
    stroke: tuple[float, float] | Sequence[tuple[float, float]],
    *,
    radius: float = 8.0,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Keep the series touched by a click or a short pixel stroke.

    A single click keeps only the nearest touched series. A stroke keeps every
    series with a point within ``radius`` pixels of any stroke sample. No point
    is added or moved.
    """

    if (
        isinstance(stroke, tuple)
        and len(stroke) == 2
        and all(isinstance(value, int | float) for value in stroke)
    ):
        first, second = cast(tuple[float, float], stroke)
        samples = [(float(first), float(second))]
    else:
        samples = [(float(x), float(y)) for x, y in cast(Sequence[tuple[float, float]], stroke)]
    if not samples:
        raise InputError("click or stroke is empty")

    scored: list[tuple[float, Series]] = []
    for series in result.series:
        if not series.points:
            continue
        pixels = np.asarray([[point.px, point.py] for point in series.points], dtype=np.float64)
        query = np.asarray(samples, dtype=np.float64)
        distance = np.hypot(
            pixels[:, None, 0] - query[None, :, 0],
            pixels[:, None, 1] - query[None, :, 1],
        )
        scored.append((float(distance.min()), series))
    if not scored:
        raise InputError("result has no series to pick")
    nearest = min(score for score, _series in scored)
    if nearest > radius:
        raise InputError(f"no series within {radius:g}px of the click")
    if len(samples) == 1:
        selected = [series for score, series in scored if score == nearest]
    else:
        selected = [series for score, series in scored if score <= radius]
    return _export(replace(result, series=selected), out)


def _merge_gaps(gaps: list[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted((float(lo), float(hi)) for lo, hi in gaps if hi > lo)
    merged: list[tuple[float, float]] = []
    for lo, hi in ordered:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))
    return merged


def clear_range(
    result: ExtractionResult,
    x_min: float,
    x_max: float,
    *,
    series_id: str | None = None,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Force one x range empty. Cleared points stay as evidence, never interpolate.

    Coordinates become ``None`` and the point gets ``MANUAL``; any
    ``INTERPOLATED`` bit in the cleared range is removed. The range is added to
    ``series.gaps`` and coverage is recomputed from the remaining emitted x.
    """

    lo, hi = sorted((float(x_min), float(x_max)))
    if not hi > lo:
        raise InputError("clear range needs x_max > x_min")
    if series_id is not None and not any(item.series_id == series_id for item in result.series):
        raise InputError(f"no series with id {series_id}")

    changed: list[Series] = []
    for series in result.series:
        if series_id is not None and series.series_id != series_id:
            changed.append(series)
            continue
        points = []
        for point in series.points:
            data_x = point.x
            if data_x is None:
                mapped = result.pixel_to_data(point.px, point.py)
                data_x = None if mapped is None else mapped[0]
            if data_x is not None and lo <= float(data_x) <= hi:
                flags = (point.flags | PointFlag.MANUAL) & ~PointFlag.INTERPOLATED
                points.append(replace(point, x=None, y=None, flags=flags))
            else:
                points.append(point)
        gaps = _merge_gaps([*series.gaps, (lo, hi)])
        updated = replace(series, points=points, gaps=gaps)
        updated.coverage = series_coverage(updated)
        changed.append(updated)
    changed = assign_segment_ids(changed)
    return _export(replace(result, series=changed), out)
