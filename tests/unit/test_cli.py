"""Debug CLI and image-loader edges."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from tests.helpers import line_figure, save_image

from curve2csv.__main__ import main
from curve2csv.errors import InputError
from curve2csv.io.image import load_image


def test_cli_extracts(tmp_path: Path) -> None:
    x = np.linspace(0.0, 3.0, 40)
    image, axes = line_figure(x, [(np.sin(x), "#d62728")])
    image_path = tmp_path / "fig.png"
    save_image(image_path, image)
    payload = {
        "x": {
            "scale": "linear",
            "ticks": [{"px": t.px, "py": t.py, "value": t.value} for t in axes.x_ticks],
        },
        "y": {
            "scale": "log10",
            "ticks": [{"px": t.px, "py": t.py, "value": max(t.value, 0.1)} for t in axes.y_ticks],
        },
    }
    # log10 of non-positive values abstains; keep the file valid and use linear values
    # that are positive so the loader's log10 branch is executed.
    axes_path = tmp_path / "axes.json"
    axes_path.write_text(json.dumps(payload), encoding="utf-8")
    code = main([str(image_path), "--axes", str(axes_path), "--out", str(tmp_path / "out"), "-v"])
    assert code == 0
    assert (tmp_path / "out" / "fig.csv").is_file()


def test_extract_subcommand_uses_axis_limits(tmp_path: Path) -> None:
    x = np.linspace(0.0, 3.0, 40)
    image, _axes = line_figure(x, [(np.sin(x), "#d62728")])
    image_path = tmp_path / "fig.png"
    save_image(image_path, image)
    out = tmp_path / "out"
    code = main(
        [
            "extract",
            str(image_path),
            "-o",
            str(out),
            "--xmin",
            "0",
            "--xmax",
            "3",
            "--ymin",
            "-1.2",
            "--ymax",
            "1.2",
        ]
    )
    assert code == 0
    assert (out / "fig.csv").is_file()
    assert (out / "fig.overlay.png").is_file()
    assert main(["extract", str(image_path), "-o", str(out)]) == 2


def test_cli_rejects_bad_input(tmp_path: Path) -> None:
    axes_path = tmp_path / "axes.json"
    axes_path.write_text("[]", encoding="utf-8")
    missing = tmp_path / "missing.png"
    assert main([str(missing), "--axes", str(axes_path), "--out", str(tmp_path)]) == 2
    image = np.full((40, 40, 3), 255, dtype=np.uint8)
    image_path = tmp_path / "blank.png"
    save_image(image_path, image)
    axes_path.write_text(json.dumps({"x": {"ticks": [{"px": 1}]}}), encoding="utf-8")
    assert main([str(image_path), "--axes", str(axes_path), "--out", str(tmp_path)]) == 2


def test_loader_rgba_gray_and_errors(tmp_path: Path) -> None:
    rgba = np.zeros((16, 16, 4), dtype=np.uint8)
    rgba[..., 0] = 20
    rgba[..., 3] = 255
    loaded = load_image(rgba)
    assert loaded.rgb.shape == (16, 16, 3)
    gray = load_image(np.full((12, 12), 30, dtype=np.uint8))
    assert gray.rgb.shape[2] == 3
    with pytest.raises(InputError):
        load_image(np.zeros((8, 8, 2), dtype=np.uint8))
    with pytest.raises(InputError):
        load_image(tmp_path / "absent.png")
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(InputError):
        load_image(bad)
