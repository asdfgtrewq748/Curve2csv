"""Plot-area detection from axis spines.

Upright figures use morphological long-line extraction, which lands on the spine
pixel. Rotated figures fall back to Hough line pairs. The returned bbox is the
axis-aligned envelope of the spine centers, in integer pixel indices.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.types import Abstain, BBox, PlotArea


def _ink(gray: np.ndarray, threshold: int) -> np.ndarray:
    return (gray < threshold).astype(np.uint8) * 255


def _clusters(indices: np.ndarray, scores: np.ndarray, gap: int = 3) -> list[int]:
    if indices.size == 0:
        return []
    groups: list[list[int]] = [[int(indices[0])]]
    for idx in indices[1:]:
        if int(idx) - groups[-1][-1] <= gap:
            groups[-1].append(int(idx))
        else:
            groups.append([int(idx)])
    peaks: list[int] = []
    for group in groups:
        best = max(group, key=lambda i: float(scores[i]))
        peaks.append(best)
    return peaks


def _side_coverage(
    mask: np.ndarray, start: int, end: int, fixed: int, *, horizontal: bool
) -> float:
    if end <= start:
        return 0.0
    if horizontal:
        row = int(np.clip(fixed, 0, mask.shape[0] - 1))
        c0 = int(np.clip(start, 0, mask.shape[1]))
        c1 = int(np.clip(end, 0, mask.shape[1]))
        band = mask[max(0, row - 1) : row + 2, c0:c1]
    else:
        col = int(np.clip(fixed, 0, mask.shape[1] - 1))
        r0 = int(np.clip(start, 0, mask.shape[0]))
        r1 = int(np.clip(end, 0, mask.shape[0]))
        band = mask[r0:r1, max(0, col - 1) : col + 2]
    if band.size == 0:
        return 0.0
    return float(
        np.any(band > 0, axis=0 if horizontal else 1).mean()
        if False
        else (band > 0).max(axis=0 if horizontal else 1).mean()
    )


def _best_aligned(opened_h: np.ndarray, opened_v: np.ndarray) -> tuple[BBox, float] | None:
    row_score = (opened_h > 0).sum(axis=1)
    col_score = (opened_v > 0).sum(axis=0)
    h, w = opened_h.shape
    rows = _clusters(np.flatnonzero(row_score > max(20, 0.12 * w)), row_score)
    cols = _clusters(np.flatnonzero(col_score > max(20, 0.12 * h)), col_score)
    if len(rows) < 2 or len(cols) < 2:
        return None
    best: tuple[BBox, float, int] | None = None
    for top in rows:
        for bottom in rows:
            if bottom - top < max(20, int(0.12 * h)):
                continue
            for left in cols:
                for right in cols:
                    if right - left < max(20, int(0.12 * w)):
                        continue
                    covs = (
                        _side_coverage(opened_h, left, right, top, horizontal=True),
                        _side_coverage(opened_h, left, right, bottom, horizontal=True),
                        _side_coverage(opened_v, top, bottom, left, horizontal=False),
                        _side_coverage(opened_v, top, bottom, right, horizontal=False),
                    )
                    score = float(min(covs))
                    area = (bottom - top) * (right - left)
                    if score < 0.55:
                        continue
                    # Bar edges and grid remnants can outscore a slightly rotated
                    # spine. Among boxes that still sit on ink, take the outer one.
                    if best is None or area > best[2] or (area == best[2] and score > best[1]):
                        best = ((left, top, right, bottom), score, area)
    if best is None:
        return None
    return best[0], best[1]


def _line_from_segment(x1: float, y1: float, x2: float, y2: float) -> tuple[np.ndarray, np.ndarray]:
    point = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0], dtype=np.float64)
    direction = np.array([x2 - x1, y2 - y1], dtype=np.float64)
    norm = float(np.hypot(direction[0], direction[1]))
    if norm == 0.0:
        direction = np.array([1.0, 0.0])
    else:
        direction = direction / norm
    return point, direction


def _cluster_segments(
    segments: list[tuple[float, float, float, float, float]],
    *,
    horizontal: bool,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if not segments:
        return []
    angles = [math.atan2(s[3] - s[1], s[2] - s[0]) for s in segments]
    median = float(np.median(angles))
    normal = np.array([-math.sin(median), math.cos(median)], dtype=np.float64)
    offsets = []
    for x1, y1, x2, y2, _length in segments:
        mid = np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])
        offsets.append(float(mid @ normal))
    order = np.argsort(offsets)
    groups: list[list[int]] = [[int(order[0])]]
    for idx in order[1:]:
        if abs(offsets[int(idx)] - offsets[groups[-1][-1]]) <= 5.0:
            groups[-1].append(int(idx))
        else:
            groups.append([int(idx)])
    lines: list[tuple[np.ndarray, np.ndarray]] = []
    for group in groups:
        pts = []
        for idx in group:
            x1, y1, x2, y2, _length = segments[idx]
            pts.append([x1, y1])
            pts.append([x2, y2])
        arr = np.asarray(pts, dtype=np.float64)
        mean = arr.mean(axis=0)
        _, _, vh = np.linalg.svd(arr - mean, full_matrices=False)
        direction = vh[0]
        if horizontal and direction[0] < 0:
            direction = -direction
        if not horizontal and direction[1] < 0:
            direction = -direction
        lines.append((mean, direction))
    return lines


def _intersect(p1: np.ndarray, d1: np.ndarray, p2: np.ndarray, d2: np.ndarray) -> np.ndarray | None:
    matrix = np.column_stack([d1, -d2])
    try:
        solved = np.linalg.solve(matrix, p2 - p1)
    except np.linalg.LinAlgError:
        return None
    scale = float(solved[0])
    point = np.array(
        [float(p1[0]) + scale * float(d1[0]), float(p1[1]) + scale * float(d1[1])],
        dtype=np.float64,
    )
    return point


Quad = tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]


def _detect_hough(ink: np.ndarray, cfg: PipelineConfig) -> tuple[BBox, float, Quad] | None:
    height, width = ink.shape
    min_len = max(25, int(cfg.min_line_frac * min(height, width)))
    raw = cv2.HoughLinesP(
        ink,
        1,
        np.pi / 180.0,
        threshold=max(20, min_len // 2),
        minLineLength=min_len,
        maxLineGap=8,
    )
    if raw is None:
        return None
    horiz: list[tuple[float, float, float, float, float]] = []
    vert: list[tuple[float, float, float, float, float]] = []
    for x1, y1, x2, y2 in np.asarray(raw).reshape(-1, 4):
        angle = abs(math.degrees(math.atan2(float(y2 - y1), float(x2 - x1))))
        angle = min(angle, 180.0 - angle)
        length = float(math.hypot(x2 - x1, y2 - y1))
        seg = (float(x1), float(y1), float(x2), float(y2), length)
        if angle < 25.0:
            horiz.append(seg)
        elif angle > 65.0:
            vert.append(seg)
    h_lines = _cluster_segments(horiz, horizontal=True)
    v_lines = _cluster_segments(vert, horizontal=False)
    if len(h_lines) < 2 or len(v_lines) < 2:
        return None
    best: (
        tuple[
            float,
            BBox,
            tuple[
                tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]
            ],
        ]
        | None
    ) = None
    for hp, hd in h_lines:
        for hq, hd2 in h_lines:
            for vp, vd in v_lines:
                for vq, vd2 in v_lines:
                    corners = [
                        _intersect(hp, hd, vp, vd),
                        _intersect(hp, hd, vq, vd2),
                        _intersect(hq, hd2, vq, vd2),
                        _intersect(hq, hd2, vp, vd),
                    ]
                    if any(c is None for c in corners):
                        continue
                    pts = [c for c in corners if c is not None]
                    xs = [float(p[0]) for p in pts]
                    ys = [float(p[1]) for p in pts]
                    if max(xs) - min(xs) < 0.12 * width or max(ys) - min(ys) < 0.12 * height:
                        continue
                    # Order tl, tr, br, bl.
                    ordered = sorted(pts, key=lambda p: (float(p[1]), float(p[0])))
                    top = sorted(ordered[:2], key=lambda p: float(p[0]))
                    bot = sorted(ordered[2:], key=lambda p: float(p[0]))
                    quad = (top[0], top[1], bot[1], bot[0])
                    x0 = int(np.clip(round(min(xs)), 0, width - 1))
                    x1 = int(np.clip(round(max(xs)), 0, width - 1))
                    y0 = int(np.clip(round(min(ys)), 0, height - 1))
                    y1 = int(np.clip(round(max(ys)), 0, height - 1))
                    if x1 - x0 < 20 or y1 - y0 < 20:
                        continue
                    # Border support on the AABB is a reasonable score for small rotations.
                    support = 0.0
                    samples = 0
                    for a, b in zip(quad, (quad[1], quad[2], quad[3], quad[0]), strict=True):
                        for t in np.linspace(0.05, 0.95, 12):
                            col = int(round(float(a[0]) * (1 - t) + float(b[0]) * t))
                            row = int(round(float(a[1]) * (1 - t) + float(b[1]) * t))
                            if 0 <= row < height and 0 <= col < width:
                                patch = ink[max(0, row - 2) : row + 3, max(0, col - 2) : col + 3]
                                support += float(np.any(patch > 0))
                                samples += 1
                    score = support / samples if samples else 0.0
                    area = (x1 - x0) * (y1 - y0)
                    if score < 0.45:
                        continue
                    if (
                        best is None
                        or score > best[0] + 0.05
                        or (
                            abs(score - best[0]) <= 0.05
                            and area > (best[1][2] - best[1][0]) * (best[1][3] - best[1][1])
                        )
                    ):
                        corner_t: Quad = (
                            (float(quad[0][0]), float(quad[0][1])),
                            (float(quad[1][0]), float(quad[1][1])),
                            (float(quad[2][0]), float(quad[2][1])),
                            (float(quad[3][0]), float(quad[3][1])),
                        )
                        best = (score, (x0, y0, x1, y1), corner_t)
    if best is None:
        return None
    return best[1], best[0], best[2]


def detect_plot_area(rgb: np.ndarray, config: PipelineConfig | None = None) -> PlotArea | Abstain:
    cfg = config or PipelineConfig()
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        return Abstain("plot_area", "bad_image")
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    if height < 30 or width < 30:
        return Abstain("plot_area", "image_too_small")
    ink = _ink(gray, cfg.ink_threshold)
    if int(ink.sum()) < 50:
        return Abstain("plot_area", "no_axis_found")
    min_len_h = max(25, int(cfg.min_line_frac * width))
    min_len_v = max(25, int(cfg.min_line_frac * height))
    opened_h = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (min_len_h, 1))
    )
    opened_v = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_len_v))
    )
    aligned = _best_aligned(opened_h, opened_v)
    if aligned is not None and aligned[1] >= 0.55:
        left, top, right, bottom = aligned[0]
        corners = (
            (float(left), float(top)),
            (float(right), float(top)),
            (float(right), float(bottom)),
            (float(left), float(bottom)),
        )
        return PlotArea(
            bbox=(int(left), int(top), int(right), int(bottom)),
            x_axis_px=float(bottom),
            y_axis_px=float(left),
            score=float(aligned[1]),
            corners=corners,
        )
    hough = _detect_hough(ink, cfg)
    if hough is None:
        return Abstain("plot_area", "no_axis_found")
    bbox, score, corners = hough
    if len(corners) != 4:
        return Abstain("plot_area", "no_axis_found")
    tl, tr, br, bl = corners
    return PlotArea(
        bbox=bbox,
        x_axis_px=float((bl[1] + br[1]) / 2.0),
        y_axis_px=float((tl[0] + bl[0]) / 2.0),
        score=float(score),
        corners=(tl, tr, br, bl),
    )
