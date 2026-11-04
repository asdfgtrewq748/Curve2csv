"""Render the domain single-curve set (W3) from published numeric data.

Each ``sources/<slug>.csv`` holds points copied from an open dataset (see
``sources/sources.json`` and ``prep_sources.py``); nothing is digitized or
synthesized. This script re-plots each series in a journal-like style
(serif font, inward ticks, no grid, single-column sizes, some JPEG
degradation) and writes ``figures/<slug>.png``, ``gt/<slug>.json`` and
``manifest.json`` in the same schema as ``benchmarks/real``.

Split rule (fixed before any extraction score): sort slugs by
``sha256(slug)``; the first 8 are dev, the remaining 16 held-out.

    python -m benchmarks.domain.build
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "fonts" / "LiberationSerif-Regular.ttf"
N_DEV = 8


def _rng(slug: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(slug.encode()).hexdigest()[:12], 16))


def _nice_step(span: float) -> float:
    raw = span / 5.0
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * mag:
            return mult * mag
    return 10 * mag


def _limits(lo: float, hi: float, from_zero: bool) -> tuple[float, float]:
    if from_zero and lo >= 0 and lo < 0.35 * (hi - lo):
        lo = 0.0
    step = _nice_step(hi - lo)
    return math.floor(lo / step) * step, math.ceil(hi / step) * step


def _log_limits(lo: float, hi: float) -> tuple[float, float]:
    return 10 ** math.floor(math.log10(lo)), 10 ** math.ceil(math.log10(hi))


def _style(slug: str) -> dict[str, Any]:
    r = _rng(slug)
    return {
        "size_in": [(3.35, 2.6), (3.5, 2.8), (4.0, 3.0), (3.0, 2.4), (5.0, 3.6)][int(r.integers(5))],
        "dpi": int(r.choice([150, 200, 300])),
        "color": str(r.choice(["black", "black", "#404040", "#d62728", "#1f4e9c"])),
        "lw": float(r.choice([0.8, 1.0, 1.25, 1.5])),
        "marker": str(r.choice(["", "", "o", "s", "^"])),
        "mirror_ticks": bool(r.integers(2)),
        "legend": bool(r.integers(2)),
        "panel_label": bool(r.integers(2)),
        "jpeg_q": int(r.choice([0, 0, 92, 80, 65])),
        "font_pt": float(r.choice([8, 9, 10])),
    }


def render(slug: str, x: np.ndarray, y: np.ndarray, meta: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    st = _style(slug)
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams.update(
        {
            "font.family": "Liberation Serif",
            "mathtext.fontset": "stix",
            "font.size": st["font_pt"],
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": st["mirror_ticks"],
            "ytick.right": st["mirror_ticks"],
            "axes.linewidth": 0.8,
            "axes.grid": False,
        }
    )
    fig, ax = plt.subplots(figsize=st["size_in"], dpi=st["dpi"])
    x_log = meta["x_scale"] == "log10"
    if x_log:
        ax.set_xscale("log")
        xl = _log_limits(float(x.min()), float(x.max()))
    else:
        xl = _limits(float(x.min()), float(x.max()), True)
    yl = _limits(float(y.min()), float(y.max()), True)
    yl = (yl[0], yl[1] + (_nice_step(yl[1] - yl[0]) if st["legend"] else 0.0))
    markevery = max(1, len(x) // 12) if len(x) > 20 else 1
    ax.plot(
        x,
        y,
        color=st["color"],
        lw=st["lw"],
        marker=st["marker"] or ("o" if len(x) < 20 else None),
        markersize=4,
        markerfacecolor="white",
        markevery=markevery,
        label=meta.get("legend") or meta["slug"].split("-")[-1],
    )
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_xlabel(meta["x_label"])
    ax.set_ylabel(meta["y_label"])
    if st["legend"]:
        ax.legend(loc="upper left" if meta.get("peak_right") else "upper right", frameon=False)
    if st["panel_label"]:
        ax.text(0.03, 0.93, "(a)", transform=ax.transAxes)
    fig.tight_layout()
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=st["dpi"])
    plt.close(fig)
    image = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    if st["jpeg_q"]:
        jbuf = io.BytesIO()
        image.save(jbuf, format="JPEG", quality=st["jpeg_q"])
        image = Image.open(io.BytesIO(jbuf.getvalue())).convert("RGB")
    frame = {
        "plot_w": float(bbox.width),
        "plot_box_px": [
            float(bbox.x0),
            float(image.height - bbox.y1),
            float(bbox.x1),
            float(image.height - bbox.y0),
        ],
        "x_range": [float(xl[0]), float(xl[1])],
        "y_range": [float(yl[0]), float(yl[1])],
        "style": st,
        "png_size": [image.width, image.height],
    }
    return image, frame


def main() -> None:
    sources = json.loads((HERE / "sources" / "sources.json").read_text(encoding="utf-8"))
    slugs = sorted(sources, key=lambda s: hashlib.sha256(s.encode()).hexdigest())
    split = {slug: ("dev" if i < N_DEV else "held-out") for i, slug in enumerate(slugs)}
    (HERE / "figures").mkdir(exist_ok=True)
    (HERE / "gt").mkdir(exist_ok=True)
    figures = []
    for slug in sorted(sources):
        meta = dict(sources[slug])
        data = np.loadtxt(HERE / "sources" / f"{slug}.csv", delimiter=",", skiprows=1)
        x, y = data[:, 0], data[:, 1]
        meta["peak_right"] = bool(np.argmax(y) > 0.6 * len(y))
        image, frame = render(slug, x, y, meta)
        image.save(HERE / "figures" / f"{slug}.png")
        entry = {
            "slug": slug,
            "split": split[slug],
            "title": meta["title"],
            "source_url": meta["source_url"],
            "license": meta["license"],
            "source_file": meta["source_file"],
            "figure_id": meta["source_file"],
            "kind": meta["kind"],
            "x_label": meta["x_label"],
            "y_label": meta["y_label"],
            "x_scale": meta["x_scale"],
            "y_scale": meta["y_scale"],
            "notes": meta["notes"],
            "n_raw": meta["n_raw"],
            "n_points": int(len(x)),
            **frame,
        }
        figures.append(entry)
        gt = {
            **entry,
            "series": {"curve": [[float(a), float(b)] for a, b in zip(x, y, strict=False)]},
        }
        (HERE / "gt" / f"{slug}.json").write_text(json.dumps(gt, indent=1), encoding="utf-8")
    manifest = {
        "dataset": "domain-single-curve-v1",
        "split_rule": "sort slugs by sha256(slug) hex; first 8 dev, rest held-out",
        "truth": "points copied from the cited open dataset (x strictly increasing; arc-length subset of <=300 raw rows); the figure is re-plotted from exactly these points",
        "n_figures": len(figures),
        "n_dev": sum(1 for f in figures if f["split"] == "dev"),
        "n_held_out": sum(1 for f in figures if f["split"] == "held-out"),
        "figures": figures,
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("n_figures", "n_dev", "n_held_out")}))


if __name__ == "__main__":
    main()
