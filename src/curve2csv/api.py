"""Public ``extract`` entry point and small human-confirm operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

from curve2csv.calibrate.limits import axes_from_box
from curve2csv.color_math import deltaE_ciede2000, rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.errors import InputError
from curve2csv.io.export import export_all
from curve2csv.io.image import load_image
from curve2csv.pipeline import run_pipeline
from curve2csv.quality.coverage import series_coverage
from curve2csv.quality.flags import assign_segment_ids
from curve2csv.separate.color import lab_to_hex
from curve2csv.types import (
    Abstain,
    AxesOverride,
    AxisCalibration,
    AxisScale,
    BBox,
    DataPoint,
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


def _hex_to_lab(color_hex: str) -> np.ndarray | None:
    text = color_hex.strip().lstrip("#")
    if len(text) != 6:
        return None
    try:
        rgb = np.asarray(
            [[[int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)]]],
            dtype=np.uint8,
        )
    except ValueError:
        return None
    return np.asarray(rgb2lab(rgb)[0, 0], dtype=np.float64)


def _subtract_gaps(
    gaps: list[tuple[float, float]], lo: float, hi: float
) -> list[tuple[float, float]]:
    remaining: list[tuple[float, float]] = []
    for glo, ghi in gaps:
        if hi <= glo or lo >= ghi:
            remaining.append((glo, ghi))
        else:
            if glo < lo:
                remaining.append((glo, lo))
            if ghi > hi:
                remaining.append((hi, ghi))
    return _merge_gaps(remaining)


def trace_stroke(
    result: ExtractionResult,
    stroke: Sequence[tuple[float, float]],
    *,
    series_id: str | None = None,
    radius: float = 10.0,
    snap_series_px: float = 16.0,
    bridge: bool = False,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Trace and snap to real curve ink guided by human-provided stroke points.

    Strictly obeys 'abstain over fabricate': only columns with real ink matching
    the target color (or dark ink) within ``radius`` pixels of the stroke guide
    are emitted as data points. Emitted points receive ``PointFlag.MANUAL``
    (with status="ok"). Missing ink columns are left empty unless ``bridge=True``
    is explicitly requested for short gaps.
    """

    if radius <= 0:
        raise InputError("radius must be positive")
    samples = [(float(x), float(y)) for x, y in stroke]
    if len(samples) < 2:
        raise InputError("trace_stroke requires at least 2 stroke points")
    if not isinstance(result.plot_area, PlotArea):
        raise InputError("result has no valid plot area")
    if not _calibrated(result):
        raise InputError("result is not calibrated")

    area = result.plot_area
    x0, y0, x1, y1 = area.bbox

    # Target series determination
    target_series: Series | None = None
    if series_id is not None:
        target_series = next((s for s in result.series if s.series_id == series_id), None)
        if target_series is None:
            raise InputError(f"no series with id {series_id}")
    else:
        best_dist = float("inf")
        closest_s: Series | None = None
        stroke_pts = np.asarray(samples, dtype=np.float64)
        for s in result.series:
            valid_pts = [p for p in s.points if p.x is not None and p.y is not None]
            if not valid_pts:
                continue
            s_pix = np.asarray([[p.px, p.py] for p in valid_pts], dtype=np.float64)
            dists = np.hypot(
                stroke_pts[:, None, 0] - s_pix[None, :, 0],
                stroke_pts[:, None, 1] - s_pix[None, :, 1],
            )
            min_d = float(np.min(dists))
            if min_d < best_dist:
                best_dist = min_d
                closest_s = s
        if closest_s is not None and best_dist <= snap_series_px:
            target_series = closest_s

    # Stroke interpolation function y_guide(c)
    xs = np.asarray([p[0] for p in samples], dtype=np.float64)
    ys = np.asarray([p[1] for p in samples], dtype=np.float64)
    order = np.argsort(xs)
    s_xs = xs[order]
    s_ys = ys[order]
    ux, uidx = np.unique(s_xs, return_index=True)
    uy = s_ys[uidx]
    if len(ux) < 2:
        raise InputError("stroke needs at least two distinct x coordinates")

    c_min = max(x0, int(np.floor(float(ux[0]))))
    c_max = min(x1 - 1, int(np.ceil(float(ux[-1]))))
    if c_max < c_min:
        return _export(result, out)

    rgb = result.source.rgb
    lab_img = rgb2lab(rgb)
    gray = np.mean(rgb.astype(np.float64), axis=2)
    bg_q75 = float(np.percentile(gray[y0:y1, x0:x1], 75))

    # Target color determination
    target_lab: np.ndarray | None = None
    is_achromatic = True
    if target_series is not None and target_series.color_hex is not None:
        target_lab = _hex_to_lab(target_series.color_hex)
        if target_lab is not None:
            chroma = float(np.hypot(target_lab[1], target_lab[2]))
            is_achromatic = chroma < 12.0

    if target_lab is None:
        sampled_pixels = []
        for sx, sy in samples:
            cx, cy = int(round(sx)), int(round(sy))
            rw0, rw1 = max(0, cy - int(radius)), min(rgb.shape[0], cy + int(radius) + 1)
            cw0, cw1 = max(0, cx - int(radius)), min(rgb.shape[1], cx + int(radius) + 1)
            if rw1 > rw0 and cw1 > cw0:
                patch_gray = gray[rw0:rw1, cw0:cw1]
                patch_lab = lab_img[rw0:rw1, cw0:cw1]
                dark = patch_gray < min(215.0, bg_q75 - 15.0)
                if np.any(dark):
                    sampled_pixels.append(patch_lab[dark])
        if sampled_pixels:
            all_sampled = np.concatenate(sampled_pixels, axis=0)
            target_lab = np.median(all_sampled, axis=0)
            chroma = float(np.hypot(target_lab[1], target_lab[2]))
            is_achromatic = chroma < 12.0

    # Column-by-column tracing
    traced_by_col: dict[int, DataPoint] = {}
    prev_py: float | None = None

    for col in range(c_min, c_max + 1):
        col_x = float(col) + 0.5
        guide_y = float(np.interp(col_x, ux, uy))
        r_start = max(y0, int(np.floor(guide_y - radius)))
        r_end = min(y1, int(np.ceil(guide_y + radius)) + 1)
        if r_end <= r_start:
            continue

        strip_lab = lab_img[r_start:r_end, col]
        strip_gray = gray[r_start:r_end, col]

        if not is_achromatic and target_lab is not None:
            de = deltaE_ciede2000(strip_lab, target_lab)
            ink_mask = (de <= 18.0) & (strip_gray < 235.0)
            if np.any(ink_mask):
                weights = np.maximum(0.0, 18.0 - de[ink_mask]) + 1e-3
            else:
                ink_mask = np.zeros(strip_gray.shape, dtype=bool)
                weights = np.zeros(0, dtype=np.float64)
        else:
            ink_mask = strip_gray < min(215.0, bg_q75 - 18.0)
            if np.any(ink_mask):
                weights = np.maximum(0.0, 255.0 - strip_gray[ink_mask]) + 1e-3
            else:
                ink_mask = np.zeros(strip_gray.shape, dtype=bool)
                weights = np.zeros(0, dtype=np.float64)

        if not np.any(ink_mask):
            prev_py = None
            continue

        matching_rows = np.arange(r_start, r_end)[ink_mask]
        ref_y = prev_py if prev_py is not None else guide_y

        diffs = np.diff(matching_rows)
        split_indices = np.where(diffs > 1)[0] + 1
        runs = np.split(matching_rows, split_indices)
        weights_split = np.split(weights, split_indices)

        best_idx = int(np.argmin([abs(float(np.mean(r)) - ref_y) for r in runs]))
        best_run = runs[best_idx]
        best_weights = weights_split[best_idx]

        py_centroid = float(np.average(best_run.astype(np.float64) + 0.5, weights=best_weights))
        prev_py = py_centroid

        mapped = result.pixel_to_data(col_x, py_centroid)
        if mapped is None:
            continue
        dx, dy = mapped
        traced_by_col[col] = DataPoint(
            x=dx,
            y=dy,
            px=col_x,
            py=py_centroid,
            confidence=0.9,
            flags=PointFlag.MANUAL,
        )

    # Optional short bridging
    if bridge and len(traced_by_col) >= 2:
        cols_sorted = sorted(traced_by_col.keys())
        for i in range(len(cols_sorted) - 1):
            left_col = cols_sorted[i]
            right_col = cols_sorted[i + 1]
            gap_len = right_col - left_col - 1
            if 1 <= gap_len <= 6:
                p_left = traced_by_col[left_col]
                p_right = traced_by_col[right_col]
                if (
                    p_left.x is not None
                    and p_left.y is not None
                    and p_right.x is not None
                    and p_right.y is not None
                ):
                    for step, b_col in enumerate(range(left_col + 1, right_col), start=1):
                        frac = float(step) / float(gap_len + 1)
                        b_px = float(b_col) + 0.5
                        b_py = p_left.py + frac * (p_right.py - p_left.py)
                        b_x = float(p_left.x) + frac * (float(p_right.x) - float(p_left.x))
                        b_y = float(p_left.y) + frac * (float(p_right.y) - float(p_left.y))
                        traced_by_col[b_col] = DataPoint(
                            x=b_x,
                            y=b_y,
                            px=b_px,
                            py=b_py,
                            confidence=0.55,
                            flags=PointFlag.MANUAL | PointFlag.INTERPOLATED,
                        )

    if not traced_by_col:
        return _export(result, out)

    recovered_xs = [p.x for p in traced_by_col.values() if p.x is not None]
    rec_lo = min(recovered_xs) if recovered_xs else 0.0
    rec_hi = max(recovered_xs) if recovered_xs else 0.0

    # Update or create series
    new_series_list: list[Series] = []
    created_id: str | None = None
    if target_series is not None:
        for s in result.series:
            if s.series_id != target_series.series_id:
                new_series_list.append(s)
                continue
            col_map = {int(round(p.px - 0.5)): p for p in s.points}
            col_map.update(traced_by_col)
            updated_points = [col_map[c] for c in sorted(col_map.keys())]
            updated_gaps = _subtract_gaps(s.gaps, rec_lo, rec_hi)
            updated_s = replace(s, points=updated_points, gaps=updated_gaps)
            updated_s.coverage = series_coverage(updated_s)
            new_series_list.append(updated_s)
    else:
        created_id = f"series_{len(result.series)}"
        new_color = (
            lab_to_hex((float(target_lab[0]), float(target_lab[1]), float(target_lab[2])))
            if target_lab is not None
            else "#1f77b4"
        )
        created_points = [traced_by_col[c] for c in sorted(traced_by_col.keys())]
        new_s = Series(
            series_id=created_id,
            kind="line",
            label=None,
            color_hex=new_color,
            points=created_points,
            gaps=[],
            coverage=1.0,
            confidence=0.9,
            style="solid",
        )
        new_s.coverage = series_coverage(new_s)
        new_series_list = [*result.series, new_s]

    final_series = assign_segment_ids(new_series_list)
    diagnostics = dict(result.diagnostics)
    edits = list(cast(list[object], diagnostics.get("edits", [])))
    edits.append(
        {
            "op": "trace_stroke",
            "n_points": len(traced_by_col),
            "target_series": target_series.series_id if target_series else created_id,
        }
    )
    diagnostics["edits"] = edits
    return _export(replace(result, series=final_series, diagnostics=diagnostics), out)
