"""Flag helpers.

``INTERPOLATED`` is allowed only on an occlusion bridge: another series covers
a hole no wider than the stroke plus a few pixels, with this series' ink on
both sides. ``strip_interpolation`` keeps those points. ``assert_no_interpolation``
still rejects them, and the plain-gap tests use that assertion.
"""

from __future__ import annotations

from curve2csv.types import PointFlag, Series


def assert_no_interpolation(series: list[Series]) -> None:
    for item in series:
        for point in item.points:
            if PointFlag.INTERPOLATED in point.flags:
                raise RuntimeError("main output must not contain INTERPOLATED points")


def strip_interpolation(series: list[Series]) -> list[Series]:
    """Keep occlusion bridges. They are already marked ``INTERPOLATED``.

    Plain gaps never produce that flag. The points stay in the CSV and JSON
    with ``interpolated=1`` and are excluded from the strict score.
    """

    return series
