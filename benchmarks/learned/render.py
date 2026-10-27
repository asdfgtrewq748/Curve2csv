"""Draw labeled charts. Labels are visible series ink, not legends or gridlines."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Rectangle
from numpy.typing import NDArray

from benchmarks.generator.render import FONT_FILES

CANVAS = (850, 600)
MAX_SERIES = 6

_PALETTES: dict[str, list[str]] = {
    "matplotlib": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
    "excel": ["#4472C4", "#ED7D31", "#A9D08E", "#FFC000", "#5B9BD5", "#70AD47"],
    "ggplot": ["#F8766D", "#7CAE00", "#00BFC4", "#C77CFF", "#00BA38", "#619CFF"],
    "owid_like": ["#C15065", "#4C6A9C", "#2A9D8F", "#E9C46A", "#6D597A", "#B5838D"],
    "muted": ["#6B7C85", "#A67C52", "#5E8C6A", "#8C6B7A", "#7A8456", "#5C6E91"],
}
_FONTS_READY = False
_FIG: plt.Figure | None = None
_AX: plt.Axes | None = None


@dataclass(frozen=True)
class RenderedChart:
    rgb: NDArray[np.uint8]
    label: NDArray[np.uint8]
    style: str
    n_series: int
    colors: tuple[tuple[int, int, int], ...]


def _ensure_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    for path in FONT_FILES.values():
        if path.is_file():
            font_manager.fontManager.addfont(str(path))
    _FONTS_READY = True


def _hex_rgb(color: str) -> NDArray[np.int16]:
    return np.array([int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)], dtype=np.int16)


def _curve(rng: np.random.Generator, kind: str, n: int) -> NDArray[np.float64]:
    x = np.linspace(0.0, 1.0, n)
    if kind == "sine":
        y = np.sin(2.0 * np.pi * float(rng.uniform(0.5, 2.2)) * x + float(rng.uniform(0.0, 6.0)))
    elif kind == "linear":
        y = float(rng.uniform(-0.4, 0.4)) + float(rng.uniform(-1.6, 1.6)) * x
    elif kind == "random-walk":
        y = np.cumsum(rng.normal(0.0, 0.12, n))
    elif kind == "exp":
        y = np.exp(float(rng.uniform(0.4, 1.4)) * x)
    else:
        knee = float(rng.uniform(0.3, 0.7))
        y = np.where(x < knee, 0.2 * x, 0.2 * knee + float(rng.uniform(1.5, 3.0)) * (x - knee))
    y = np.asarray(y, dtype=np.float64)
    span = float(np.ptp(y))
    if span < 1e-6:
        y = x.copy()
        span = 1.0
    y = (y - float(y.min())) / span
    offset = float(rng.uniform(0.0, 0.35))
    scale = float(rng.uniform(0.45, 0.95))
    return offset + scale * y


def _colors(rng: np.random.Generator, palette: list[str], n: int) -> list[NDArray[np.int16]]:
    chosen = [_hex_rgb(palette[i % len(palette)]).copy() for i in range(n)]
    if n >= 2 and float(rng.random()) < 0.22:
        partner = int(rng.integers(1, n))
        delta = float(rng.integers(14, 37))
        direction = rng.normal(0.0, 1.0, 3)
        direction = direction / (float(np.linalg.norm(direction)) + 1e-6)
        nudged = chosen[0].astype(np.float64) + direction * delta
        chosen[partner] = np.clip(np.rint(nudged), 0, 255).astype(np.int16)
    if float(rng.random()) < 0.12:
        chosen[int(rng.integers(0, n))] = np.array([34, 34, 34], dtype=np.int16)
    return chosen


def _axes() -> tuple[plt.Figure, plt.Axes]:
    global _FIG, _AX
    if _FIG is None or _AX is None:
        _ensure_fonts()
        _FIG, _AX = plt.subplots(figsize=(8.5, 6.0), dpi=100)
    _AX.clear()
    return _FIG, _AX


def _pixels(
    ax: plt.Axes, x: NDArray[np.float64], y: NDArray[np.float64], height: int, width: int
) -> NDArray[np.int32]:
    disp = ax.transData.transform(np.column_stack([x, y]))
    cols = np.rint(disp[:, 0] - 0.5).astype(np.int32)
    rows = np.rint(height - disp[:, 1] - 0.5).astype(np.int32)
    return np.stack(
        [np.clip(cols, 0, width - 1), np.clip(rows, 0, height - 1)],
        axis=1,
    )


def _degrade(rgb: NDArray[np.uint8], rng: np.random.Generator) -> NDArray[np.uint8]:
    image = rgb
    if float(rng.random()) < 0.55:
        quality = int(rng.integers(55, 91))
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        ok, encoded = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if ok:
            decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            if decoded is not None:
                image = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    if float(rng.random()) < 0.25:
        image = cv2.GaussianBlur(image, (3, 3), 0)
    if float(rng.random()) < 0.40:
        sigma = float(rng.uniform(2.0, 6.0))
        noise = rng.normal(0.0, sigma, image.shape)
        image = np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return image


def render_chart(rng: np.random.Generator) -> RenderedChart:
    """One chart. ``label`` is 0 on background and 1..n on visible series ink."""

    style = str(
        rng.choice(
            ["owid_like", "matplotlib", "excel", "ggplot", "muted"],
            p=[0.35, 0.20, 0.15, 0.15, 0.15],
        )
    )
    chart = str(
        rng.choice(["line", "line+marker", "scatter", "dashed"], p=[0.45, 0.25, 0.15, 0.15])
    )
    grid = str(rng.choice(["none", "h", "both"], p=[0.30, 0.40, 0.30]))
    n_series = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.15, 0.30, 0.28, 0.15, 0.07, 0.05]))
    colors = _colors(rng, _PALETTES[style], n_series)
    kinds = ["sine", "linear", "random-walk", "exp", "knee"]
    fig, ax = _axes()
    if style == "ggplot":
        fig.patch.set_facecolor("#EBEBEB")
        ax.set_facecolor("#EBEBEB")
    else:
        fig.patch.set_facecolor("#FFFFFF")
        ax.set_facecolor("#FAFAFA" if style == "owid_like" else "#FFFFFF")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.35)
    series_xy: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []
    for index, color in enumerate(colors):
        n_pts = 48 if chart == "scatter" else 180
        x = np.linspace(0.0, 1.0, n_pts)
        y = np.clip(_curve(rng, str(rng.choice(kinds)), n_pts), 0.02, 1.28)
        if chart == "scatter":
            y = np.clip(y + rng.normal(0.0, 0.03, n_pts), 0.02, 1.28)
        series_xy.append((x, y))
        hex_color = f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
        width = float(rng.uniform(1.4, 2.3))
        if chart == "scatter":
            ax.plot(
                x,
                y,
                linestyle="none",
                marker="o",
                markersize=4.5,
                color=hex_color,
                label=f"s{index}",
            )
        elif chart == "dashed":
            ax.plot(
                x, y, linestyle=(0, (5, 3)), linewidth=width, color=hex_color, label=f"s{index}"
            )
        elif chart == "line+marker":
            ax.plot(
                x,
                y,
                linestyle="-",
                linewidth=width,
                marker="o",
                markevery=12,
                markersize=4.5,
                color=hex_color,
                label=f"s{index}",
            )
        else:
            ax.plot(x, y, linestyle="-", linewidth=width, color=hex_color, label=f"s{index}")
    if grid == "h":
        ax.grid(True, axis="y", color="#D5D5D5", linewidth=0.6, zorder=0)
    elif grid == "both":
        ax.grid(True, color="#D0D0D0", linewidth=0.6, zorder=0)
    if style == "ggplot":
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    if float(rng.random()) < 0.55:
        ax.legend(loc="upper left", framealpha=1.0, edgecolor="#BBBBBB", fontsize=8)
    if float(rng.random()) < 0.7:
        ax.set_title("series", fontsize=11)
    ax.tick_params(labelsize=8)
    if float(rng.random()) < 0.30:
        x0 = float(rng.uniform(0.15, 0.55))
        y0 = float(rng.uniform(0.2, 0.7))
        ax.add_patch(Rectangle((x0, y0), 0.18, 0.22, facecolor="white", edgecolor="none", zorder=5))
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.10, top=0.90)
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    rgb = np.ascontiguousarray(rgba[:, :, :3])
    height, width = rgb.shape[:2]
    label = np.zeros((height, width), dtype=np.uint8)
    nominal = np.stack(colors, axis=0)
    for index, (x, y) in enumerate(series_xy):
        pts = _pixels(ax, x, y, height, width)
        layer = np.zeros((height, width), dtype=np.uint8)
        if chart == "scatter":
            for col, row in pts:
                cv2.circle(layer, (int(col), int(row)), 5, 1, thickness=-1, lineType=cv2.LINE_8)
        else:
            cv2.polylines(
                layer, [pts.reshape(-1, 1, 2)], False, 1, thickness=3, lineType=cv2.LINE_8
            )
            if chart == "line+marker":
                for col, row in pts[::12]:
                    cv2.circle(layer, (int(col), int(row)), 5, 1, thickness=-1, lineType=cv2.LINE_8)
        diff = np.abs(rgb.astype(np.int16) - nominal[index].reshape(1, 1, 3)).sum(axis=2)
        visible = (layer > 0) & (diff <= 150) & (label == 0)
        label[visible] = np.uint8(index + 1)
    rgb = _degrade(rgb, rng)
    if rgb.shape[1] != CANVAS[0] or rgb.shape[0] != CANVAS[1]:
        rgb = cv2.resize(rgb, CANVAS, interpolation=cv2.INTER_AREA)
        label = cv2.resize(label, CANVAS, interpolation=cv2.INTER_NEAREST)
    stored = tuple((int(color[0]), int(color[1]), int(color[2])) for color in colors)
    return RenderedChart(rgb=rgb, label=label, style=style, n_series=n_series, colors=stored)
