"""Turn OCR strings into axis values and choose linear vs log10.

RapidOCR (Apache-2.0) often glues a matplotlib power-of-ten label ``10`` and its
superscript into ``101``. Those strings are kept as a second reading and used
only when every label on the axis has that shape.
"""

from __future__ import annotations

import re

import numpy as np

from curve2csv.calibrate.model import fit_axis_1d
from curve2csv.config import PipelineConfig
from curve2csv.types import AxisCalibration, AxisScale

_SUPERS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUPER_DIGITS = "0123456789"
_MULT = {
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
    "trillion": 1e12,
}
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _base(text: str) -> str:
    cleaned = text.strip().replace("−", "-").replace("–", "-").replace("—", "-")
    cleaned = cleaned.replace("×", "x").replace("∗", "x")
    # A tick mark beside a label is often read as a trailing dash: "1.0 -".
    cleaned = re.sub(r"\s+-\s*$", "", cleaned)
    # RapidOCR reads a lone zero as the letter O ("O years") or D ("D").
    cleaned = re.sub(r"(?<![A-Za-z0-9])[OoD](?=\s|$)", "0", cleaned)
    out: list[str] = []
    index = 0
    while index < len(cleaned):
        char = cleaned[index]
        if char in _SUPERS or (
            char in "⁻-" and index + 1 < len(cleaned) and cleaned[index + 1] in _SUPERS
        ):
            out.append("^")
            while index < len(cleaned) and (cleaned[index] in _SUPERS or cleaned[index] in "⁻-"):
                if cleaned[index] in _SUPERS:
                    out.append(_SUPER_DIGITS[_SUPERS.index(cleaned[index])])
                elif cleaned[index] in "⁻-":
                    out.append("-")
                index += 1
            continue
        out.append(char)
        index += 1
    # Thousands separators are punctuation, not decimals: "1,000" → "1000".
    return re.sub(r"(?<=\d),(?=\d)", "", "".join(out))


def _is_concat_power(text: str) -> bool:
    compact = _base(text).replace(" ", "")
    return re.fullmatch(r"10\d", compact) is not None


def parse_label(text: str) -> list[tuple[float, str]]:
    """Return ``(value, kind)`` readings. ``kind`` is ``plain`` or ``power10``."""

    raw = _base(text)
    if not raw:
        return []
    compact = raw.replace(" ", "")
    found: list[tuple[float, str]] = []

    power = re.fullmatch(rf"({_NUMBER})?[xX]?10\^([-+]?\d+)", compact)
    if power is not None:
        mantissa = float(power.group(1)) if power.group(1) else 1.0
        found.append((mantissa * 10.0 ** int(power.group(2)), "power10"))
        return found

    if _is_concat_power(raw):
        exponent = int(compact[-1])
        found.append((float(compact), "plain"))
        found.append((10.0**exponent, "power10"))
        return found

    unit = re.fullmatch(
        rf"({_NUMBER})%?(?:\s+(thousand|million|billion|trillion))?(?:\s+(BCE|BC|CE|AD))?(?:\s+[A-Za-z%/°]+)*",
        raw,
        flags=re.IGNORECASE,
    )
    if unit is not None:
        value = float(unit.group(1))
        word = (unit.group(2) or "").lower()
        if word in _MULT:
            value *= _MULT[word]
        era = (unit.group(3) or "").upper()
        if era in {"BCE", "BC"}:
            value = -abs(value)
        found.append((value, "plain"))
    return found


def _fit_pairs(
    pairs: list[tuple[float, float]],
    *,
    vertical: bool,
    config: PipelineConfig | None,
) -> tuple[float, int, AxisScale, list[tuple[float, float]]] | None:
    positions = [position for position, _value in pairs]
    values = [value for _position, value in pairs]
    best: tuple[float, int, AxisScale, list[tuple[float, float]]] | None = None
    for scale in (AxisScale.LINEAR, AxisScale.LOG10):
        fitted = fit_axis_1d(
            np.asarray(positions, dtype=np.float64),
            np.asarray(values, dtype=np.float64),
            axis="y" if vertical else "x",
            scale=scale,
            source="ocr",
            config=config,
        )
        if not isinstance(fitted, AxisCalibration):
            continue
        rank = (fitted.residual_rel, -fitted.n_ticks_used)
        if best is None or rank < (best[0], best[1]):
            best = (fitted.residual_rel, -fitted.n_ticks_used, scale, pairs)
    return best


def choose_axis(
    labels: list[tuple[float, str]],
    *,
    vertical: bool,
    config: PipelineConfig | None = None,
) -> tuple[list[tuple[float, float]], AxisScale] | None:
    """Pick a value reading and a scale. Positions are pixels along the axis.

    A single label that does not lie on the line (two years glued into one
    token, for example) is dropped when the other ticks already agree. The
    full set is kept whenever it fits.
    """

    parsed: list[tuple[float, str, list[tuple[float, str]]]] = []
    for position, text in labels:
        readings = parse_label(text)
        if readings:
            parsed.append((position, text, readings))
    if len(parsed) < 2:
        return None

    def _values(kind: str) -> list[tuple[float, float]]:
        chosen: list[tuple[float, float]] = []
        for position, _text, readings in parsed:
            match = next((value for value, tag in readings if tag == kind), None)
            if match is not None:
                chosen.append((position, match))
        return chosen

    plain = _values("plain")
    sets: list[list[tuple[float, float]]] = []
    if len(parsed) >= 2 and all(_is_concat_power(text) for _pos, text, _c in parsed):
        powers = _values("power10")
        if len(powers) >= 2:
            sets.append(powers)
    elif len(plain) >= 2:
        sets.append(plain)

    best: tuple[float, int, AxisScale, list[tuple[float, float]]] | None = None
    for pairs in sets:
        fitted = _fit_pairs(pairs, vertical=vertical, config=config)
        if fitted is None and len(pairs) >= 4:
            for index in range(len(pairs)):
                subset = [pair for item, pair in enumerate(pairs) if item != index]
                trial = _fit_pairs(subset, vertical=vertical, config=config)
                if trial is None:
                    continue
                if fitted is None or (trial[0], trial[1]) < (fitted[0], fitted[1]):
                    fitted = trial
        if fitted is None:
            continue
        if best is None or (fitted[0], fitted[1]) < (best[0], best[1]):
            best = fitted
    if best is None:
        return None
    return best[3], best[2]
