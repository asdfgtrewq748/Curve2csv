"""Sample specifications. All randomness comes from PCG64 seeded per sample."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from skimage.color import deltaE_ciede2000, lab2rgb, rgb2lab

from benchmarks.generator.shapes import LINE_SHAPES

GLOBAL_SEED = 20261025
SPLIT_SEEDS = {"train": 1, "dev": 2, "test": 3, "smoke": 4}
CHART_TYPES = ("line", "line+marker", "scatter", "bar")
DEGRADATIONS = ("clean", "light", "medium")
BUCKETS = ("1", "2-3", "4+")
TAB10 = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#bcbd22",
    "#17becf",
)
MARKERS = ("o", "s", "^", "x")
FONTS = ("DejaVu Sans", "Liberation Serif")
LINE_SHAPE_NAMES = tuple(LINE_SHAPES)


def mix_seed(*parts: int) -> int:
    """Deterministic 64-bit mix. Python's builtin hash is not stable across processes."""

    value = 0
    for part in parts:
        value = (value + (int(part) & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
        value = (value * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 30
        value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 27
        value = (value * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        value ^= value >> 31
    return int(value)


def sample_seed(split: str, index: int, global_seed: int = GLOBAL_SEED) -> int:
    return mix_seed(global_seed, SPLIT_SEEDS[split], index)


def stratum_for(index: int) -> tuple[str, str, str]:
    strata = [
        (chart, deg, bucket) for chart in CHART_TYPES for deg in DEGRADATIONS for bucket in BUCKETS
    ]
    chart, deg, bucket = strata[index % len(strata)]
    return chart, deg, bucket


def _hex_to_lab(color: str) -> np.ndarray:
    rgb = np.array(
        [int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)],
        dtype=np.float64,
    )
    return rgb2lab((rgb / 255.0).reshape(1, 1, 3))[0, 0]


def _lab_to_hex(lab: np.ndarray) -> str:
    rgb = lab2rgb(lab.reshape(1, 1, 3))[0, 0]
    channels = np.clip(np.round(rgb * 255.0), 0, 255).astype(int)
    return f"#{channels[0]:02x}{channels[1]:02x}{channels[2]:02x}"


def _close_pair(rng: np.random.Generator) -> tuple[str, str]:
    for _ in range(400):
        base = np.array(
            [
                float(rng.uniform(28.0, 72.0)),
                float(rng.uniform(-50.0, 50.0)),
                float(rng.uniform(-50.0, 50.0)),
            ]
        )
        other = base + rng.normal(0.0, 7.0, size=3)
        other[0] = float(np.clip(other[0], 20.0, 85.0))
        delta = float(deltaE_ciede2000(base[None, None, :], other[None, None, :])[0, 0])
        if 10.0 <= delta <= 20.0 and float(np.hypot(base[1], base[2])) > 20.0:
            return _lab_to_hex(base), _lab_to_hex(other)
    return TAB10[0], TAB10[1]


def _colors(n_series: int, mode: str, rng: np.random.Generator) -> list[str]:
    if mode == "close_pair" and n_series >= 2:
        first, second = _close_pair(rng)
        rest = [c for c in TAB10 if c not in {first, second}]
        rng.shuffle(rest)  # type: ignore[arg-type]
        return [first, second, *list(rest)[: n_series - 2]]
    picks = list(TAB10)
    rng.shuffle(picks)  # type: ignore[arg-type]
    return picks[:n_series]


def _degradation(level: str, rng: np.random.Generator) -> dict[str, float | int | None]:
    if level == "clean":
        return {"jpeg_quality": None, "noise_sigma": 0.0, "blur_sigma": 0.0, "rotation_deg": 0.0}
    if level == "light":
        return {
            "jpeg_quality": int(rng.choice(np.array([75, 85, 90, 95]))),
            "noise_sigma": float(rng.choice(np.array([0.0, 1.0, 2.0]))),
            "blur_sigma": float(rng.choice(np.array([0.0, 0.3, 0.5]))),
            "rotation_deg": float(rng.choice(np.array([-0.5, -0.25, 0.0, 0.25, 0.5]))),
        }
    return {
        "jpeg_quality": int(rng.choice(np.array([50, 60, 70, 75]))),
        "noise_sigma": float(rng.choice(np.array([0.0, 2.0, 4.0, 5.0]))),
        "blur_sigma": float(rng.choice(np.array([0.0, 0.5, 0.8, 1.0]))),
        "rotation_deg": float(rng.choice(np.array([-1.0, -0.5, 0.0, 0.5, 1.0]))),
    }


@dataclass
class SampleSpec:
    spec_seed: int
    split: str
    index: int
    chart_type: str
    n_series: int
    series_bucket: str
    color_mode: str
    colors: list[str]
    shape: str
    linewidth: float
    marker: str | None
    marker_size: float
    grid: str
    legend: str
    legend_loc: str
    font: str
    font_size: float
    dpi: int
    fig_w: float
    fig_h: float
    degradation: str
    jpeg_quality: int | None
    noise_sigma: float
    blur_sigma: float
    rotation_deg: float
    n_points: int
    x_label: str
    y_label: str
    title: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def make_spec(split: str, index: int, global_seed: int = GLOBAL_SEED) -> SampleSpec:
    seed = sample_seed(split, index, global_seed)
    rng = np.random.Generator(np.random.PCG64(seed))
    chart, degradation, bucket = stratum_for(index)
    if bucket == "1":
        n_series = 1
    elif bucket == "2-3":
        n_series = int(rng.integers(2, 4))
    else:
        n_series = 4
    color_mode = "tab10" if n_series == 1 or float(rng.random()) < 0.75 else "close_pair"
    colors = _colors(n_series, color_mode, rng)
    if chart == "scatter":
        shape = "displacement_scatter" if float(rng.random()) < 0.7 else "generic_noisy"
        marker = str(rng.choice(np.array(MARKERS)))
        n_points = int(rng.integers(14, 36))
        linewidth = 0.0
    elif chart == "bar":
        shape = "bar_values"
        marker = None
        n_points = int(rng.integers(4, 8))
        linewidth = 0.0
    else:
        shape = str(rng.choice(np.array(LINE_SHAPE_NAMES)))
        marker = None if chart == "line" else str(rng.choice(np.array(MARKERS)))
        n_points = int(rng.integers(280, 420))
        linewidth = float(rng.uniform(0.75, 2.5))
    grid = str(rng.choice(np.array(["none", "major", "major+minor"])))
    legend = str(rng.choice(np.array(["none", "inside", "outside"])))
    legend_loc = str(
        rng.choice(np.array(["upper right", "upper left", "lower left", "lower right"]))
    )
    font = str(rng.choice(np.array(FONTS)))
    font_size = float(rng.uniform(7.0, 12.0))
    dpi = int(rng.choice(np.array([72, 100, 150, 200, 300])))
    fig_w = float(rng.uniform(3.5, 7.0))
    fig_h = float(fig_w * float(rng.uniform(0.58, 1.05)))
    # Keep the raster inside the runtime gate's size class. dpi and inches still
    # come from the M1 ranges; only combinations that would exceed 1600x1200 shrink.
    scale = min(1.0, 1580.0 / (fig_w * dpi), 1180.0 / (fig_h * dpi))
    fig_w *= scale
    fig_h *= scale
    deg = _degradation(degradation, rng)
    from benchmarks.generator.shapes import LABELS

    x_label, y_label = LABELS[shape]
    title = "" if float(rng.random()) < 0.35 else shape.replace("_", " ")
    marker_size = float(rng.uniform(4.0, 8.0))
    return SampleSpec(
        spec_seed=seed,
        split=split,
        index=index,
        chart_type=chart,
        n_series=n_series,
        series_bucket=bucket,
        color_mode=color_mode,
        colors=colors,
        shape=shape,
        linewidth=linewidth,
        marker=marker,
        marker_size=marker_size,
        grid=grid,
        legend=legend,
        legend_loc=legend_loc,
        font=font,
        font_size=font_size,
        dpi=dpi,
        fig_w=fig_w,
        fig_h=fig_h,
        degradation=degradation,
        jpeg_quality=None if deg["jpeg_quality"] is None else int(deg["jpeg_quality"]),
        noise_sigma=float(deg["noise_sigma"] or 0.0),
        blur_sigma=float(deg["blur_sigma"] or 0.0),
        rotation_deg=float(deg["rotation_deg"] or 0.0),
        n_points=n_points,
        x_label=x_label,
        y_label=y_label,
        title=title,
    )
