"""Debug CLI and image-loader edges."""

from __future__ import annotations

import csv
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
    blank = tmp_path / "blank.png"
    save_image(blank, np.full((80, 80, 3), 255, dtype=np.uint8))
    assert main(["extract", str(blank), "-o", str(out)]) == 2


def test_extract_subcommand_clear_range_writes_empty_rows(tmp_path: Path) -> None:
    x = np.linspace(0.0, 3.0, 120)
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
            "--clear-range",
            "1:2",
        ]
    )
    assert code == 0
    with (out / "fig.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cleared = [row for row in rows if row["status"] == "empty"]
    assert cleared
    assert all(row["x"] == "" and row["y"] == "" for row in cleared)
    assert all(row["interpolated"] == "0" for row in cleared)


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


def test_headless_smoke_prints_ok(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    x = np.linspace(0.0, 3.0, 40)
    image, _axes = line_figure(x, [(np.sin(x), "#d62728")])
    image_path = tmp_path / "smoke.png"
    save_image(image_path, image)
    code = main(["--headless-smoke", str(image_path), "-o", str(tmp_path / "out")])
    captured = capsys.readouterr()
    assert code == 0
    assert "SMOKE_OK" in captured.out
    assert (tmp_path / "out" / "smoke.csv").is_file()


def test_pdf_page_and_series_rename(tmp_path: Path) -> None:
    pypdfium2 = pytest.importorskip("pypdfium2")
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    from matplotlib.backends.backend_pdf import PdfPages

    pdf_path = tmp_path / "pages.pdf"
    with PdfPages(pdf_path) as pdf:
        for color in ("#ffffff", "#000000"):
            fig = matplotlib.figure.Figure()
            ax = fig.add_subplot(1, 1, 1)
            ax.plot([0, 1], [0, 1], color=color)
            pdf.savefig(fig)
    first = load_image(pdf_path, page=1)
    second = load_image(pdf_path, page=2)
    assert first.page == 1 and second.page == 2
    assert first.rgb.shape[2] == 3
    assert int(first.rgb.mean()) != int(second.rgb.mean())
    with pytest.raises(InputError):
        load_image(pdf_path, page=3)
    del pypdfium2

    from curve2csv.io.labels import rename_series_label

    csv_path = tmp_path / "fig.csv"
    json_path = tmp_path / "fig.json"
    csv_path.write_text(
        "series_id,series_label,kind,x,y,confidence,flags,px,py\ns1,,line,0,1,1,,1,2\n",
        encoding="utf-8",
    )
    json_path.write_text('{"series": [{"series_id": "s1", "label": ""}]}\n', encoding="utf-8")
    rename_series_label(csv_path, json_path, "s1", "measured")
    assert "s1,measured,line" in csv_path.read_text(encoding="utf-8")
    assert '"label": "measured"' in json_path.read_text(encoding="utf-8")
    with pytest.raises(InputError):
        rename_series_label(csv_path, json_path, "s1", "a,b")
