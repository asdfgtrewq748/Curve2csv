"""Separate data series by clustering chromatic pixels in CIELAB."""

from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from curve2csv.color_math import deltaE_ciede2000, lab2rgb, rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.types import Masks, SeriesMask


def _kmeans(
    data: NDArray[np.float64],
    k: int,
    rng: np.random.Generator,
    iterations: int = 20,
) -> tuple[NDArray[np.float64], NDArray[np.int32]]:
    n_samples = data.shape[0]
    centers = np.empty((k, data.shape[1]), dtype=np.float64)
    centers[0] = data[int(rng.integers(0, n_samples))]
    closest = np.full(n_samples, np.inf)
    for j in range(1, k):
        dist = ((data - centers[j - 1]) ** 2).sum(axis=1)
        closest = np.minimum(closest, dist)
        total = float(closest.sum())
        if total <= 0.0:
            centers[j] = data[int(rng.integers(0, n_samples))]
            continue
        probs = closest / total
        centers[j] = data[int(rng.choice(n_samples, p=probs))]
    labels = np.zeros(n_samples, dtype=np.int32)
    for _ in range(iterations):
        distances = ((data[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = np.argmin(distances, axis=1).astype(np.int32)
        for j in range(k):
            selected = data[labels == j]
            if selected.size == 0:
                centers[j] = data[int(rng.integers(0, n_samples))]
            else:
                centers[j] = selected.mean(axis=0)
    return centers, labels


def _min_de00(centers: NDArray[np.float64]) -> float:
    if len(centers) < 2:
        return 1e9
    best = 1e9
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            de = float(deltaE_ciede2000(centers[i][None, None, :], centers[j][None, None, :])[0, 0])
            best = min(best, de)
    return best


def _centroids_apart(
    labels: NDArray[np.int32],
    positions: NDArray[np.float64] | None,
    minimum: float = 8.0,
) -> bool:
    """True when two color clusters sit on different parts of the figure.

    Shades of one stroke have almost the same centroid. Two lines do not.
    """

    if positions is None or len(positions) != len(labels):
        return True
    centroids: list[NDArray[np.float64]] = []
    for label in np.unique(labels):
        selected = positions[labels == label]
        if selected.size == 0:
            continue
        centroids.append(selected.mean(axis=0))
    if len(centroids) < 2:
        return False
    nearest = 1e9
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            delta = centroids[i] - centroids[j]
            nearest = min(nearest, float(np.hypot(delta[0], delta[1])))
    return nearest >= minimum


def _choose_centers(
    samples: NDArray[np.float64],
    cfg: PipelineConfig,
    positions: NDArray[np.float64] | None = None,
) -> tuple[NDArray[np.float64], bool]:
    rng = np.random.Generator(np.random.PCG64(cfg.kmeans_seed))
    best_centers = samples.mean(axis=0, keepdims=True)
    ambiguous = False
    max_k = int(min(cfg.max_series, max(1, samples.shape[0] // max(cfg.min_cluster_pixels, 1))))
    max_k = max(1, min(max_k, 6))
    for k in range(1, max_k + 1):
        centers, labels = _kmeans(samples, k, rng)
        if k > 1 and _min_de00(centers) < cfg.min_series_delta_e:
            # Keep the coarser clustering. A rejected extra split marks the
            # series ambiguous only when those inks are also far apart in the
            # image (two strokes). Anti-aliased shades of one stroke are not.
            if (
                len(best_centers) < 2
                and _min_de00(centers) < cfg.ambiguous_delta_e
                and _centroids_apart(labels, positions)
            ):
                ambiguous = True
            break
        counts = np.bincount(labels, minlength=k)
        if counts.min() < cfg.min_cluster_pixels:
            break
        best_centers = centers
    if len(best_centers) >= 2 and _min_de00(best_centers) < cfg.ambiguous_delta_e:
        # Merge inseparable colors into one series and say so.
        best_centers = best_centers.mean(axis=0, keepdims=True)
        ambiguous = True
    return best_centers, ambiguous


def lab_to_hex(lab: tuple[float, float, float]) -> str:
    rgb = lab2rgb(np.asarray(lab, dtype=np.float64).reshape(1, 1, 3))[0, 0]
    channels = np.clip(np.round(rgb * 255.0), 0, 255).astype(int)
    return f"#{channels[0]:02x}{channels[1]:02x}{channels[2]:02x}"


def _core_pixels(
    lab: NDArray[np.float64], foreground: NDArray[np.bool_], chroma_min: float
) -> NDArray[np.bool_]:
    """Ridge pixels: local chroma maxima. Anti-aliased fringes are not maxima."""

    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    dilated = cv2.dilate(chroma.astype(np.float32), np.ones((3, 3), np.float32))
    core = foreground & (chroma + 1e-3 >= dilated) & (chroma >= max(chroma_min, 14.0))
    if int(core.sum()) < 30:
        core = foreground & (chroma >= max(chroma_min, 14.0))
    return np.asarray(core, dtype=bool)


def _column_centers(mask: NDArray[np.bool_]) -> tuple[NDArray[np.int32], NDArray[np.float64]]:
    ys, xs = np.nonzero(mask)
    if xs.size == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float64)
    order = np.argsort(xs, kind="mergesort")
    xs = xs[order]
    ys = ys[order]
    breaks = np.flatnonzero(np.diff(xs)) + 1
    groups = np.split(ys, breaks)
    cols = xs[np.r_[0, breaks]]
    centers = np.array([float(np.median(group)) for group in groups], dtype=np.float64)
    return cols.astype(np.int32), centers


def _same_stroke(left: SeriesMask, right: SeriesMask) -> bool:
    """True when two masks are the core and the fringe of one stroke.

    Distinct lines sit many pixels apart. Anti-aliased shades of one stroke
    share columns and stay within a couple of pixels.
    """

    de = float(
        deltaE_ciede2000(
            np.asarray(left.color_lab, dtype=np.float64)[None, None, :],
            np.asarray(right.color_lab, dtype=np.float64)[None, None, :],
        )[0, 0]
    )
    if de > 17.0:
        return False
    cols_a, cen_a = _column_centers(left.mask)
    cols_b, cen_b = _column_centers(right.mask)
    if cols_a.size == 0 or cols_b.size == 0:
        return False
    shared_a = np.isin(cols_a, cols_b)
    if int(shared_a.sum()) < 40:
        return False
    lookup = {int(col): float(center) for col, center in zip(cols_b, cen_b, strict=True)}
    delta = np.array(
        [
            abs(float(center) - lookup[int(col)])
            for col, center in zip(cols_a[shared_a], cen_a[shared_a], strict=True)
        ],
        dtype=np.float64,
    )
    shorter = min(int(cols_a.size), int(cols_b.size))
    if delta.size < 0.4 * shorter:
        return False
    return float(np.median(delta)) <= 2.5 and float(np.percentile(delta, 90)) <= 7.0


def _merge_stroke_shades(series: list[SeriesMask]) -> list[SeriesMask]:
    if len(series) < 2:
        return series
    parent = list(range(len(series)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i in range(len(series)):
        for j in range(i + 1, len(series)):
            if _same_stroke(series[i], series[j]):
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for index in range(len(series)):
        groups.setdefault(find(index), []).append(index)
    merged: list[SeriesMask] = []
    for indexes in groups.values():
        if len(indexes) == 1:
            merged.append(series[indexes[0]])
            continue
        primary = max(indexes, key=lambda item: int(series[item].mask.sum()))
        mask = np.zeros_like(series[primary].mask)
        for item in indexes:
            mask |= series[item].mask
        base = series[primary]
        merged.append(
            SeriesMask(
                series_id=base.series_id,
                color_lab=base.color_lab,
                style=base.style,
                mask=mask,
                separation_score=base.separation_score,
                ambiguous=base.ambiguous,
            )
        )
    return _strip_ridge_halos(merged)


def _strip_ridge_halos(series: list[SeriesMask]) -> list[SeriesMask]:
    """Drop pixels that sit on another stroke's ridge and far from their own.

    Anti-aliased bleed and a crossing halo make ``other_dist`` flag the parent
    centerline for the rest of the column. A real crossing stays: those pixels
    are near both centerlines. A parallel stroke stays: its pixels are near its
    own centerline. Empty masks are removed. Nothing is filled in.
    """

    if len(series) < 2:
        return series
    width = int(series[0].mask.shape[1])
    center_rows: list[NDArray[np.float64]] = []
    for item in series:
        cols, centers = _column_centers(item.mask)
        row = np.full(width, np.nan, dtype=np.float64)
        if cols.size:
            row[cols] = centers
        center_rows.append(row)
    stripped: list[SeriesMask] = []
    for index, guest in enumerate(series):
        mask = np.array(guest.mask, copy=True)
        ys, xs = np.nonzero(mask)
        if ys.size == 0:
            continue
        guest_y = center_rows[index][xs]
        rows = ys.astype(np.float64)
        drop = np.zeros(ys.shape[0], dtype=bool)
        for host_index, host_row in enumerate(center_rows):
            if host_index == index:
                continue
            host_y = host_row[xs]
            on_host = np.isfinite(host_y) & (np.abs(rows - host_y) <= 2.5)
            on_guest = np.isfinite(guest_y) & (np.abs(rows - guest_y) <= 6.0)
            drop |= on_host & ~on_guest
        if np.any(drop):
            mask[ys[drop], xs[drop]] = False
        if int(mask.sum()) < 10:
            continue
        stripped.append(
            SeriesMask(
                series_id=guest.series_id,
                color_lab=guest.color_lab,
                style=guest.style,
                mask=mask,
                separation_score=guest.separation_score,
                ambiguous=guest.ambiguous,
            )
        )
    return stripped


def separate_series(
    rgb: np.ndarray,
    masks: Masks,
    config: PipelineConfig | None = None,
) -> list[SeriesMask]:
    cfg = config or PipelineConfig()
    if not np.any(masks.foreground):
        return []
    lab = rgb2lab(rgb).astype(np.float64)
    core = _core_pixels(lab, masks.foreground, cfg.chroma_min)
    ys_c, xs_c = np.nonzero(core)
    if ys_c.size < 10:
        return []
    samples = lab[ys_c, xs_c]
    positions = np.stack([xs_c, ys_c], axis=1).astype(np.float64)
    if samples.shape[0] > 8000:
        rng = np.random.Generator(np.random.PCG64(cfg.kmeans_seed))
        pick = rng.choice(samples.shape[0], size=8000, replace=False)
        samples = samples[pick]
        positions = positions[pick]
    centers, ambiguous = _choose_centers(samples, cfg, positions)
    # Assign the full foreground, not only the ridge, so markers and bar fills survive.
    ys, xs = np.nonzero(masks.foreground)
    pixels = lab[ys, xs]
    # Assign every foreground pixel to the nearest center within a Lab radius.
    distances = np.sqrt(((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
    nearest = np.argmin(distances, axis=1)
    nearest_dist = distances[np.arange(pixels.shape[0]), nearest]
    keep = nearest_dist <= cfg.assign_delta_e
    series: list[SeriesMask] = []
    de_margin = _min_de00(centers)
    for idx, center in enumerate(centers):
        selected = keep & (nearest == idx)
        if int(selected.sum()) < max(10, cfg.min_cluster_pixels // 2):
            continue
        mask = np.zeros(masks.foreground.shape, dtype=bool)
        mask[ys[selected], xs[selected]] = True
        lab_t = (float(center[0]), float(center[1]), float(center[2]))
        series.append(
            SeriesMask(
                series_id=f"s{len(series)}",
                color_lab=lab_t,
                style="solid",
                mask=mask,
                separation_score=float(de_margin if len(centers) > 1 else 100.0),
                ambiguous=ambiguous or de_margin < cfg.ambiguous_delta_e,
            )
        )
    return _merge_stroke_shades(series)
