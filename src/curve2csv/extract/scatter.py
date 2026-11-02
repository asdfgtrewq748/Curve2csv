"""Scatter-marker centers from local maxima of the series mask."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.extract.curve import _component_mask
from curve2csv.types import DataPoint, PixelMapper, PlotArea, PointFlag, Series, SeriesMask


def extract_scatter(
    series_mask: SeriesMask,
    area: PlotArea,
    mapper: PixelMapper,
    config: PipelineConfig | None = None,
    *,
    color_hex: str | None = None,
) -> Series:
    cfg = config or PipelineConfig()
    mask = _component_mask(series_mask.mask, area.bbox, kind="scatter")
    x0, y0, x1, y1 = area.bbox
    crop = mask[y0:y1, x0:x1]
    if crop.size == 0 or int(crop.sum()) < cfg.scatter_min_pixels:
        return Series(series_mask.series_id, "scatter", None, color_hex, [], [], 0.0, 0.0, "solid")
    # Matplotlib anchors a marker at the center of its bounding box. The ink
    # centroid of a triangle sits below that point, so use the box center.
    count, _labels, stats, _ = cv2.connectedComponentsWithStats(
        crop.astype(np.uint8), connectivity=8
    )
    areas = [int(stats[idx, cv2.CC_STAT_AREA]) for idx in range(1, count)]
    if not areas:
        return Series(series_mask.series_id, "scatter", None, color_hex, [], [], 0.0, 0.0, "solid")
    typical = float(np.median([a for a in areas if a >= cfg.scatter_min_pixels] or areas))
    kept: list[tuple[float, float]] = []
    for idx in range(1, count):
        x, y, w, h, area_px = (int(v) for v in stats[idx])
        if area_px < max(cfg.scatter_min_pixels, int(0.35 * typical)):
            continue
        if typical > 0 and (area_px > 12.0 * typical or w > 4.0 * max(h, 1) and w > 30):
            continue
        cx = float(x0 + x) + w / 2.0
        cy = float(y0 + y) + h / 2.0
        if any((cx - kx) ** 2 + (cy - ky) ** 2 < cfg.scatter_min_distance**2 for kx, ky in kept):
            continue
        kept.append((cx, cy))
    points: list[DataPoint] = []
    for cx, cy in kept:
        data = mapper.pixel_to_data(cx, cy)
        flags = PointFlag.AMBIGUOUS_SERIES if series_mask.ambiguous else PointFlag.NONE
        if data is None:
            flags |= PointFlag.LOW_CONFIDENCE
            x_val: float | None = None
            y_val: float | None = None
            confidence = 0.2
        else:
            x_val, y_val = data
            confidence = 0.9 if not series_mask.ambiguous else 0.6
        points.append(DataPoint(x_val, y_val, cx, cy, confidence, flags))
    points.sort(key=lambda p: (p.x is None, p.x if p.x is not None else 0.0, p.px))
    confs = [p.confidence for p in points if p.x is not None]
    return Series(
        series_id=series_mask.series_id,
        kind="scatter",
        label=None,
        color_hex=color_hex,
        points=points,
        gaps=[],
        coverage=1.0 if points else 0.0,
        confidence=float(np.median(confs)) if confs else 0.0,
        style=None,
    )
