"""Render one sample and record pixel-accurate ground truth from ``transData``."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from PIL import Image

from benchmarks.generator.degrade import apply_points, degrade
from benchmarks.generator.shapes import (
    LINE_SHAPES,
    bar_heights,
    displacement_scatter,
    generic_noisy,
)
from benchmarks.generator.spec import SampleSpec

FONT_FILES = {
    "DejaVu Sans": Path(__file__).resolve().parents[1] / "fonts" / "DejaVuSans.ttf",
    "Liberation Serif": Path(__file__).resolve().parents[1]
    / "fonts"
    / "LiberationSerif-Regular.ttf",
}
_FONTS_READY = False


def _ensure_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    for path in FONT_FILES.values():
        if not path.is_file():
            raise FileNotFoundError(path)
        font_manager.fontManager.addfont(str(path))
    _FONTS_READY = True


def _font_family(name: str) -> str:
    _ensure_fonts()
    prop = font_manager.FontProperties(fname=str(FONT_FILES[name]))
    return prop.get_name()


def _hex_rgb(color: str) -> np.ndarray:
    return np.array([int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)], dtype=np.int16)


def _series_xy(spec: SampleSpec, rng: np.random.Generator) -> list[tuple[np.ndarray, np.ndarray]]:
    series: list[tuple[np.ndarray, np.ndarray]] = []
    for _ in range(spec.n_series):
        if spec.shape == "bar_values":
            series.append(bar_heights(spec.n_points, rng))
        elif spec.shape == "displacement_scatter":
            series.append(displacement_scatter(spec.n_points, rng))
        elif spec.shape == "generic_noisy" and spec.chart_type == "scatter":
            x, y = generic_noisy(max(spec.n_points, 40), rng)
            pick = np.linspace(0, len(x) - 1, spec.n_points).astype(int)
            series.append((x[pick], y[pick]))
        else:
            series.append(LINE_SHAPES[spec.shape](spec.n_points, rng))
    return series


def _visible(rgb: np.ndarray, pix: np.ndarray, color: str, radius: int) -> np.ndarray:
    nominal = _hex_rgb(color)
    height, width = rgb.shape[:2]
    flags = np.zeros(len(pix), dtype=bool)
    for idx, (px, py) in enumerate(pix):
        col = int(round(px - 0.5))
        row = int(round(py - 0.5))
        if col < 0 or row < 0 or col >= width or row >= height:
            continue
        r0, r1 = max(0, row - radius), min(height, row + radius + 1)
        c0, c1 = max(0, col - radius), min(width, col + radius + 1)
        patch = rgb[r0:r1, c0:c1].astype(np.int16)
        dist = np.abs(patch - nominal).sum(axis=2)
        flags[idx] = bool(np.any(dist <= 120))
    return flags


def _ranges(xs: np.ndarray, mask: np.ndarray) -> list[list[float]]:
    if xs.size == 0:
        return []
    order = np.argsort(xs)
    xs = xs[order]
    mask = mask[order]
    ranges: list[list[float]] = []
    start: float | None = None
    prev = float(xs[0])
    for x, flag in zip(xs.tolist(), mask.tolist(), strict=True):
        if flag and start is None:
            start = float(x)
        elif not flag and start is not None:
            ranges.append([start, prev])
            start = None
        prev = float(x)
    if start is not None:
        ranges.append([start, float(xs[-1])])
    return [[lo, hi] for lo, hi in ranges if hi > lo]


def _save_png(path: Path, rgb: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(path, format="PNG", compress_level=3)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_sample(spec: SampleSpec, out_dir: Path | None = None) -> dict[str, object]:
    """Render ``spec``. When ``out_dir`` is set, write ``img.png``, ``clean.png``, ``gt.json``, ``spec.json``."""

    _ensure_fonts()
    # The spec seed already consumed its own stream inside make_spec. Rebuild the
    # series from a stream keyed only by spec_seed so a reloaded spec matches.
    series_rng = np.random.Generator(np.random.PCG64(spec.spec_seed ^ 0xA5A5A5A5))
    curves = _series_xy(spec, series_rng)
    family = _font_family(spec.font)
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": spec.font_size,
            "axes.linewidth": 1.0,
            "axes.unicode_minus": False,
            "axes.axisbelow": True,
        }
    )
    fig = plt.figure(figsize=(spec.fig_w, spec.fig_h), dpi=spec.dpi)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.18, right=0.96, bottom=0.16, top=0.90)
    if spec.legend == "outside":
        fig.subplots_adjust(right=0.76)

    artists: list[object] = []
    if spec.chart_type == "bar":
        group = 0.8
        width = group / spec.n_series
        for idx, (_x, heights) in enumerate(curves):
            offset = (idx - (spec.n_series - 1) / 2.0) * width
            positions = np.arange(len(heights), dtype=np.float64) + offset
            rects = ax.bar(
                positions,
                heights,
                width=width * 0.9,
                color=spec.colors[idx],
                label=f"S{idx}",
                zorder=3,
                linewidth=0.0,
            )
            artists.append(rects)
        ax.set_xlim(-0.6, len(curves[0][1]) - 0.4)
        ax.set_ylim(0.0, max(float(np.max(h)) for _x, h in curves) * 1.12)
    elif spec.chart_type == "scatter":
        for idx, (x, y) in enumerate(curves):
            ax.scatter(
                x,
                y,
                s=(spec.marker_size**2),
                c=spec.colors[idx],
                marker=spec.marker or "o",
                label=f"S{idx}",
                zorder=3,
                linewidths=0.6,
            )
        ax.margins(0.08)
    else:
        for idx, (x, y) in enumerate(curves):
            ax.plot(
                x,
                y,
                color=spec.colors[idx],
                lw=spec.linewidth,
                marker=spec.marker,
                markersize=spec.marker_size if spec.marker else 0.0,
                label=f"S{idx}",
                zorder=3,
            )
        ax.margins(x=0.02, y=0.08)
    ax.set_xlabel(spec.x_label)
    ax.set_ylabel(spec.y_label)
    if spec.title:
        ax.set_title(spec.title)
    if spec.grid == "major":
        ax.grid(True, which="major", color="#B0B0B0", alpha=0.75, linewidth=0.6, zorder=0)
    elif spec.grid == "major+minor":
        ax.minorticks_on()
        ax.grid(True, which="major", color="#B0B0B0", alpha=0.75, linewidth=0.6, zorder=0)
        ax.grid(True, which="minor", color="#D0D0D0", alpha=0.55, linewidth=0.4, zorder=0)
    if spec.legend == "inside":
        ax.legend(loc=spec.legend_loc, framealpha=1.0, edgecolor="#555555", fancybox=False)
    elif spec.legend == "outside":
        ax.legend(
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            framealpha=1.0,
            edgecolor="#555555",
            fancybox=False,
        )

    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    clean = np.ascontiguousarray(rgba[:, :, :3])
    height, width = clean.shape[:2]
    bb = ax.get_window_extent()
    bbox = [
        int(round(bb.x0)),
        int(round(height - bb.y1)),
        int(round(bb.x1)),
        int(round(height - bb.y0)),
    ]
    xlim = tuple(float(v) for v in ax.get_xlim())
    ylim = tuple(float(v) for v in ax.get_ylim())

    def image_xy(data_x: float, data_y: float) -> tuple[float, float]:
        px, py = ax.transData.transform((data_x, data_y))
        return float(px), float(height - py)

    def axis_ticks(name: str) -> list[dict[str, float]]:
        if name == "x":
            values = [
                float(v) for v in ax.get_xticks() if xlim[0] - 1e-8 <= float(v) <= xlim[1] + 1e-8
            ]
            if len(values) < 2:
                values = [xlim[0], xlim[1]]
            ticks = []
            for value in values:
                px, py = image_xy(value, ylim[0])
                ticks.append({"px": px, "py": py, "value": value})
            return ticks
        values = [float(v) for v in ax.get_yticks() if ylim[0] - 1e-8 <= float(v) <= ylim[1] + 1e-8]
        if len(values) < 2:
            values = [ylim[0], ylim[1]]
        ticks = []
        for value in values:
            px, py = image_xy(xlim[0], value)
            ticks.append({"px": px, "py": py, "value": value})
        return ticks

    gt_series: list[dict[str, object]] = []
    line_width_px = spec.linewidth * spec.dpi / 72.0
    radius = max(2, int(round(line_width_px)))
    for idx, (x, y) in enumerate(curves):
        color = spec.colors[idx]
        record: dict[str, object] = {
            "series_id": f"s{idx}",
            "kind": "bar"
            if spec.chart_type == "bar"
            else ("scatter" if spec.chart_type == "scatter" else "line"),
            "color": color,
            "x": [float(v) for v in x],
            "y": [float(v) for v in y],
        }
        if spec.chart_type == "bar":
            group = 0.8
            width_bar = group / spec.n_series
            offset = (idx - (spec.n_series - 1) / 2.0) * width_bar
            bars = []
            for cat, height_v in enumerate(y):
                center = float(cat) + offset
                top = float(height_v)
                px, py = image_xy(center, top)
                bars.append({"x": center, "y": top, "px": px, "py": py})
            record["bars"] = bars
            record["polyline_clean"] = [[item["px"], item["py"]] for item in bars]
        elif spec.chart_type == "scatter":
            markers = []
            for xv, yv in zip(x.tolist(), y.tolist(), strict=True):
                px, py = image_xy(float(xv), float(yv))
                markers.append({"x": float(xv), "y": float(yv), "px": px, "py": py})
            record["markers"] = markers
            record["polyline_clean"] = [[item["px"], item["py"]] for item in markers]
        else:
            pix = np.array([image_xy(float(xv), float(yv)) for xv, yv in zip(x, y, strict=True)])
            vis = _visible(clean, pix, color, radius)
            record["polyline_clean"] = pix.tolist()
            record["visible"] = vis.astype(int).tolist()
            record["visible_ranges"] = _ranges(x, vis)
            record["invisible_ranges"] = _ranges(x, ~vis)
        gt_series.append(record)

    # Scatter overlap in the clean image, using marker diameter.
    overlap = False
    if spec.chart_type == "scatter":
        diameter = spec.marker_size * spec.dpi / 72.0
        for record in gt_series:
            markers = record.get("markers")
            if not isinstance(markers, list) or len(markers) < 2:
                continue
            coords = np.array([[float(m["px"]), float(m["py"])] for m in markers], dtype=np.float64)
            for i in range(len(coords)):
                delta = coords[i + 1 :] - coords[i]
                if delta.size and float(np.min(np.hypot(delta[:, 0], delta[:, 1]))) < diameter:
                    overlap = True
                    break

    occluded = False
    for record in gt_series:
        visible = record.get("visible")
        if isinstance(visible, list) and visible:
            if 1.0 - (sum(visible) / len(visible)) > 0.05:
                occluded = True

    probes = []
    for xv in np.linspace(xlim[0], xlim[1], 3):
        for yv in np.linspace(ylim[0], ylim[1], 3):
            px, py = image_xy(float(xv), float(yv))
            probes.append({"px": px, "py": py, "x": float(xv), "y": float(yv)})
    x_ticks = axis_ticks("x")
    y_ticks = axis_ticks("y")

    plt.close(fig)

    degrade_rng = np.random.Generator(np.random.PCG64(spec.spec_seed ^ 0x123456789))
    degraded, matrix = degrade(clean, spec, degrade_rng)

    def _transform_pairs(pairs: list[list[float]]) -> list[list[float]]:
        if not pairs:
            return []
        arr = apply_points(np.asarray(pairs, dtype=np.float64), matrix)
        return arr.tolist()

    for record in gt_series:
        clean_poly = record.get("polyline_clean", [])
        if isinstance(clean_poly, list):
            record["polyline"] = _transform_pairs(clean_poly)  # type: ignore[arg-type]
        for key in ("markers", "bars"):
            items = record.get(key)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        mapped = apply_points(
                            np.array([[item["px"], item["py"]]], dtype=np.float64), matrix
                        )[0]
                        item["px"] = float(mapped[0])
                        item["py"] = float(mapped[1])
    mapped_probes = []
    for probe in probes:
        mapped = apply_points(np.array([[probe["px"], probe["py"]]], dtype=np.float64), matrix)[0]
        mapped_probes.append(
            {"px": float(mapped[0]), "py": float(mapped[1]), "x": probe["x"], "y": probe["y"]}
        )
    corners = np.array(
        [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
        ],
        dtype=np.float64,
    )
    mapped_corners = apply_points(corners, matrix)
    deg_bbox = [
        int(round(float(mapped_corners[:, 0].min()))),
        int(round(float(mapped_corners[:, 1].min()))),
        int(round(float(mapped_corners[:, 0].max()))),
        int(round(float(mapped_corners[:, 1].max()))),
    ]

    def _map_ticks(ticks: list[dict[str, float]]) -> list[dict[str, float]]:
        if not ticks:
            return []
        arr = apply_points(np.array([[t["px"], t["py"]] for t in ticks], dtype=np.float64), matrix)
        return [
            {"px": float(arr[i, 0]), "py": float(arr[i, 1]), "value": ticks[i]["value"]}
            for i in range(len(ticks))
        ]

    document: dict[str, object] = {
        "id": f"{spec.split}_{spec.index:05d}",
        "dataset_version": "synth-v0.1",
        "spec_seed": spec.spec_seed,
        "chart_type": spec.chart_type,
        "degradation": spec.degradation,
        "color_mode": spec.color_mode,
        "n_series": spec.n_series,
        "series_bucket": spec.series_bucket,
        "domain_shape": spec.shape,
        "occluded": occluded,
        "markers_overlap": overlap,
        "width": int(degraded.shape[1]),
        "height": int(degraded.shape[0]),
        "plot_area": {"bbox": deg_bbox, "bbox_clean": bbox},
        "transform": matrix.tolist(),
        "axes": {
            "x": {"scale": "linear", "lim": list(xlim), "ticks": _map_ticks(x_ticks)},
            "y": {"scale": "linear", "lim": list(ylim), "ticks": _map_ticks(y_ticks)},
        },
        "R_x": float(xlim[1] - xlim[0]),
        "R_y": float(ylim[1] - ylim[0]),
        "series": gt_series,
        "probes": mapped_probes,
        "image": "img.png",
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        sha = _save_png(out_dir / "img.png", degraded)
        _save_png(out_dir / "clean.png", clean)
        (out_dir / "gt.json").write_text(json.dumps(document), encoding="utf-8")
        (out_dir / "spec.json").write_text(json.dumps(spec.to_dict()), encoding="utf-8")
        document["sha256"] = sha
    return document
