"""Tick-mark detection along the spines. Values are filled in by calibration, not here."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.types import PlotArea, Tick


def _peaks_1d(signal: np.ndarray, min_distance: int, threshold: float) -> list[int]:
    if signal.size == 0:
        return []
    peaks: list[int] = []
    for idx in range(1, signal.size - 1):
        if signal[idx] < threshold:
            continue
        if signal[idx] >= signal[idx - 1] and signal[idx] >= signal[idx + 1]:
            if peaks and idx - peaks[-1] < min_distance:
                if signal[idx] > signal[peaks[-1]]:
                    peaks[-1] = idx
            else:
                peaks.append(idx)
    return peaks


def detect_ticks(
    rgb: np.ndarray,
    area: PlotArea,
    config: PipelineConfig | None = None,
) -> list[Tick]:
    """Detect tick marks just outside (and just inside) the spines.

    Matplotlib's default tick direction is outward, but inward ticks occur in
    published figures, so both bands are searched. Returned ticks have no values.
    """

    cfg = config or PipelineConfig()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    x0, y0, x1, y1 = area.bbox
    x0 = int(np.clip(x0, 0, width - 1))
    x1 = int(np.clip(x1, 0, width - 1))
    y0 = int(np.clip(y0, 0, height - 1))
    y1 = int(np.clip(y1, 0, height - 1))
    ink = gray < cfg.ink_threshold
    band = max(4, cfg.edge_band_px + 3)
    ticks: list[Tick] = []

    # X ticks: short vertical marks crossing the bottom spine.
    r0 = max(0, y1 - band)
    r1 = min(height, y1 + band + 1)
    if r1 > r0 and x1 > x0:
        col_score = ink[r0:r1, x0:x1].sum(axis=0).astype(np.float64)
        for col in _peaks_1d(col_score, min_distance=6, threshold=2.0):
            ticks.append(Tick(axis="x", px=float(x0 + col) + 0.5, value=None, py=float(y1) + 0.5))

    # Y ticks: short horizontal marks crossing the left spine.
    c0 = max(0, x0 - band)
    c1 = min(width, x0 + band + 1)
    if c1 > c0 and y1 > y0:
        row_score = ink[y0:y1, c0:c1].sum(axis=1).astype(np.float64)
        for row in _peaks_1d(row_score, min_distance=6, threshold=2.0):
            ticks.append(Tick(axis="y", px=float(x0) + 0.5, value=None, py=float(y0 + row) + 0.5))
    return ticks
