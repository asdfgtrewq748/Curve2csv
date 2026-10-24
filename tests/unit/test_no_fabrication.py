"""Occluded intervals are not filled, and INTERPOLATED never appears."""

from __future__ import annotations

import numpy as np
from tests.helpers import line_figure

from curve2csv.api import extract
from curve2csv.quality.flags import assert_no_interpolation
from curve2csv.types import PointFlag


def test_occlusion_is_not_invented() -> None:
    x = np.linspace(0.0, 10.0, 240)
    y = 0.4 * x
    image, axes = line_figure(x, [(y, "#1f77b4")], occlude=(3.0, 6.0))
    result = extract(image, axes=axes)
    assert_no_interpolation(result.series)
    assert result.series
    series = result.series[0]
    assert any(hi > lo and not (hi < 3.0 or lo > 6.0) for lo, hi in series.gaps)
    invented = 0
    for point in series.points:
        assert PointFlag.INTERPOLATED not in point.flags
        if point.x is None or point.y is None:
            continue
        if 3.2 <= point.x <= 5.8 and point.flags == PointFlag.NONE and point.confidence >= 0.5:
            invented += 1
    assert invented == 0
