"""Tab10 splits; near-duplicate colors merge or stay pure."""

from __future__ import annotations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from curve2csv.config import PipelineConfig
from curve2csv.separate.color import separate_series
from curve2csv.separate.foreground import build_masks
from curve2csv.types import PlotArea


def _figure(colors: list[tuple[int, int, int]]) -> tuple[np.ndarray, PlotArea]:
    image = np.full((160, 240, 3), 255, dtype=np.uint8)
    # Axis spines so the plot box is not required by separation itself.
    image[20, 15:225] = 0
    image[140, 15:225] = 0
    image[20:141, 15] = 0
    image[20:141, 224] = 0
    for index, color in enumerate(colors):
        row = 40 + index * 28
        image[row : row + 3, 30:210] = color
    area = PlotArea(bbox=(15, 20, 224, 140), x_axis_px=140.0, y_axis_px=15.0, score=1.0)
    return image, area


def test_three_tab10_colors_become_three_series() -> None:
    colors = [(214, 39, 40), (31, 119, 180), (44, 160, 44)]
    image, area = _figure(colors)
    masks = build_masks(image, area, PipelineConfig())
    series = separate_series(image, masks, PipelineConfig())
    assert len(series) == 3


def test_close_colors_merge_or_stay_pure() -> None:
    first = (176, 48, 48)
    second = (180, 52, 50)
    lab = rgb2lab(np.array([[first, second]], dtype=np.uint8) / 255.0)
    delta = float(deltaE_ciede2000(lab[:, 0:1, :], lab[:, 1:2, :])[0, 0])
    assert delta < 5.0
    image, area = _figure([first, second])
    masks = build_masks(image, area, PipelineConfig())
    series = separate_series(image, masks, PipelineConfig())
    assert series
    if len(series) == 1:
        assert series[0].ambiguous
        return
    # Separated colors must not share the other's ink.
    bands = [(40, 43), (68, 71)]
    for item in series:
        counts = [int(item.mask[row0:row1, 30:210].sum()) for row0, row1 in bands]
        owned = sum(counts)
        assert owned > 0
        assert max(counts) / owned >= 0.9
