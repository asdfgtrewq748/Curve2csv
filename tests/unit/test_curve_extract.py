"""A sine wave stays within 1% NRMSE, and an occluding label becomes a gap."""

from __future__ import annotations

import numpy as np
from tests.helpers import line_figure

from curve2csv.api import extract
from curve2csv.types import PointFlag


def test_sine_nrmse_and_occluded_gap() -> None:
    x = np.linspace(0.0, 6.0 * np.pi, 360)
    y = np.sin(x)
    image, axes = line_figure(x, [(y, "#d62728")], occlude=(6.0, 9.0))
    result = extract(image, axes=axes)
    assert result.series
    series = result.series[0]
    emitted = [(p.x, p.y) for p in series.points if p.x is not None and p.y is not None]
    assert emitted
    px = np.array([item[0] for item in emitted])
    py = np.array([item[1] for item in emitted])
    order = np.argsort(px)
    px, py = px[order], py[order]
    sample_x = np.linspace(0.2, 6.0 * np.pi - 0.2, 80)
    # Skip the occluded interval when scoring error.
    keep = (sample_x < 6.0) | (sample_x > 9.0)
    sample_x = sample_x[keep]
    truth = np.sin(sample_x)
    pred = np.interp(sample_x, px, py)
    ry = 2.0
    nrmse = float(np.sqrt(np.mean(((pred - truth) / ry) ** 2)))
    assert nrmse <= 0.01
    assert any(lo <= 6.5 <= hi or (lo <= 6.2 and hi >= 8.5) for lo, hi in series.gaps)
    for point in series.points:
        if point.x is None:
            continue
        if 6.0 <= point.x <= 9.0:
            assert point.flags != PointFlag.NONE
