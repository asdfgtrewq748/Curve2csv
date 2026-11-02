"""Flag helpers. ``INTERPOLATED`` is rejected from the main output."""

from __future__ import annotations

from curve2csv.types import PointFlag, Series


def assert_no_interpolation(series: list[Series]) -> None:
    for item in series:
        for point in item.points:
            if PointFlag.INTERPOLATED in point.flags:
                raise RuntimeError("main output must not contain INTERPOLATED points")


def strip_interpolation(series: list[Series]) -> list[Series]:
    """Defensive copy that drops the forbidden flag and nulls any such point."""

    cleaned: list[Series] = []
    for item in series:
        points = []
        for point in item.points:
            if PointFlag.INTERPOLATED in point.flags:
                flags = point.flags & ~PointFlag.INTERPOLATED
                flags |= PointFlag.LOW_CONFIDENCE
                points.append(
                    type(point)(
                        x=None,
                        y=None,
                        px=point.px,
                        py=point.py,
                        confidence=min(point.confidence, 0.2),
                        flags=flags,
                    )
                )
            else:
                points.append(point)
        cleaned.append(
            Series(
                series_id=item.series_id,
                kind=item.kind,
                label=item.label,
                color_hex=item.color_hex,
                points=points,
                gaps=list(item.gaps),
                coverage=item.coverage,
                confidence=item.confidence,
                style=item.style,
            )
        )
    return cleaned
