"""Bar rectangles: one point per bar at the top edge and the horizontal center."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.extract.curve import _component_mask, column_is_occluded
from curve2csv.types import DataPoint, PixelMapper, PlotArea, PointFlag, Series, SeriesMask


def extract_bar(
    series_mask: SeriesMask,
    area: PlotArea,
    mapper: PixelMapper,
    config: PipelineConfig | None = None,
    *,
    color_hex: str | None = None,
    gray: np.ndarray | None = None,
) -> Series:
    _ = config
    mask = _component_mask(series_mask.mask, area.bbox, kind="bar")
    x0, y0, x1, y1 = area.bbox
    crop = mask[y0:y1, x0:x1]
    points: list[DataPoint] = []
    if crop.size == 0 or not np.any(crop):
        return Series(series_mask.series_id, "bar", None, color_hex, [], [], 0.0, 0.0, None)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(crop.astype(np.uint8), connectivity=8)
    for idx in range(1, n):
        x, y, w, h, area_px = (int(v) for v in stats[idx])
        if area_px < 12 or w < 2 or h < 3:
            continue
        fill = area_px / float(max(w * h, 1))
        if fill < 0.45:
            continue
        component = labels[y : y + h, x : x + w] == idx
        rows = np.flatnonzero(component.any(axis=1))
        cols = np.flatnonzero(component.any(axis=0))
        if rows.size == 0 or cols.size == 0:
            continue
        # Top edge is the boundary at the first filled row (continuous coordinate).
        top = float(y0 + y + int(rows[0]))
        cx = float(x0 + x + float(np.mean(cols)) + 0.5)
        # Use the top edge itself, not the center of the top pixel.
        py = top
        data = mapper.pixel_to_data(cx, py)
        flags = PointFlag.AMBIGUOUS_SERIES if series_mask.ambiguous else PointFlag.NONE
        if column_is_occluded(gray, area.bbox, cx):
            flags |= PointFlag.THICK_SEGMENT
        if data is None:
            flags |= PointFlag.LOW_CONFIDENCE
            x_val: float | None = None
            y_val: float | None = None
            confidence = 0.2
        else:
            x_val, y_val = data
            confidence = 0.9
        points.append(DataPoint(x_val, y_val, cx, py, confidence, flags))
    points.sort(key=lambda p: (p.x is None, p.x if p.x is not None else p.px))
    confs = [p.confidence for p in points if p.x is not None]
    return Series(
        series_id=series_mask.series_id,
        kind="bar",
        label=None,
        color_hex=color_hex,
        points=points,
        gaps=[],
        coverage=1.0 if points else 0.0,
        confidence=float(np.median(confs)) if confs else 0.0,
        style=None,
    )
