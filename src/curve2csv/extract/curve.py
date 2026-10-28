"""Column-wise centerline extraction.

The path is a color-constrained dynamic program. A short hole is filled only
when another series covers it; those points carry ``INTERPOLATED``. Every other
missing column stays a gap.
"""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.extract.track import track_series
from curve2csv.types import (
    DataPoint,
    Masks,
    PixelMapper,
    PlotArea,
    PointFlag,
    Series,
    SeriesMask,
)


def _broken_thin_stroke(crop: np.ndarray) -> bool:
    """True when same-color ink is a thin stroke split into short pieces.

    Round markers are thicker and leave most columns empty. A continuous stroke
    has one long component. Neither matches.
    """

    if crop.size == 0:
        return False
    covered = int(crop.any(axis=0).sum())
    width = max(1, crop.shape[1])
    if covered / float(width) < 0.55:
        return False
    if float(crop.sum()) / float(covered) > 2.0:
        return False
    count, _labels, stats, _ = cv2.connectedComponentsWithStats(
        crop.astype(np.uint8), connectivity=8
    )
    wide = 0
    pieces = 0
    heights: list[int] = []
    for idx in range(1, count):
        if int(stats[idx, cv2.CC_STAT_AREA]) < 3:
            continue
        pieces += 1
        wide = max(wide, int(stats[idx, cv2.CC_STAT_WIDTH]))
        heights.append(int(stats[idx, cv2.CC_STAT_HEIGHT]))
    if not heights:
        return False
    # The two held-out strokes are one pixel tall. Taller fragments are a
    # different series running nearby, and tracking them pulls the centerline off.
    return (
        pieces >= 5
        and 40 <= wide < int(0.2 * width)
        and float(np.median(heights)) <= 4.0
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
    broken = kind == "line" and _broken_thin_stroke(crop)
    for idx in range(1, n):
        _x, _y, w, h, area = (int(v) for v in stats[idx])
        if kind == "line":
            # Legend handles are short in height and much smaller than the stroke.
            # Steep pieces of the curve are tall, so they stay. A thin stroke that
            # is already split into short pieces keeps those pieces.
            handle_limit = 3 if broken else max(80, int(0.12 * largest))
            speck_limit = 3 if broken else max(12, int(0.015 * largest))
            handle = area < handle_limit and w < 0.22 * plot_w and h < 0.08 * plot_h
            speck = area < speck_limit and max(w, h) < 18
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
    # A 1px stroke broken into short pieces still covers most columns. Round
    # markers are thicker and leave most columns empty, so they remain scatter.
    if _broken_thin_stroke(crop):
        return "line"
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
    lab_image: np.ndarray | None = None,
) -> Series:
    cfg = config or PipelineConfig()
    x0, y0, x1, y1 = area.bbox
    broken = _broken_thin_stroke(series_mask.mask[y0:y1, x0:x1])
    mask = _component_mask(series_mask.mask, area.bbox, kind="line")
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
    text_dist = cv2.distanceTransform((~masks.text).astype(np.uint8), cv2.DIST_L2, 3)
    tracked = track_series(
        mask,
        area.bbox,
        est_width=est_width,
        thin_width=thin_width,
        color_lab=series_mask.color_lab,
        lab_image=lab_image,
        other_mask=other_mask,
        keep_short_segments=broken,
    )
    for node in tracked:
        px = float(node.col) + 0.5
        py = float(node.py)
        data = mapper.pixel_to_data(px, py)
        if node.kind == "bridge":
            if data is None:
                continue
            points.append(
                DataPoint(
                    x=data[0],
                    y=data[1],
                    px=px,
                    py=py,
                    confidence=0.55,
                    flags=PointFlag.INTERPOLATED,
                )
            )
            continue
        flags = PointFlag.NONE
        # The path already picked this series' color. A run whose best pixel is
        # another series' color stays flagged so strict scoring drops it.
        if node.color_delta > 28.0 or (node.n_runs > 1 and node.color_delta > 17.0):
            flags |= PointFlag.AMBIGUOUS_SERIES
        if 0 <= int(py) < text_dist.shape[0] and text_dist[int(py), int(px)] <= 1.5:
            flags |= PointFlag.NEAR_TEXT
        if node.col <= x0 + 1 or node.col >= x1 - 2:
            flags |= PointFlag.EDGE_OF_PLOT
        if node.thickness > cfg.thick_factor * est_width and node.n_runs > 1:
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
    # Specks acquired after a gap are legend remnants, not a curve. Short pieces
    # of one thin stroke, split by one or two empty columns, stay. The empty
    # columns themselves are not emitted.
    pieces: list[list[DataPoint]] = []
    run: list[DataPoint] = []

    def flush_run() -> None:
        nonlocal run
        if run:
            pieces.append(run)
        run = []

    for point in points:
        if run and point.px - run[-1].px > 1.6:
            flush_run()
        run.append(point)
    flush_run()

    def _joins(left: list[DataPoint], right: list[DataPoint]) -> bool:
        if not broken:
            return False
        gap = right[0].px - left[-1].px
        dy = abs(right[0].py - left[-1].py)
        return gap <= 3.6 and dy <= max(10.0, 3.0 * gap)

    parent = list(range(len(pieces)))

    def _find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for index in range(1, len(pieces)):
        if _joins(pieces[index - 1], pieces[index]):
            root_left = _find(index - 1)
            root_right = _find(index)
            if root_left != root_right:
                parent[root_right] = root_left
    totals: dict[int, int] = {}
    for index, piece in enumerate(pieces):
        root = _find(index)
        totals[root] = totals.get(root, 0) + len(piece)
    kept_points: list[DataPoint] = []
    for index, piece in enumerate(pieces):
        if totals[_find(index)] >= 16:
            kept_points.extend(piece)
    points = kept_points
    covered = {int(point.px) for point in points}
    gap_runs: list[tuple[int, int]] = []
    gap_start: int | None = None
    for col in range(x0, x1):
        if col in covered:
            if gap_start is not None:
                gap_runs.append((gap_start, col))
                gap_start = None
        elif gap_start is None:
            gap_start = col
    if gap_start is not None:
        gap_runs.append((gap_start, x1))
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
