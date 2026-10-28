"""Conservative fallback for one dark achromatic curve.

The chromatic separator only considers colored ink, so a black or dark-grey
stroke produces no series at all. This module builds at most one candidate from
dark, low-chroma ink inside the plot box. The frame band, attached tick marks,
text glyphs, a legend handle, and the grid are removed first. A component must
be dominant and span a reasonable part of the plot width; otherwise the figure
stays a no-series result instead of guessing.
"""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from curve2csv.color_math import rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.types import BBox, Masks, PlotArea, SeriesMask

_TICK_MAX_FRACTION = 0.03
_DOMINANT_WIDTH_FRACTION = 0.25
_FRAGMENT_AREA_FRACTION = 0.08


def _frame_band(cfg: PipelineConfig) -> int:
    return max(2, int(cfg.edge_band_px))


def _clear_border(mask: NDArray[np.bool_], bbox: BBox, band: int) -> NDArray[np.bool_]:
    """Remove the spine band itself, including a pixel of anti-aliasing."""

    out = np.array(mask, copy=True)
    height, width = out.shape
    x0, y0, x1, y1 = bbox
    left, right = max(0, x0), min(width, x1)
    top, bottom = max(0, y0), min(height, y1)
    depth = band + 1
    out[top : min(bottom, top + depth), left:right] = False
    out[max(top, bottom - depth) : bottom, left:right] = False
    out[top:bottom, left : min(right, left + depth)] = False
    out[top:bottom, max(left, right - depth) : right] = False
    return out


def _remove_ticks(mask: NDArray[np.bool_], bbox: BBox, cfg: PipelineConfig) -> NDArray[np.bool_]:
    """Drop short marks attached to any of the four spines, including mirrors."""

    out = np.array(mask, copy=True)
    x0, y0, x1, y1 = bbox
    plot_w = max(1, x1 - x0)
    plot_h = max(1, y1 - y0)
    band = _frame_band(cfg)
    max_len = max(8, min(24, int(round(_TICK_MAX_FRACTION * min(plot_w, plot_h)))))
    max_thick = max(3, band + 1)
    edge_gap = band + 2
    count, labels, stats, _ = cv2.connectedComponentsWithStats(out.astype(np.uint8), connectivity=8)
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < 3:
            continue
        near_left = x <= x0 + edge_gap
        near_right = x + w - 1 >= x1 - edge_gap
        near_top = y <= y0 + edge_gap
        near_bottom = y + h - 1 >= y1 - edge_gap
        vertical_tick = (near_left or near_right) and w <= max_len and h <= max_thick
        horizontal_tick = (near_top or near_bottom) and h <= max_len and w <= max_thick
        if vertical_tick or horizontal_tick:
            out[labels == idx] = False
    return out


def _curve_like_text(text: NDArray[np.bool_], bbox: BBox) -> NDArray[np.bool_]:
    """Text components that are really short horizontal pieces of a stroke.

    ``detect_text_mask`` removes long rules but a short, flat stretch of a thin
    curve can still look like a glyph run. Re-allow only shallow, horizontally
    elongated components; words, marker blobs, and panel labels stay excluded.
    """

    x0, y0, x1, y1 = bbox
    plot_w = max(1, x1 - x0)
    plot_h = max(1, y1 - y0)
    height, width = text.shape
    out = np.zeros((height, width), dtype=bool)
    left, right = max(0, x0), min(width, x1)
    top, bottom = max(0, y0), min(height, y1)
    if right <= left or bottom <= top or not np.any(text[top:bottom, left:right]):
        return out
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        text.astype(np.uint8), connectivity=8
    )
    max_h = max(4, min(14, int(round(0.02 * plot_h)) + 2))
    # A flat stretch of a thin curve can survive the long-rule filter and then
    # be dilated into one very long text component. Any length is still a stroke
    # when it stays shallow; give the long ones a slightly taller dilation cap
    # so JPEG fringes and a 3x3 text dilation do not evict them.
    long_min_w = max(40, int(round(0.12 * plot_w)))
    long_max_h = max(max_h, min(22, int(round(0.06 * plot_h)) + 4))
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if x + w <= left or x >= right or y + h <= top or y >= bottom:
            continue
        height_cap = long_max_h if w >= long_min_w else max_h
        if area < 12 or h > height_cap:
            continue
        if w < max(12, 3 * h):
            continue
        out[labels == idx] = True
    return out


def achromatic_text_exclusion(text: NDArray[np.bool_], bbox: BBox) -> NDArray[np.bool_]:
    """Text mask with short stroke-like horizontal pieces re-allowed."""

    return np.asarray(text & ~_curve_like_text(text, bbox), dtype=bool)


def _text_blocks(text: NDArray[np.bool_], bbox: BBox) -> list[tuple[int, int, int, int, int]]:
    """Group text glyphs into horizontal word/line blocks inside the plot box."""

    x0, y0, x1, y1 = bbox
    height, width = text.shape
    left, right = max(0, x0 + 1), min(width, x1 - 1)
    top, bottom = max(0, y0 + 1), min(height, y1 - 1)
    if right <= left or bottom <= top:
        return []
    crop = text[top:bottom, left:right]
    if not np.any(crop):
        return []
    kernel_w = max(5, (right - left) // 80)
    grouped = cv2.dilate(
        crop.astype(np.uint8),
        np.ones((3, kernel_w), dtype=np.uint8),
        iterations=1,
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(grouped, connectivity=8)
    blocks: list[tuple[int, int, int, int, int]] = []
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < 20 or h < 4:
            continue
        # A vertical marker is not a word. Legend labels are wider than tall.
        if w < max(18, int(round(1.5 * h))):
            continue
        blocks.append((x + left, y + top, w, h, area))
    return blocks


def _legend_handle_mask(
    candidate: NDArray[np.bool_],
    text: NDArray[np.bool_],
    bbox: BBox,
    cfg: PipelineConfig,
) -> NDArray[np.bool_]:
    """Remove a short sample line/marker immediately left of legend text.

    The text itself is already excluded by ``detect_text_mask``. This targets
    the handle only, and only when it lies in the text line's vertical band and
    is short enough to be a legend sample rather than a curve fragment.
    """

    x0, y0, x1, y1 = bbox
    plot_w = max(1, x1 - x0)
    height, width = candidate.shape
    out = np.zeros((height, width), dtype=bool)
    blocks = _text_blocks(text, bbox)
    if not blocks or not np.any(candidate):
        return out
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        candidate.astype(np.uint8), connectivity=8
    )
    handle_max_w = max(12, int(round(0.4 * plot_w)))
    for bx, by, _bw, bh, _area in blocks:
        max_gap = max(12, 2 * bh)
        lo_y = by - max(3, bh // 4)
        hi_y = by + bh + max(3, bh // 4)
        for idx in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[idx])
            if area < 3:
                continue
            right = x + w
            gap = bx - right
            if gap < 0 or gap > max_gap:
                continue
            center_y = y + 0.5 * h
            if not (lo_y <= center_y <= hi_y):
                continue
            if w > handle_max_w or h > max(4, 2 * bh):
                continue
            out[labels == idx] = True
    return out


def _dominant_curve_mask(
    candidate: NDArray[np.bool_], bbox: BBox, cfg: PipelineConfig
) -> NDArray[np.bool_]:
    """Keep the dominant wide component plus nearby fragments of the same stroke."""

    x0, y0, x1, y1 = bbox
    plot_w = max(1, x1 - x0)
    plot_h = max(1, y1 - y0)
    empty = np.zeros(candidate.shape, dtype=bool)
    if not np.any(candidate):
        return empty
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        candidate.astype(np.uint8), connectivity=8
    )
    components: list[tuple[int, int, int, int, int, int]] = []
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < 3:
            continue
        components.append((idx, area, x, y, w, h))
    if not components:
        return empty
    main = max(components, key=lambda item: item[1])
    main_idx, main_area, main_x, main_y, main_w, main_h = main
    min_width = max(20, int(round(_DOMINANT_WIDTH_FRACTION * plot_w)))
    min_area = max(20, int(round(0.0002 * plot_w * plot_h)))
    if main_w < min_width or main_area < min_area:
        return empty
    keep = labels == main_idx
    x_gap_limit = max(12, int(round(0.08 * plot_w)))
    y_gap_limit = max(12, int(round(0.10 * plot_h)))
    fragment_area = max(10, int(round(_FRAGMENT_AREA_FRACTION * main_area)))
    for idx, area, x, y, w, h in components:
        if idx == main_idx or area < fragment_area:
            continue
        if w < 6 and h < 6:
            continue
        gap_x = max(0, main_x - (x + w), x - (main_x + main_w))
        gap_y = max(0, main_y - (y + h), y - (main_y + main_h))
        if gap_x <= x_gap_limit and gap_y <= y_gap_limit:
            keep |= labels == idx
    ys, xs = np.nonzero(keep)
    if xs.size == 0 or int(xs.max() + 1 - xs.min()) < min_width:
        return empty
    return np.asarray(keep, dtype=bool)


def _spine_band_zone(
    dark_ink: NDArray[np.bool_], bbox: BBox, band: int
) -> NDArray[np.bool_]:
    """Top/bottom spine rows plus the border depth strips inside the box."""

    x0, y0, x1, y1 = bbox
    height, width = dark_ink.shape
    left, right = max(0, x0), min(width, x1)
    top, bottom = max(0, y0), min(height, y1)
    zone = np.zeros((height, width), dtype=bool)
    if right <= left or bottom <= top:
        return zone
    plot_w = right - left
    plot_h = bottom - top
    depth = band + 1
    zone[top : min(bottom, top + depth), left:right] = True
    zone[max(top, bottom - depth) : bottom, left:right] = True
    near = max(band + 4, int(round(0.02 * plot_h)))
    rows = np.unique(
        np.concatenate(
            [
                np.arange(max(0, top - near), min(height, top + near + 1)),
                np.arange(max(0, bottom - near), min(height, bottom + near + 1)),
            ]
        )
    )
    min_span = 0.75 * plot_w
    for row in rows:
        if int(dark_ink[int(row), left:right].sum()) >= min_span:
            zone[int(row), left:right] = True
    return zone


def grow_along_spine_band(
    mask: NDArray[np.bool_],
    dark_ink: NDArray[np.bool_],
    text_exclusion: NDArray[np.bool_],
    grid: NDArray[np.bool_],
    legend: NDArray[np.bool_],
    bbox: BBox,
    band: int,
) -> NDArray[np.bool_]:
    """Geodesically recover axis-band ink in columns that have no curve yet.

    A curve segment that lies on the x axis is removed with the spine by the
    border clear. Grow the dominant stroke through the leftover spine band, but
    only into columns without any current curve ink so the spine cannot be
    painted underneath the rest of the curve.
    """

    grown = np.array(mask, copy=True)
    x0, y0, x1, y1 = bbox
    height, width = mask.shape
    left, right = max(0, x0), min(width, x1)
    top, bottom = max(0, y0), min(height, y1)
    if right <= left or bottom <= top:
        return grown
    if not np.any(grown[top:bottom, left:right]):
        return grown
    inside = np.zeros((height, width), dtype=bool)
    inside[top:bottom, left:right] = True
    band_zone = _spine_band_zone(dark_ink, bbox, band)
    if not np.any(band_zone):
        return grown
    box_columns = np.any(grown[top:bottom, left:right], axis=0)
    empty_cols = np.zeros(width, dtype=bool)
    empty_cols[left:right] = ~box_columns
    # A thick spine or an anti-aliased stroke may put the only inside-box ink
    # one pixel away from the dark core. Tolerate that fringe, but only inside
    # the axis band.
    kernel = np.ones((3, 3), dtype=np.uint8)
    band_ink = cv2.dilate(dark_ink.astype(np.uint8), kernel, iterations=1) > 0
    allow = (
        band_zone
        & band_ink
        & inside
        & ~text_exclusion
        & ~grid
        & ~legend
        & empty_cols[None, :]
    ) | grown
    current = grown
    for _ in range(150):
        dilated = cv2.dilate(current.astype(np.uint8), kernel, iterations=1) > 0
        updated = dilated & allow
        if np.array_equal(updated, current):
            break
        current = updated
    return np.asarray(current, dtype=bool)


def achromatic_width_hint(mask: NDArray[np.bool_], bbox: BBox) -> float:
    """Nominal width that keeps a steep, tall ink run out of the swatch rule.

    A near-vertical curve fills many rows in one column even though it is one
    thin stroke. The hint is only used for the achromatic fallback, never for a
    chromatically separated series.
    """

    x0, y0, x1, y1 = bbox
    tallest = 1
    for col in range(max(0, x0), max(0, x1)):
        rows = np.flatnonzero(mask[max(0, y0) : max(0, y1), col])
        if rows.size == 0:
            continue
        breaks = np.flatnonzero(np.diff(rows) > 2) + 1
        for run in np.split(rows, breaks):
            tallest = max(tallest, int(run.size))
    return max(1.0, tallest / 2.0)


def separate_achromatic_series(
    rgb: np.ndarray,
    masks: Masks,
    area: PlotArea,
    config: PipelineConfig | None = None,
) -> list[SeriesMask]:
    """Return at most one dark achromatic curve, or nothing when not confident."""

    cfg = config or PipelineConfig()
    x0, y0, x1, y1 = area.bbox
    if x1 - x0 < 20 or y1 - y0 < 20:
        return []
    height, width = rgb.shape[:2]
    inside = np.zeros((height, width), dtype=bool)
    left, right = max(0, x0), min(width, x1)
    top, bottom = max(0, y0), min(height, y1)
    if right <= left or bottom <= top:
        return []
    inside[top:bottom, left:right] = True
    lab = rgb2lab(rgb).astype(np.float64)
    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Text glyphs use a slightly wider chroma tolerance than the chromatic
    # separator; JPEG fringes around a grey stroke must not split the candidate.
    low_chroma = chroma < max(cfg.chroma_min, 18.0)
    dark_ink = (gray < cfg.ink_threshold) & low_chroma
    candidate = dark_ink & inside
    text_exclusion = achromatic_text_exclusion(masks.text, area.bbox)
    candidate &= ~text_exclusion
    candidate &= ~masks.grid
    candidate &= ~masks.axes
    candidate &= ~masks.legend
    candidate = _clear_border(candidate, area.bbox, _frame_band(cfg))
    candidate = _remove_ticks(candidate, area.bbox, cfg)
    handle = _legend_handle_mask(candidate, masks.text, area.bbox, cfg)
    if np.any(handle):
        candidate &= ~handle
    # Bridge one-pixel holes such as open marker outlines before choosing the
    # dominant stroke. Never let the close pull in text, grid, or axis ink.
    closed = cv2.morphologyEx(
        candidate.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1
    )
    candidate = (closed > 0) & dark_ink & inside
    candidate &= ~text_exclusion
    candidate &= ~masks.grid
    candidate &= ~masks.axes
    candidate &= ~masks.legend
    candidate = _dominant_curve_mask(candidate, area.bbox, cfg)
    candidate = grow_along_spine_band(
        candidate,
        dark_ink,
        text_exclusion,
        masks.grid,
        masks.legend,
        area.bbox,
        _frame_band(cfg),
    )
    ys, xs = np.nonzero(candidate)
    if xs.size < 10:
        return []
    color_lab = tuple(float(value) for value in np.median(lab[ys, xs], axis=0))
    return [
        SeriesMask(
            series_id="s0",
            color_lab=(color_lab[0], color_lab[1], color_lab[2]),
            style="solid",
            mask=candidate,
            separation_score=100.0,
            ambiguous=False,
        )
    ]
