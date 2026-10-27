"""ONNX series segmentation. A missing or unchecked weight file returns None.

The rule-based separator stays the fallback. An empty list means the model
ran and found no series.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from curve2csv.color_math import rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.types import SeriesMask

_WEIGHTS = Path(__file__).resolve().parent.parent / "models" / "segmenter.onnx"
_DIGEST = _WEIGHTS.with_suffix(".sha256")


def weights_path() -> Path:
    return _WEIGHTS


def weights_ready() -> bool:
    if not _WEIGHTS.is_file() or not _DIGEST.is_file():
        return False
    expected = _DIGEST.read_text(encoding="utf-8").strip().split()[0].lower()
    actual = hashlib.sha256(_WEIGHTS.read_bytes()).hexdigest()
    return actual == expected


@lru_cache(maxsize=1)
def _load_session() -> object:
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session: object = ort.InferenceSession(
        str(_WEIGHTS),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    return session


def _drop_specks(mask: NDArray[np.bool_], min_area: int) -> NDArray[np.bool_]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    if count <= 1:
        return mask
    keep = np.zeros(mask.shape, dtype=bool)
    for index in range(1, count):
        if int(stats[index, cv2.CC_STAT_AREA]) >= min_area:
            keep[labels == index] = True
    return keep


def masks_from_output(
    output: NDArray[np.float32],
    rgb: NDArray[np.uint8],
    bbox: tuple[int, int, int, int] | None,
    *,
    threshold: float,
    tau: float,
    max_series: int,
    min_pixels: int,
) -> list[NDArray[np.bool_]]:
    """Cluster an NCHW-free ``9×H×W`` tensor into series masks.

    Channel 0 is an ink logit. Channels 1:9 are a unit embedding. Pixels
    outside the plot box (inset 2px) are dropped. Components under 12px and
    clusters under ``min_pixels`` are dropped. Masks are not closed, so gaps
    stay empty.
    """

    if output.ndim != 3 or output.shape[0] < 9:
        return []
    logit = output[0]
    embed = np.asarray(output[1:9], dtype=np.float32)
    prob = 1.0 / (1.0 + np.exp(-logit))
    ink = prob >= float(threshold)
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        inset = 2
        allowed = np.zeros(ink.shape, dtype=bool)
        y_lo = y0 + inset
        y_hi = y1 - inset
        x_lo = x0 + inset
        x_hi = x1 - inset
        if y_hi > y_lo and x_hi > x_lo:
            allowed[y_lo:y_hi, x_lo:x_hi] = True
        ink &= allowed
    ys, xs = np.nonzero(ink)
    if ys.size == 0:
        return []
    vecs = np.transpose(embed[:, ys, xs], (1, 0)).astype(np.float32, copy=False)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    vecs = vecs / np.maximum(norms, 1e-6)
    step = max(1, int(ys.size) // 2000)
    order = np.arange(0, ys.size, step)
    seed = vecs[order]
    taken = np.zeros(order.size, dtype=bool)
    leaders: list[NDArray[np.float32]] = []
    cap = max(1, max_series * 3)
    for index in range(order.size):
        if taken[index] or len(leaders) >= cap:
            continue
        leader = seed[index]
        taken |= seed @ leader >= tau
        leaders.append(leader)
    if not leaders:
        return []
    bank = np.stack(leaders, axis=0)
    for _ in range(2):
        scores = vecs @ bank.T
        assignment = np.argmax(scores, axis=1).astype(np.int32)
        similarity = scores[np.arange(ys.size), assignment]
        refreshed: list[NDArray[np.float32]] = []
        for cluster in range(bank.shape[0]):
            chosen = (assignment == cluster) & (similarity >= tau)
            if not np.any(chosen):
                refreshed.append(bank[cluster])
                continue
            mean = vecs[chosen].mean(axis=0)
            mean = mean / max(float(np.linalg.norm(mean)), 1e-6)
            refreshed.append(mean.astype(np.float32))
        bank = np.stack(refreshed, axis=0)
    scores = vecs @ bank.T
    assignment = np.argmax(scores, axis=1).astype(np.int32)
    similarity = scores[np.arange(ys.size), assignment]
    height, width = ink.shape
    masks: list[NDArray[np.bool_]] = []
    for cluster in range(bank.shape[0]):
        chosen = (assignment == cluster) & (similarity >= tau)
        if int(chosen.sum()) < min_pixels:
            continue
        mask = np.zeros((height, width), dtype=bool)
        mask[ys[chosen], xs[chosen]] = True
        mask = _drop_specks(mask, 12)
        if int(mask.sum()) < min_pixels:
            continue
        masks.append(mask)
    masks.sort(key=lambda item: int(item.sum()), reverse=True)
    return masks[:max_series]


def _color_lab(rgb: NDArray[np.uint8], mask: NDArray[np.bool_]) -> tuple[float, float, float]:
    mean = rgb[mask].mean(axis=0)
    lab = rgb2lab(np.asarray(mean, dtype=np.float64).reshape(1, 1, 3))[0, 0]
    return (float(lab[0]), float(lab[1]), float(lab[2]))


def segment_series(
    rgb: NDArray[np.uint8],
    bbox: tuple[int, int, int, int],
    config: PipelineConfig,
) -> list[SeriesMask] | None:
    """Series masks, or None when the learned weights cannot be used."""

    if not weights_ready():
        return None
    try:
        session = _load_session()
        image = np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1))[None]
        raw = session.run(None, {"image": image})  # type: ignore[attr-defined]
    except Exception:
        return None
    output = np.asarray(raw[0], dtype=np.float32)
    if output.ndim != 4 or output.shape[0] != 1:
        return None
    plane = output[0]
    if plane.shape[1:] != rgb.shape[:2]:
        return None
    masks = masks_from_output(
        plane,
        rgb,
        bbox,
        threshold=float(config.learned_threshold),
        tau=float(config.learned_tau),
        max_series=int(config.max_series),
        min_pixels=int(config.min_cluster_pixels),
    )
    series: list[SeriesMask] = []
    for index, mask in enumerate(masks):
        series.append(
            SeriesMask(
                series_id=f"s{index}",
                color_lab=_color_lab(rgb, mask),
                style="solid",
                mask=mask,
                separation_score=100.0,
                ambiguous=False,
            )
        )
    return series
