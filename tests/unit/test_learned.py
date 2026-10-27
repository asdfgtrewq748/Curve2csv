"""Learned extractor: checksum, fallback, and no interpolation."""

from __future__ import annotations

import numpy as np
import pytest
from tests.helpers import line_figure

from curve2csv.api import extract
from curve2csv.config import PipelineConfig
from curve2csv.separate.learned import segment_series, weights_ready
from curve2csv.types import PointFlag


def test_default_extractor_is_rules() -> None:
    config = PipelineConfig()
    assert config.extractor == "rules"


def test_weights_checksum_matches() -> None:
    assert weights_ready()


def test_bad_checksum_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("curve2csv.separate.learned.weights_ready", lambda: False)
    rgb = np.full((40, 40, 3), 255, np.uint8)
    assert segment_series(rgb, (0, 0, 40, 40), PipelineConfig(extractor="learned")) is None


def test_rules_path_stays_default() -> None:
    x = np.linspace(0.0, 6.0, 80)
    image, axes = line_figure(x, [(np.sin(x), "#d62728")])
    result = extract(image, axes=axes)
    assert result.diagnostics.get("extractor") == "rules"


def test_learned_path_does_not_interpolate() -> None:
    x = np.linspace(0.0, 6.0, 100)
    image, axes = line_figure(x, [(np.sin(x), "#d62728"), (np.cos(x), "#1f77b4")])
    result = extract(
        image,
        axes=axes,
        config=PipelineConfig(extractor="learned", learned_threshold=0.35, learned_tau=0.7),
    )
    assert result.diagnostics.get("extractor") == "learned"
    for series in result.series:
        for point in series.points:
            assert PointFlag.INTERPOLATED not in point.flags
