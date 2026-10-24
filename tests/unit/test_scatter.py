"""A handful of separated round markers are recovered."""

from __future__ import annotations

import numpy as np
from tests.helpers import scatter_figure

from curve2csv.api import extract


def test_scatter_recovers_markers() -> None:
    image, axes, x, y = scatter_figure()
    result = extract(image, axes=axes)
    assert result.series
    assert result.series[0].kind == "scatter"
    pred = np.array([(p.x, p.y) for p in result.series[0].points if p.x is not None])
    assert len(pred) >= 8
    matched = 0
    for gx, gy in zip(x, y, strict=True):
        if np.min(np.hypot(pred[:, 0] - gx, pred[:, 1] - gy)) <= 0.35:
            matched += 1
    assert matched >= 10
