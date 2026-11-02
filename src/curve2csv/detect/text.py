"""Text-block and legend-frame masks without OCR.

Text is dark, low-chroma connected components that are not long rules. Legend
frames are small rectangles inside the plot; masking them keeps legend swatches
out of the data.
"""

from __future__ import annotations

import cv2
import numpy as np
from skimage.color import rgb2lab

from curve2csv.config import PipelineConfig
from curve2csv.types import BBox


def detect_text_mask(
    rgb: np.ndarray, bbox: BBox, config: PipelineConfig | None = None
) -> np.ndarray:
    _ = config or PipelineConfig()
    lab = rgb2lab(rgb)
    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dark = (gray < 80) & (chroma < 18)
    height, width = gray.shape
    # Remove long lines so spines and underlines are not called text.
    ink = dark.astype(np.uint8) * 255
    long_h = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, width // 20), 1))
    )
    long_v = cv2.morphologyEx(
        ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, height // 20)))
    )
    glyphs = dark & ~(long_h > 0) & ~(long_v > 0)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(glyphs.astype(np.uint8), connectivity=8)
    mask = np.zeros((height, width), dtype=bool)
    for idx in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < 8 or area > 4000:
            continue
        if h < 4 or h > 48 or w < 2 or w > 240:
            continue
        if w / max(h, 1) > 14:
            continue
        mask[labels == idx] = True
    if mask.any():
        mask = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=1) > 0
    return mask


def detect_legend_mask(
    rgb: np.ndarray, bbox: BBox, config: PipelineConfig | None = None
) -> np.ndarray:
    """Return an empty legend mask.

    A frame detector that treats a light rectangle as a legend also matches the
    plot background and deletes real data. Legend swatches are removed later as
    short components, and an opaque legend already leaves a gap in the ink.
    """

    _ = (bbox, config)
    return np.zeros(rgb.shape[:2], dtype=bool)
