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


def _choose_centers(
    samples: NDArray[np.float64],
    cfg: PipelineConfig,
) -> tuple[NDArray[np.float64], bool]:
    rng = np.random.Generator(np.random.PCG64(cfg.kmeans_seed))
    best_centers = samples.mean(axis=0, keepdims=True)
    ambiguous = False
    max_k = int(min(cfg.max_series, max(1, samples.shape[0] // max(cfg.min_cluster_pixels, 1))))
    max_k = max(1, min(max_k, 6))
    for k in range(1, max_k + 1):
        centers, labels = _kmeans(samples, k, rng)
        if k > 1 and _min_de00(centers) < cfg.min_series_delta_e:
            if _min_de00(centers) < cfg.ambiguous_delta_e:
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
    if samples.shape[0] > 8000:
        rng = np.random.Generator(np.random.PCG64(cfg.kmeans_seed))
        pick = rng.choice(samples.shape[0], size=8000, replace=False)
        samples = samples[pick]
    centers, ambiguous = _choose_centers(samples, cfg)
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
    return series
