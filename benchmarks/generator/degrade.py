"""Photometric and small-angle geometric degradation. Geometry updates ground truth."""

from __future__ import annotations

import cv2
import numpy as np

from benchmarks.generator.spec import SampleSpec


def apply_points(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    if points.size == 0:
        return points.reshape(0, 2)
    hom = np.column_stack([points.astype(np.float64), np.ones(len(points))])
    return (hom @ matrix.T)[:, :2]


def degrade(
    rgb: np.ndarray, spec: SampleSpec, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Return the degraded RGB image and the 3x3 map from clean pixels to it."""

    image = rgb
    matrix = np.eye(3, dtype=np.float64)
    angle = float(spec.rotation_deg)
    if abs(angle) >= 1e-6:
        height, width = image.shape[:2]
        cosine, sine = abs(np.cos(np.deg2rad(angle))), abs(np.sin(np.deg2rad(angle)))
        new_w = int(np.ceil(width * cosine + height * sine))
        new_h = int(np.ceil(width * sine + height * cosine))
        affine = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), angle, 1.0)
        affine[0, 2] += (new_w - width) / 2.0
        affine[1, 2] += (new_h - height) / 2.0
        image = cv2.warpAffine(
            image,
            affine,
            (new_w, new_h),
            flags=cv2.INTER_LINEAR,
            borderValue=(255, 255, 255),
        )
        matrix = np.eye(3, dtype=np.float64)
        matrix[:2, :] = affine
    if spec.blur_sigma > 0:
        image = cv2.GaussianBlur(image, (0, 0), sigmaX=float(spec.blur_sigma))
    if spec.noise_sigma > 0:
        noise = rng.normal(0.0, float(spec.noise_sigma), size=image.shape)
        image = np.clip(image.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    if spec.jpeg_quality is not None:
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        ok, encoded = cv2.imencode(
            ".jpg",
            bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(spec.jpeg_quality)],
        )
        if not ok:
            raise RuntimeError("jpeg encode failed")
        decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
    return np.ascontiguousarray(image), matrix
