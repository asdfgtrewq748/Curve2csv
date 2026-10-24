"""Domain-shaped series used by the synthetic generator."""

from __future__ import annotations

import numpy as np

Shape = tuple[np.ndarray, np.ndarray]


def abutment_pressure(n: int, rng: np.random.Generator) -> Shape:
    """Yielded coal face, a peak, then decay back toward in-situ stress."""

    length = float(rng.uniform(40.0, 120.0))
    x = np.linspace(0.0, length, n)
    face = float(rng.uniform(0.35, 0.9))
    peak = float(rng.uniform(1.8, 3.8))
    peak_at = float(rng.uniform(3.0, 18.0))
    decay = float(rng.uniform(8.0, 28.0))
    power = float(rng.uniform(0.8, 1.5))
    rise = face + (peak - face) * np.clip(x / peak_at, 0.0, 1.0) ** power
    fall = 1.0 + (peak - 1.0) * np.exp(-(x - peak_at) / decay)
    y = np.where(x <= peak_at, rise, fall)
    return x, y


def support_load_cycle(n: int, rng: np.random.Generator) -> Shape:
    length = float(rng.uniform(60.0, 160.0))
    x = np.linspace(0.0, length, n)
    period = float(rng.uniform(10.0, 30.0))
    base = float(rng.uniform(18.0, 32.0))
    amp = float(rng.uniform(6.0, 18.0))
    phase = float(rng.uniform(0.0, period))
    u = np.mod(x + phase, period) / period
    y = base + amp * (u**1.15)
    return x, y


def stress_strain(n: int, rng: np.random.Generator) -> Shape:
    emax = float(rng.uniform(0.8, 2.4))
    x = np.linspace(0.0, emax, n)
    elastic_end = float(rng.uniform(0.12, 0.3) * emax)
    modulus = float(rng.uniform(25.0, 70.0))
    peak_x = elastic_end + float(rng.uniform(0.08, 0.28) * emax)
    peak = float(rng.uniform(1.05, 1.5)) * modulus * elastic_end
    residual = float(rng.uniform(0.35, 0.75)) * peak
    y = np.empty_like(x)
    elastic = x <= elastic_end
    hardening = (x > elastic_end) & (x <= peak_x)
    softening = x > peak_x
    y[elastic] = modulus * x[elastic]
    t_h = (x[hardening] - elastic_end) / max(peak_x - elastic_end, 1e-6)
    y0 = modulus * elastic_end
    y[hardening] = y0 + (peak - y0) * (1.0 - (1.0 - t_h) ** 2)
    t_s = np.clip((x[softening] - peak_x) / max(emax - peak_x, 1e-6), 0.0, 1.0)
    y[softening] = residual + (peak - residual) * np.exp(-3.0 * t_s)
    return x, y


def displacement_scatter(n: int, rng: np.random.Generator) -> Shape:
    xmax = float(rng.uniform(20.0, 100.0))
    x = np.sort(rng.uniform(0.0, xmax, size=n))
    slope = float(rng.uniform(-0.4, 1.2))
    intercept = float(rng.uniform(0.0, 4.0))
    noise = float(rng.uniform(0.04, 0.35))
    y = intercept + slope * (x / max(xmax, 1.0)) * 10.0 + rng.normal(0.0, noise, size=n)
    return x, y


def generic_smooth(n: int, rng: np.random.Generator) -> Shape:
    xmax = float(rng.choice(np.array([1.0, 10.0, 50.0, 100.0])))
    x = np.linspace(0.0, xmax, n)
    t = x / xmax
    y = np.zeros(n, dtype=np.float64)
    for _ in range(int(rng.integers(2, 4))):
        amp = float(rng.uniform(0.3, 1.3))
        freq = float(rng.uniform(0.5, 3.0))
        phase = float(rng.uniform(0.0, 2.0 * np.pi))
        y += amp * np.sin(2.0 * np.pi * freq * t + phase)
    y += float(rng.uniform(-0.4, 0.4))
    return x, y


def generic_noisy(n: int, rng: np.random.Generator) -> Shape:
    x, y = generic_smooth(n, rng)
    scale = float(np.ptp(y)) + 1e-6
    y = y + rng.normal(0.0, 0.04 * scale, size=n)
    return x, y


def step_shape(n: int, rng: np.random.Generator) -> Shape:
    xmax = float(rng.uniform(10.0, 50.0))
    x = np.linspace(0.0, xmax, n)
    levels_n = int(rng.integers(3, 6))
    edges = np.linspace(0.0, xmax, levels_n + 1)
    levels = rng.uniform(0.4, 9.0, size=levels_n)
    y = np.full(n, levels[-1], dtype=np.float64)
    for idx in range(levels_n):
        y[(x >= edges[idx]) & (x < edges[idx + 1])] = levels[idx]
    return x, y


def peaks(n: int, rng: np.random.Generator) -> Shape:
    xmax = float(rng.uniform(20.0, 80.0))
    x = np.linspace(0.0, xmax, n)
    y = np.zeros(n, dtype=np.float64)
    for _ in range(int(rng.integers(2, 5))):
        amp = float(rng.uniform(0.4, 3.0))
        mu = float(rng.uniform(0.1 * xmax, 0.9 * xmax))
        sigma = float(rng.uniform(0.6, 4.0))
        y += amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
    y += float(rng.uniform(0.0, 0.4))
    return x, y


def bar_heights(n: int, rng: np.random.Generator) -> Shape:
    x = np.arange(n, dtype=np.float64)
    y = rng.uniform(0.8, 10.0, size=n)
    return x, y


LINE_SHAPES = {
    "abutment_pressure": abutment_pressure,
    "support_load_cycle": support_load_cycle,
    "stress_strain": stress_strain,
    "generic_smooth": generic_smooth,
    "generic_noisy": generic_noisy,
    "step": step_shape,
    "peaks": peaks,
}

LABELS = {
    "abutment_pressure": ("Distance from coal face (m)", "Abutment pressure ratio"),
    "support_load_cycle": ("Advance (m)", "Support load (MN)"),
    "stress_strain": ("Strain (%)", "Stress (MPa)"),
    "displacement_scatter": ("Time (d)", "Displacement (mm)"),
    "generic_smooth": ("X", "Y"),
    "generic_noisy": ("X", "Y"),
    "step": ("Stage", "Value"),
    "peaks": ("Position", "Intensity"),
    "bar_values": ("Category", "Value"),
}
