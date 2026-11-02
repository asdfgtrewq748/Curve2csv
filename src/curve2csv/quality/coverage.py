"""Self-reported x coverage from emitted points and gaps."""

from __future__ import annotations

from curve2csv.types import Series


def series_coverage(series: Series) -> float:
    xs = [point.x for point in series.points if point.x is not None]
    if len(xs) < 2:
        return 0.0
    span = max(xs) - min(xs)
    if span <= 0:
        return 0.0
    gap = sum(max(0.0, hi - lo) for lo, hi in series.gaps)
    return float(max(0.0, min(1.0, 1.0 - gap / span)))
