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


def assign_segment_ids(series: list[Series]) -> list[Series]:
    """Number contiguous line runs, breaking on plain empty columns.

    A short occlusion bridge is inserted as adjacent columns, so it stays in
    the same segment. An empty point or a real hole (>= 2 px between emitted
    columns) starts the next segment. Scatter and bar points keep segment 0.
    """

    from dataclasses import replace

    for item in series:
        if item.kind != "line" or not item.points:
            item.points = [replace(point, segment_id=0) for point in item.points]
            continue
        ordered = sorted(item.points, key=lambda point: (point.px, point.py))
        numbered = []
        segment = -1
        previous_px: float | None = None
        previous_empty = True
        for point in ordered:
            empty = point.status == "empty"
            starts = previous_px is None or point.px - previous_px > 1.6 or empty or previous_empty
            if starts:
                segment += 1
            numbered.append(replace(point, segment_id=segment))
            previous_px = point.px
            previous_empty = empty
        item.points = numbered
    return series
