"""Public ``extract`` entry point."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from curve2csv.calibrate.limits import axes_from_box
from curve2csv.config import PipelineConfig
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.errors import InputError
from curve2csv.io.export import export_all
from curve2csv.io.image import load_image
from curve2csv.pipeline import run_pipeline
from curve2csv.types import Abstain, AxesOverride, AxisScale, ExtractionResult


def extract(
    src: str | Path | NDArray[np.uint8],
    *,
    axes: AxesOverride | None = None,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Digitize one figure.

    When ``out`` is set, CSV, JSON, an overlay PNG, and a metrics file are written
    together. Passing no ``axes`` abstains from calibration (M1 does not read tick
    labels) and returns an empty series list rather than guessing values.
    """

    loaded = load_image(src)
    result = run_pipeline(loaded, axes=axes, config=config)
    if out is not None:
        export_all(result, Path(out))
    return result


def extract_with_limits(
    src: str | Path | NDArray[np.uint8],
    *,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    x_scale: AxisScale = AxisScale.LINEAR,
    y_scale: AxisScale = AxisScale.LINEAR,
    config: PipelineConfig | None = None,
    out: str | Path | None = None,
) -> ExtractionResult:
    """Digitize using the detected plot box and typed axis endpoints."""

    loaded = load_image(src)
    area = detect_plot_area(loaded.rgb, config)
    if isinstance(area, Abstain):
        raise InputError(f"plot area: {area.reason}")
    axes = axes_from_box(
        area.bbox,
        xmin=xmin,
        xmax=xmax,
        ymin=ymin,
        ymax=ymax,
        x_scale=x_scale,
        y_scale=y_scale,
    )
    result = run_pipeline(loaded, axes=axes, config=config)
    if out is not None:
        export_all(result, Path(out))
    return result
