"""Bar heights track the source values."""

from __future__ import annotations

import numpy as np
from tests.helpers import bar_figure

from curve2csv.api import extract


def test_bar_heights() -> None:
    image, axes, heights = bar_figure()
    result = extract(image, axes=axes)
    bars = [series for series in result.series if series.kind == "bar"]
    assert bars
    pred = np.array([(p.x, p.y) for series in bars for p in series.points if p.y is not None])
    assert len(pred) >= 3
    span = float(heights.max())
    errors = []
    for index, height in enumerate(heights):
        nearest = int(np.argmin(np.abs(pred[:, 0] - index)))
        if abs(pred[nearest, 0] - index) <= 0.35:
            errors.append(abs(pred[nearest, 1] - height) / span)
    assert len(errors) >= 3
    assert float(np.median(errors)) <= 0.01
