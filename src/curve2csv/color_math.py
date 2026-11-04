"""sRGB ↔ CIELAB and CIEDE2000 without a native image library.

The desktop package used to call scikit-image for these three functions.
scikit-image does not publish an Android wheel, and the on-device app runs
this module instead. The formulas follow the sRGB / D65 path used by
scikit-image so series separation stays the same.
"""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray

_XN = 95.047
_YN = 100.0
_ZN = 108.883
_DELTA = 6.0 / 29.0


def _as_float_rgb(rgb: NDArray[np.generic]) -> NDArray[np.float64]:
    array = np.asarray(rgb, dtype=np.float64)
    if array.size and float(np.max(array)) > 1.0:
        array = array / 255.0
    return array


def _linearize(channel: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.where(channel <= 0.04045, channel / 12.92, ((channel + 0.055) / 1.055) ** 2.4)


def _compand(channel: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.where(
        channel <= 0.0031308,
        12.92 * channel,
        1.055 * np.power(np.maximum(channel, 0.0), 1.0 / 2.4) - 0.055,
    )


def _f_lab(t: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.where(t > _DELTA**3, np.cbrt(t), t / (3.0 * _DELTA**2) + 4.0 / 29.0)


def _f_lab_inv(t: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.where(t > _DELTA, t**3, 3.0 * _DELTA**2 * (t - 4.0 / 29.0))


def rgb2lab(rgb: NDArray[np.generic]) -> NDArray[np.float64]:
    """Convert sRGB to CIELAB. Accepts 0–1 floats or 0–255 ints."""

    red, green, blue = np.moveaxis(_as_float_rgb(rgb), -1, 0)
    r_lin, g_lin, b_lin = _linearize(red), _linearize(green), _linearize(blue)
    x = (0.4124564 * r_lin + 0.3575761 * g_lin + 0.1804375 * b_lin) * 100.0
    y = (0.2126729 * r_lin + 0.7151522 * g_lin + 0.0721750 * b_lin) * 100.0
    z = (0.0193339 * r_lin + 0.1191920 * g_lin + 0.9503041 * b_lin) * 100.0
    fx, fy, fz = _f_lab(x / _XN), _f_lab(y / _YN), _f_lab(z / _ZN)
    light = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    stacked = np.stack([light, a, b], axis=-1)
    return cast(NDArray[np.float64], np.asarray(stacked, dtype=np.float64))


def lab2rgb(lab: NDArray[np.generic]) -> NDArray[np.float64]:
    """Convert CIELAB to sRGB floats in 0–1."""

    light, a, b = np.moveaxis(np.asarray(lab, dtype=np.float64), -1, 0)
    fy = (light + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    x = _XN * _f_lab_inv(fx)
    y = _YN * _f_lab_inv(fy)
    z = _ZN * _f_lab_inv(fz)
    r_lin = (3.2404542 * x + -1.5371385 * y + -0.4985314 * z) / 100.0
    g_lin = (-0.9692660 * x + 1.8760108 * y + 0.0415560 * z) / 100.0
    b_lin = (0.0556434 * x + -0.2040259 * y + 1.0572252 * z) / 100.0
    rgb = np.stack([_compand(r_lin), _compand(g_lin), _compand(b_lin)], axis=-1)
    clipped = np.clip(rgb, 0.0, 1.0)
    return cast(NDArray[np.float64], np.asarray(clipped, dtype=np.float64))


def deltaE_ciede2000(
    lab1: NDArray[np.generic],
    lab2: NDArray[np.generic],
) -> NDArray[np.float64]:
    """CIEDE2000 color difference. Both arrays broadcast like scikit-image."""

    first = np.asarray(lab1, dtype=np.float64)
    second = np.asarray(lab2, dtype=np.float64)
    l1, a1, b1 = first[..., 0], first[..., 1], first[..., 2]
    l2, a2, b2 = second[..., 0], second[..., 1], second[..., 2]
    c1 = np.hypot(a1, b1)
    c2 = np.hypot(a2, b2)
    c_bar = 0.5 * (c1 + c2)
    c_bar7 = c_bar**7
    g = 0.5 * (1.0 - np.sqrt(c_bar7 / (c_bar7 + 25.0**7)))
    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = np.hypot(a1p, b1)
    c2p = np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0
    dl = l2 - l1
    dc = c2p - c1p
    dh = h2p - h1p
    dh = np.where(dh > 180.0, dh - 360.0, dh)
    dh = np.where(dh < -180.0, dh + 360.0, dh)
    dh = np.where((c1p * c2p) == 0.0, 0.0, dh)
    dhp = 2.0 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh) / 2.0)
    l_bar = 0.5 * (l1 + l2)
    c_bar_p = 0.5 * (c1p + c2p)
    h_sum = h1p + h2p
    h_bar = np.where(np.abs(h1p - h2p) > 180.0, h_sum + 360.0, h_sum)
    h_bar = np.where((c1p * c2p) == 0.0, h_sum, h_bar)
    h_bar = (0.5 * h_bar) % 360.0
    t = (
        1.0
        - 0.17 * np.cos(np.radians(h_bar - 30.0))
        + 0.24 * np.cos(np.radians(2.0 * h_bar))
        + 0.32 * np.cos(np.radians(3.0 * h_bar + 6.0))
        - 0.20 * np.cos(np.radians(4.0 * h_bar - 63.0))
    )
    sl = 1.0 + (0.015 * (l_bar - 50.0) ** 2) / np.sqrt(20.0 + (l_bar - 50.0) ** 2)
    sc = 1.0 + 0.045 * c_bar_p
    sh = 1.0 + 0.015 * c_bar_p * t
    dt = 30.0 * np.exp(-(((h_bar - 275.0) / 25.0) ** 2))
    rc = 2.0 * np.sqrt(c_bar_p**7 / (c_bar_p**7 + 25.0**7))
    rt = -np.sin(np.radians(2.0 * dt)) * rc
    delta = np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dhp / sh) ** 2 + rt * (dc / sc) * (dhp / sh))
    return cast(NDArray[np.float64], np.asarray(delta, dtype=np.float64))
