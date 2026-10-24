"""Ground-truth polylines land on the rendered ink."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from benchmarks.generator.render import render_sample
from benchmarks.generator.spec import make_spec


def _hex_rgb(value: str) -> np.ndarray:
    return np.array([int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)], dtype=np.int16)


def test_polyline_chamfer_within_one_pixel(tmp_path: Path) -> None:
    spec = make_spec("dev", 0, 20261025)
    document = render_sample(spec, tmp_path)
    clean = np.asarray(Image.open(tmp_path / "clean.png"))
    series = document["series"][0]
    color = _hex_rgb(str(series["color"]))
    diff = np.abs(clean.astype(np.int16) - color).sum(axis=2)
    ink = np.argwhere(diff <= 80)
    assert ink.size
    tree = cKDTree(ink[:, ::-1].astype(np.float64))  # row, col -> x, y
    polyline = np.asarray(series["polyline_clean"], dtype=np.float64)
    dist, _ = tree.query(polyline, k=1)
    assert float(np.mean(dist)) <= 1.0
