"""Public ``extract`` entry point."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from curve2csv.config import PipelineConfig
from curve2csv.io.export import export_all
from curve2csv.io.image import load_image
from curve2csv.pipeline import run_pipeline
from curve2csv.types import AxesOverride, ExtractionResult


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
