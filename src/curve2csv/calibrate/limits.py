"""Build a two-tick calibration from axis limits and a plot box.

The on-device app and the ``extract`` command use this when the reader types
the axis endpoints instead of supplying a tick file. The bottom-left of the
box is ``(xmin, ymin)`` and the top-right is ``(xmax, ymax)``.
"""

from __future__ import annotations

from curve2csv.types import AxesOverride, AxisScale, BBox, TickInput


def axes_from_box(
    bbox: BBox,
    *,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    x_scale: AxisScale = AxisScale.LINEAR,
    y_scale: AxisScale = AxisScale.LINEAR,
) -> AxesOverride:
    x0, y0, x1, y1 = bbox
    return AxesOverride(
        x_ticks=(
            TickInput(px=float(x0), py=float(y1), value=float(xmin)),
            TickInput(px=float(x1), py=float(y1), value=float(xmax)),
        ),
        y_ticks=(
            TickInput(px=float(x0), py=float(y1), value=float(ymin)),
            TickInput(px=float(x0), py=float(y0), value=float(ymax)),
        ),
        x_scale=x_scale,
        y_scale=y_scale,
        source="manual",
    )
