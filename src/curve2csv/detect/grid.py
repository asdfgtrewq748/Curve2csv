"""Grid-line mask. Light-gray grids are included; dark spines are left to axes."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.config import PipelineConfig
from curve2csv.types import BBox


def detect_grid_mask(
    rgb: np.ndarray, bbox: BBox, config: PipelineConfig | None = None
) -> np.ndarray:
    cfg = config or PipelineConfig()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    mask = np.zeros((height, width), dtype=bool)
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(width, x1), min(height, y1)
    if x1 - x0 < 10 or y1 - y0 < 10:
        return mask
    # Grid ink is darker than the background but the long-line test is restricted
    # to the plot interior so the spines themselves are not required.
    interior = gray[y0 + 2 : y1 - 2, x0 + 2 : x1 - 2]
    if interior.size == 0:
        return mask
    grid_ink = ((interior < cfg.ink_threshold + 50) & (interior > 40)).astype(np.uint8) * 255
    min_h = max(15, (x1 - x0) // 5)
    min_v = max(15, (y1 - y0) // 5)
    horiz = cv2.morphologyEx(
        grid_ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (min_h, 1))
    )
    vert = cv2.morphologyEx(
        grid_ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_v))
    )
    local = (horiz > 0) | (vert > 0)
    mask[y0 + 2 : y1 - 2, x0 + 2 : x1 - 2] = local
    return mask
