"""Public datatypes for the digitizing pipeline.

Pixel coordinates are continuous image coordinates: pixel index ``i`` has center
``i + 0.5``, origin at the top-left, ``x`` to the right and ``y`` downward.
That convention matches Matplotlib's display ``x`` and ``height - display_y``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, Flag
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 (original pixels, right/bottom open)

SCHEMA_VERSION = "1.0"


class AxisScale(str, Enum):
    LINEAR = "linear"
    LOG10 = "log10"


class PointFlag(Flag):
    NONE = 0
    LOW_CONFIDENCE = 1
    AMBIGUOUS_SERIES = 2
    NEAR_TEXT = 4
    NEAR_GRID = 8
    EDGE_OF_PLOT = 16
    THICK_SEGMENT = 32
    MANUAL = 64
    INTERPOLATED = 128


def flag_names(flags: PointFlag) -> list[str]:
    if flags == PointFlag.NONE:
        return []
    value = flags.value
    names: list[str] = []
    for member in PointFlag:
        bit = member.value
        if bit and (value & bit) == bit and member.name is not None:
            names.append(member.name)
    return names


@dataclass(frozen=True)
class Abstain:
    stage: str
    reason: str


@dataclass(frozen=True)
class LoadedImage:
    rgb: NDArray[np.uint8]
    source: str
    sha256: str
    page: int | None = None
    dpi: float | None = None

    @property
    def height(self) -> int:
        return int(self.rgb.shape[0])

    @property
    def width(self) -> int:
        return int(self.rgb.shape[1])


@dataclass(frozen=True)
class PlotArea:
    bbox: BBox
    x_axis_px: float
    y_axis_px: float
    score: float
    # Four corners (tl, tr, br, bl) in continuous pixels. Axis-aligned when unused.
    corners: (
        tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]
        | None
    ) = None


@dataclass(frozen=True)
class Tick:
    axis: str
    px: float
    value: float | None
    text: str | None = None
    ocr_conf: float | None = None
    py: float | None = None
    source: str = "detected"


@dataclass(frozen=True)
class TickInput:
    """One sidecar or manual tick. ``px``/``py`` are continuous image coordinates."""

    px: float
    value: float
    py: float | None = None


@dataclass(frozen=True)
class AxesOverride:
    x_ticks: tuple[TickInput, ...]
    y_ticks: tuple[TickInput, ...]
    x_scale: AxisScale = AxisScale.LINEAR
    y_scale: AxisScale = AxisScale.LINEAR
    source: str = "manual"


@dataclass(frozen=True)
class AxisCalibration:
    axis: str
    scale: AxisScale
    a: float
    b: float
    inverted: bool
    residual_rel: float
    n_ticks_used: int
    source: str
    # Unit direction of the axis parameter. ``t = px * dir_x + py * dir_y``.
    dir_x: float = 1.0
    dir_y: float = 0.0

    def _target_to_data(self, target: NDArray[np.float64]) -> NDArray[np.float64]:
        if self.scale is AxisScale.LOG10:
            return np.power(10.0, target)
        return target

    def _data_to_target(self, values: NDArray[np.float64]) -> NDArray[np.float64]:
        if self.scale is AxisScale.LOG10:
            return np.log10(values)
        return values

    def px_to_data(self, px: NDArray[np.float64]) -> NDArray[np.float64]:
        target = self.a * np.asarray(px, dtype=np.float64) + self.b
        return self._target_to_data(target)

    def data_to_px(self, values: NDArray[np.float64]) -> NDArray[np.float64]:
        target = self._data_to_target(np.asarray(values, dtype=np.float64))
        return (target - self.b) / self.a


class PixelMapper(Protocol):
    def pixel_to_data(self, col: float, row: float) -> tuple[float, float]: ...

    def data_to_pixel(self, x: float, y: float) -> tuple[float, float]: ...


@dataclass(frozen=True)
class Masks:
    foreground: NDArray[np.bool_]
    text: NDArray[np.bool_]
    grid: NDArray[np.bool_]
    legend: NDArray[np.bool_]
    axes: NDArray[np.bool_]


@dataclass(frozen=True)
class SeriesMask:
    series_id: str
    color_lab: tuple[float, float, float] | None
    style: str | None
    mask: NDArray[np.bool_]
    separation_score: float
    ambiguous: bool = False


@dataclass(frozen=True)
class DataPoint:
    x: float | None
    y: float | None
    px: float
    py: float
    confidence: float
    flags: PointFlag


@dataclass
class Series:
    series_id: str
    kind: str
    label: str | None
    color_hex: str | None
    points: list[DataPoint]
    gaps: list[tuple[float, float]]
    coverage: float
    confidence: float
    style: str | None = "solid"


@dataclass
class ExtractionResult:
    schema_version: str
    source: LoadedImage
    plot_area: PlotArea | Abstain
    calibration: dict[str, AxisCalibration | Abstain]
    series: list[Series]
    image_confidence: float
    abstentions: list[Abstain]
    diagnostics: dict[str, object] = field(default_factory=dict)
    mapper: PixelMapper | None = field(default=None, repr=False, compare=False)
    config_hash: str = ""

    def pixel_to_data(self, col: float, row: float) -> tuple[float, float] | None:
        if self.mapper is not None:
            return self.mapper.pixel_to_data(col, row)
        x_cal = self.calibration.get("x")
        y_cal = self.calibration.get("y")
        if not isinstance(x_cal, AxisCalibration) or not isinstance(y_cal, AxisCalibration):
            return None
        dx = float(x_cal.px_to_data(np.asarray([col], dtype=np.float64))[0])
        dy = float(y_cal.px_to_data(np.asarray([row], dtype=np.float64))[0])
        return dx, dy

    def to_csv(self, path: str | Path) -> None:
        from curve2csv.io.export import write_csv

        write_csv(self, Path(path))

    def to_json(self, path: str | Path) -> None:
        from curve2csv.io.export import write_json

        write_json(self, Path(path))

    def overlay(self, path: str | Path) -> None:
        from curve2csv.quality.overlay import write_overlay

        write_overlay(self, Path(path))

    def metrics(self) -> dict[str, object]:
        n_points = 0
        n_flagged = 0
        n_abstained = 0
        for series in self.series:
            for point in series.points:
                n_points += 1
                if point.flags != PointFlag.NONE:
                    n_flagged += 1
                if point.x is None or point.y is None:
                    n_abstained += 1
        return {
            "n_points": n_points,
            "n_flagged": n_flagged,
            "n_abstained": n_abstained,
            "n_series": len(self.series),
            "image_confidence": self.image_confidence,
        }
