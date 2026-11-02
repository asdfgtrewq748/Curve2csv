"""Public extract() returns a result and writes a non-empty overlay."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from tests.helpers import line_figure

from curve2csv.api import extract
from curve2csv.types import ExtractionResult


def test_extract_writes_overlay(tmp_path: Path) -> None:
    x = np.linspace(0.0, 2.0, 40)
    image, axes = line_figure(x, [(x**2, "#ff7f0e")])
    result = extract(image, axes=axes, out=tmp_path)
    assert isinstance(result, ExtractionResult)
    overlay = tmp_path / "extraction.overlay.png"
    assert overlay.is_file()
    assert overlay.stat().st_size > 32
