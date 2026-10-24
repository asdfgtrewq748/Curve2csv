"""Assemble foreground, text, grid, legend, and axis masks."""

from __future__ import annotations

import cv2
import numpy as np

from curve2csv.color_math import rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.detect.grid import detect_grid_mask
from curve2csv.detect.text import detect_legend_mask, detect_text_mask
from curve2csv.types import Masks, PlotArea


def chromatic_mask(rgb: np.ndarray, chroma_min: float) -> np.ndarray:
    lab = rgb2lab(rgb)
    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    lightness = lab[:, :, 0]
    mask = (chroma >= chroma_min) & (lightness > 8.0) & (lightness < 98.0)
    return np.asarray(mask, dtype=bool)


def build_masks(rgb: np.ndarray, area: PlotArea, config: PipelineConfig | None = None) -> Masks:
    cfg = config or PipelineConfig()
    height, width = rgb.shape[:2]
    x0, y0, x1, y1 = area.bbox
    inside = np.zeros((height, width), dtype=bool)
    xa, ya = max(0, x0 + cfg.inset_px), max(0, y0 + cfg.inset_px)
    xb, yb = min(width, x1 - cfg.inset_px), min(height, y1 - cfg.inset_px)
    if xb > xa and yb > ya:
        inside[ya:yb, xa:xb] = True
    text = detect_text_mask(rgb, area.bbox, cfg)
    grid = detect_grid_mask(rgb, area.bbox, cfg)
    legend = detect_legend_mask(rgb, area.bbox, cfg)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    ink = gray < cfg.ink_threshold
    axes = np.zeros((height, width), dtype=bool)
    band = cfg.edge_band_px
    axes[max(0, y0 - band) : min(height, y0 + band + 1), max(0, x0) : min(width, x1)] = True
    axes[max(0, y1 - band) : min(height, y1 + band + 1), max(0, x0) : min(width, x1)] = True
    axes[max(0, y0) : min(height, y1), max(0, x0 - band) : min(width, x0 + band + 1)] = True
    axes[max(0, y0) : min(height, y1), max(0, x1 - band) : min(width, x1 + band + 1)] = True
    axes &= ink
    foreground = chromatic_mask(rgb, cfg.chroma_min) & inside & ~legend
    return Masks(foreground=foreground, text=text, grid=grid, legend=legend, axes=axes)
