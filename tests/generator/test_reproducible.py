"""The same seed renders the same bytes, and probes sit on the stored pixels."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from benchmarks.generator.render import render_sample
from benchmarks.generator.spec import make_spec


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_same_seed_same_manifest_hash(tmp_path: Path) -> None:
    spec = make_spec("smoke", 4, 20261025)
    first = render_sample(spec, tmp_path / "a")
    second = render_sample(spec, tmp_path / "b")
    assert first["sha256"] == second["sha256"]
    assert _sha(tmp_path / "a" / "img.png") == _sha(tmp_path / "b" / "img.png")


def test_probe_reprojection_within_half_pixel(tmp_path: Path) -> None:
    spec = make_spec("dev", 0, 20261025)
    document = render_sample(spec, tmp_path)
    probes = document["probes"]
    design = np.array([[p["px"], p["py"], 1.0] for p in probes], dtype=np.float64)
    target_x = np.array([p["x"] for p in probes], dtype=np.float64)
    target_y = np.array([p["y"] for p in probes], dtype=np.float64)
    coef_x, _, _, _ = np.linalg.lstsq(design, target_x, rcond=None)
    coef_y, _, _, _ = np.linalg.lstsq(design, target_y, rcond=None)
    # Project data back through the fitted pixel map and compare with stored pixels.
    # Solve the 2x2 linear system for each probe.
    worst = 0.0
    for probe in probes:
        system = np.array([[coef_x[0], coef_x[1]], [coef_y[0], coef_y[1]]], dtype=np.float64)
        rhs = np.array(
            [probe["x"] - coef_x[2], probe["y"] - coef_y[2]],
            dtype=np.float64,
        )
        px, py = np.linalg.solve(system, rhs)
        worst = max(worst, abs(px - probe["px"]), abs(py - probe["py"]))
    assert worst <= 0.5
