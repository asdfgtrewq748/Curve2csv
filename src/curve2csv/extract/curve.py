"""Column-wise centerline extraction. Missing columns become gaps; nothing is interpolated."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.types import (
    DataPoint,
    Masks,
    PixelMapper,
    PlotArea,
    PointFlag,
    Series,
    SeriesMask,
)


def _component_mask(mask: np.ndarray, bbox: tuple[int, int, int, int], *, kind: str) -> np.ndarray:
    """Drop legend swatches and specks. Bars and scatter keep their own size rules."""

    x0, y0, x1, y1 = bbox
    crop = mask[y0:y1, x0:x1]
    if crop.size == 0 or not np.any(crop):
        return mask
    n, labels, stats, _ = cv2.connectedComponentsWithStats(crop.astype(np.uint8), connectivity=8)
    if n <= 1:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = int(areas.max()) if areas.size else 0
    keep = np.zeros(n, dtype=bool)
    keep[0] = False
    plot_w = max(1, x1 - x0)
    plot_h = max(1, y1 - y0)
    for idx in range(1, n):
        _x, _y, w, h, area = (int(v) for v in stats[idx])
        if kind == "line":
            # Legend handles are short in height and much smaller than the stroke.
            # Steep pieces of the curve are tall, so they stay.
            handle = area < max(80, int(0.12 * largest)) and w < 0.22 * plot_w and h < 0.08 * plot_h
            speck = area < max(12, int(0.015 * largest)) and max(w, h) < 18
            if not handle and not speck:
                keep[idx] = True
        elif kind == "bar":
            if area >= max(20, int(0.15 * largest)):
                keep[idx] = True
        else:
            if area >= 3:
                keep[idx] = True
    if not np.any(keep):
        # Keep the largest component rather than deleting the series.
        biggest = int(np.argmax(stats[:, cv2.CC_STAT_AREA]))
        keep[biggest] = True
        keep[0] = False
    kept = keep[labels]
    cleaned = np.zeros_like(mask)
    cleaned[y0:y1, x0:x1] = kept
    return cleaned


def classify_mask(mask: np.ndarray, bbox: tuple[int, int, int, int]) -> str:
    x0, y0, x1, y1 = bbox
    crop = mask[y0:y1, x0:x1]
    if crop.size == 0 or int(crop.sum()) < 15:
        return "line"
    n, _labels, stats, _ = cv2.connectedComponentsWithStats(crop.astype(np.uint8), connectivity=8)
    widths: list[int] = []
    heights: list[int] = []
    fills: list[float] = []
    bottoms: list[int] = []
    comp_areas = [int(stats[idx, cv2.CC_STAT_AREA]) for idx in range(1, n)]
    largest = max(comp_areas) if comp_areas else 0
    # Speckle from JPEG noise must not outvote the real bars or strokes.
    area_floor = max(8, int(0.05 * largest))
    for idx in range(1, n):
        _x, y, w, h, area = (int(v) for v in stats[idx])
        if area < area_floor:
            continue
        widths.append(w)
        heights.append(h)
        fills.append(area / float(max(w * h, 1)))
        bottoms.append(y + h)
    if not widths:
        return "line"
    covered = int(crop.any(axis=0).sum())
    thickness = float(crop.sum()) / float(max(covered, 1))
    med_fill = float(np.median(fills))
    med_h = float(np.median(heights))
    med_w = float(np.median(widths))
    max_w = max(widths)
    crop_h = crop.shape[0]
    crop_w = max(1, crop.shape[1])
    bottom_aligned = float(np.median(bottoms)) > 0.82 * crop_h
    if (
        med_fill > 0.62
        and med_h >= 8
        and med_w >= 3
        and bottom_aligned
        and thickness >= 5.0
        and max_w < 0.85 * crop_w
    ):
        return "bar"
    # Compact blobs are markers even when they cover many columns.
    if len(widths) >= 5 and max_w < 0.2 * crop_w and med_w <= 30 and med_h <= 30 and med_fill > 0.2:
        return "scatter"
    elongated = max_w >= max(12, int(0.08 * crop_w)) and thickness < 16.0
    if elongated or (covered / crop_w > 0.45 and thickness < 8.0 and max_w >= 0.2 * crop_w):
        return "line"
    if thickness < 8.0 and max_w >= 0.15 * crop_w:
        return "line"
    return "scatter" if len(widths) >= 4 else "line"


def _runs(rows: np.ndarray) -> list[np.ndarray]:
    if rows.size == 0:
        return []
    splits = np.where(np.diff(rows) > 2)[0] + 1
    return list(np.split(rows, splits))


def column_is_occluded(
    gray: np.ndarray | None,
    bbox: tuple[int, int, int, int],
    px: float,
) -> bool:
    """True when the plot column is mostly dark, which is an occluder not a stroke."""

    if gray is None or gray.ndim != 2:
        return False
    _x0, y0, _x1, y1 = bbox
    col = int(np.clip(round(px - 0.5), 0, gray.shape[1] - 1))
    band = gray[max(0, y0) : max(0, y1), col]
    return bool(band.size) and float(np.mean(band < 200)) > 0.45


def extract_curve(
    series_mask: SeriesMask,
    area: PlotArea,
    mapper: PixelMapper,
    masks: Masks,
    config: PipelineConfig | None = None,
    *,
    color_hex: str | None = None,
    gray: np.ndarray | None = None,
    other_mask: np.ndarray | None = None,
    clean_components: bool = True,
    allow_single_ridge_overlap: bool = False,
) -> Series:
    cfg = config or PipelineConfig()
    x0, y0, x1, y1 = area.bbox
    mask = (
        _component_mask(series_mask.mask, area.bbox, kind="line")
        if clean_components
        else series_mask.mask
    )
    crop = mask[y0:y1, x0:x1]
    covered_cols = crop.any(axis=0)
    if int(covered_cols.sum()) == 0:
        return Series(
            series_id=series_mask.series_id,
            kind="line",
            label=None,
            color_hex=color_hex,
            points=[],
            gaps=[],
            coverage=0.0,
            confidence=0.0,
            style=series_mask.style,
        )
    # Width of the main stroke. A short legend handle must not set this, or a
    # steep curve looks "too thick" and is skipped.
    comp_count, comp_labels, comp_stats, _ = cv2.connectedComponentsWithStats(
        crop.astype(np.uint8), connectivity=8
    )
    if comp_count > 1:
        main = 1 + int(np.argmax(comp_stats[1:, cv2.CC_STAT_AREA]))
        main_cols = (comp_labels == main).sum(axis=0)
        main_cols = main_cols[main_cols > 0]
        est_width = float(np.median(main_cols)) if main_cols.size else 1.0
    else:
        est_width = float(np.median(crop.sum(axis=0)[covered_cols]))
    est_width = max(1.0, est_width)
    run_sizes: list[int] = []
    for col in range(x0, x1):
        col_rows = np.flatnonzero(mask[y0:y1, col])
        if col_rows.size == 0:
            continue
        run_sizes.append(max(int(run.size) for run in _runs(col_rows)))
    thin_width = (
        float(np.percentile(np.asarray(run_sizes, dtype=np.float64), 30))
        if run_sizes
        else est_width
    )
    thin_width = max(1.0, thin_width)
    points: list[DataPoint] = []
    gap_runs: list[tuple[int, int]] = []
    gap_start: int | None = None
    last_py: float | None = None
    prev_rows: np.ndarray | None = None
    text_dist = cv2.distanceTransform((~masks.text).astype(np.uint8), cv2.DIST_L2, 3)
    other_dist = None
    if other_mask is not None and np.any(other_mask):
        other_dist = cv2.distanceTransform((~other_mask).astype(np.uint8), cv2.DIST_L2, 3)

    def close_gap(col: int) -> None:
        nonlocal gap_start
        if gap_start is not None and col > gap_start:
            gap_runs.append((gap_start, col))
        gap_start = None

    for col in range(x0, x1):
        rows = np.flatnonzero(mask[y0:y1, col])
        if rows.size == 0:
            if gap_start is None:
                gap_start = col
            continue
        runs = _runs(rows)
        runs.sort(key=lambda run: int(run.size), reverse=True)
        chosen = runs[0]
        connected = False
        if prev_rows is not None and prev_rows.size and chosen.size:
            # A steep stroke moves farther than its thickness between columns.
            row_lo = int(prev_rows[0]) - 8
            row_hi = int(prev_rows[-1]) + 8
            connected = bool(np.any((chosen >= row_lo) & (chosen <= row_hi)))
        # A tall blob that does not touch the previous column is not the stroke.
        # A steep stroke stays connected, and its center is the sample.
        if float(chosen.size) > cfg.thick_factor * est_width and len(runs) == 1 and not connected:
            if gap_start is None:
                gap_start = col
            continue
        close_gap(col)
        weights_rows = chosen + y0
        chroma_w = np.ones(weights_rows.shape, dtype=np.float64)
        py = float(np.average(weights_rows, weights=chroma_w) + 0.5)
        px = float(col) + 0.5
        # A thick column that jumps away from the stroke is a step riser or a
        # legend swatch, not a sample of the curve. A steep stroke stays
        # connected and moves by about its own thickness, so its center is kept.
        # A step riser is also connected, but its center sits far from the
        # previous sample; that midpoint is not a value on the curve.
        delta_py = abs(py - last_py) if last_py is not None else 0.0
        jump = last_py is not None and delta_py > max(8.0, 3.0 * est_width)
        if jump and float(chosen.size) > 2.2 * est_width and (not connected or delta_py > 36.0):
            if gap_start is None:
                gap_start = col
            continue
        last_py = py
        prev_rows = chosen
        data = mapper.pixel_to_data(px, py)
        flags = PointFlag.NONE
        # A merged color is still one stroke. Flagging every point erases it
        # from the scored output. A second ridge far from this one, or ink that
        # sits on another series, has no single y.
        if len(runs) > 1:
            chosen_center = float(np.mean(chosen) + y0 + 0.5)
            split = max(16.0, 4.0 * thin_width)
            for extra in runs:
                center = float(np.mean(extra) + y0 + 0.5)
                if abs(center - chosen_center) > split:
                    flags |= PointFlag.AMBIGUOUS_SERIES
                    break
        if other_dist is not None:
            iy = int(np.clip(round(py - 0.5), 0, other_dist.shape[0] - 1))
            ix = int(np.clip(round(px - 0.5), 0, other_dist.shape[1] - 1))
            single_ridge = allow_single_ridge_overlap and len(runs) == 1
            if float(other_dist[iy, ix]) <= 2.0 and not single_ridge:
                flags |= PointFlag.AMBIGUOUS_SERIES
        if 0 <= int(py) < text_dist.shape[0] and text_dist[int(py), int(px)] <= 1.5:
            flags |= PointFlag.NEAR_TEXT
        # The sample comes from a chromatic series mask, so a gridline crossing
        # it is still the stroke. Gray grid ink never enters this mask.
        if col <= x0 + 1 or col >= x1 - 2:
            flags |= PointFlag.EDGE_OF_PLOT
        # A connected steep stroke has one center. Flag a tall column only when
        # several runs share it.
        if float(chosen.size) > cfg.thick_factor * est_width and len(runs) > 1:
            flags |= PointFlag.THICK_SEGMENT
        if column_is_occluded(gray, area.bbox, px):
            flags |= PointFlag.THICK_SEGMENT
        confidence = 0.93
        if series_mask.separation_score < cfg.min_series_delta_e:
            confidence *= 0.75
        if PointFlag.NEAR_TEXT in flags:
            confidence *= 0.25
        if PointFlag.THICK_SEGMENT in flags:
            confidence *= 0.85
        confidence = float(np.clip(confidence, 0.0, 1.0))
        x_val: float | None
        y_val: float | None
        if data is None or confidence < cfg.min_point_confidence:
            flags |= PointFlag.LOW_CONFIDENCE
            x_val, y_val = None, None
        else:
            x_val, y_val = data
        points.append(DataPoint(x=x_val, y=y_val, px=px, py=py, confidence=confidence, flags=flags))
    if gap_start is not None:
        gap_runs.append((gap_start, x1))
    # Specks acquired after a gap are legend remnants, not a curve.
    kept_points: list[DataPoint] = []
    run: list[DataPoint] = []

    def flush_run() -> None:
        nonlocal run
        if len(run) >= 16:
            kept_points.extend(run)
        elif run:
            c0 = int(run[0].px)
            c1 = int(run[-1].px) + 1
            gap_runs.append((c0, c1))
        run = []

    for point in points:
        if run and point.px - run[-1].px > 1.6:
            flush_run()
        run.append(point)
    flush_run()
    points = kept_points
    gaps: list[tuple[float, float]] = []
    for c0, c1 in gap_runs:
        p0 = mapper.pixel_to_data(float(c0) + 0.5, float(area.x_axis_px))
        p1 = mapper.pixel_to_data(float(c1) + 0.5, float(area.x_axis_px))
        if p0 is None or p1 is None:
            continue
        lo, hi = sorted((p0[0], p1[0]))
        if hi > lo:
            gaps.append((lo, hi))
    xs = [p.x for p in points if p.x is not None]
    if len(xs) >= 2:
        span = max(xs) - min(xs)
        gap_span = sum(hi - lo for lo, hi in gaps)
        coverage = float(np.clip(1.0 - gap_span / span, 0.0, 1.0)) if span > 0 else 0.0
    else:
        coverage = 0.0
    confs = [p.confidence for p in points if p.x is not None]
    series_conf = float(np.median(confs)) if confs else 0.0
    return Series(
        series_id=series_mask.series_id,
        kind="line",
        label=None,
        color_hex=color_hex,
        points=points,
        gaps=gaps,
        coverage=coverage,
        confidence=series_conf,
        style=series_mask.style,
    )
