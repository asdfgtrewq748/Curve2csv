"""Read tick labels with RapidOCR and calibrate from the ones that agree."""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

from curve2csv.color_math import rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.ocr.parse import _base, choose_axis, parse_label
from curve2csv.types import AxesOverride, AxisScale, PlotArea, TickInput

_ENGINE: object | None = None


@dataclass(frozen=True)
class _Word:
    text: str
    score: float
    cx: float
    cy: float
    x0: float
    x1: float
    y0: float
    y1: float


def _engine() -> object | None:
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    _ENGINE = RapidOCR()
    return _ENGINE


# One image is read twice (axis pass, then the label frame). Keep the words.
# The key includes a stride of pixels: a freed buffer can be reused at the
# same address for the next figure, so the pointer alone is not an identity.
_WORD_CACHE: tuple[tuple[int, int, int], bytes, list[_Word]] | None = None


def _recognize(rgb: np.ndarray) -> list[_Word]:
    engine = _engine()
    if engine is None or rgb.size == 0:
        return []
    result, _elapsed = engine(np.ascontiguousarray(rgb))  # type: ignore[operator]
    words: list[_Word] = []
    if not result:
        return words
    for item in result:
        box, text, score = item
        points = np.asarray(box, dtype=np.float64)
        words.append(
            _Word(
                text=str(text).strip(),
                score=float(score),
                cx=float(points[:, 0].mean()),
                cy=float(points[:, 1].mean()),
                x0=float(points[:, 0].min()),
                x1=float(points[:, 0].max()),
                y0=float(points[:, 1].min()),
                y1=float(points[:, 1].max()),
            )
        )
    return [word for word in words if word.score >= 0.4 and word.text]


def _labels_present(words: list[_Word], width: int, height: int) -> tuple[bool, bool]:
    """True when a numeric column and a numeric row are already in the words."""

    numeric = [word for word in words if parse_label(word.text)]
    has_y = False
    for group in _cluster(numeric, "x1", 14.0):
        if len(group) < 2:
            continue
        ys = [word.cy for word in group]
        if max(ys) - min(ys) >= 0.15 * height:
            has_y = True
            break
    has_x = False
    for group in _cluster(numeric, "cy", 16.0):
        if len(group) < 2:
            continue
        xs = [word.cx for word in group]
        if max(xs) - min(xs) >= 0.18 * width:
            has_x = True
            break
    return has_y, has_x


def _scaled_words(rgb: np.ndarray, scale: int, origin_x: float, origin_y: float) -> list[_Word]:
    big = cv2.resize(
        rgb,
        (rgb.shape[1] * scale, rgb.shape[0] * scale),
        interpolation=cv2.INTER_CUBIC,
    )
    scaled: list[_Word] = []
    for word in _recognize(big):
        scaled.append(
            _Word(
                text=word.text,
                score=word.score,
                cx=origin_x + word.cx / scale,
                cy=origin_y + word.cy / scale,
                x0=origin_x + word.x0 / scale,
                x1=origin_x + word.x1 / scale,
                y0=origin_y + word.y0 / scale,
                y1=origin_y + word.y1 / scale,
            )
        )
    return scaled


def _margin_words(rgb: np.ndarray, *, need_y: bool, need_x: bool) -> list[_Word]:
    """Re-read a margin at higher resolution.

    Grapher tick labels are about ten pixels tall. RapidOCR skips them on the
    full image and reads them after a 3–4× scale of that strip alone.
    """

    height, width = rgb.shape[:2]
    found: list[_Word] = []
    if need_y:
        strip_w = int(min(width, max(90, round(0.16 * width))))
        for word in _scaled_words(rgb[:, :strip_w], 4, 0.0, 0.0):
            if word.x1 > strip_w - 1.0 or word.y1 - word.y0 > 36.0:
                continue
            if len(word.text) > 18 or not parse_label(word.text):
                continue
            found.append(word)
    if need_x:
        strip_h = int(min(height, max(80, round(0.18 * height))))
        origin_y = float(height - strip_h)
        for word in _scaled_words(rgb[height - strip_h :, :], 3, 0.0, origin_y):
            if word.y0 < origin_y + 1.0 or word.x1 - word.x0 > 0.28 * width:
                continue
            if len(word.text) > 18 or not parse_label(word.text):
                continue
            found.append(word)
    return found


def _merge_words(primary: list[_Word], extra: list[_Word]) -> list[_Word]:
    merged = list(primary)
    for word in extra:
        close = next(
            (
                kept
                for kept in merged
                if abs(word.cx - kept.cx) < 12.0 and abs(word.cy - kept.cy) < 12.0
            ),
            None,
        )
        if close is None:
            merged.append(word)
            continue
        # The full-image pass sometimes drops the minus on "-2%".
        if word.text.strip().startswith("-") and not close.text.strip().startswith("-"):
            merged.remove(close)
            merged.append(word)
    return merged


def _words(rgb: np.ndarray) -> list[_Word]:
    global _WORD_CACHE
    sample = np.ascontiguousarray(rgb[::16, ::16]).tobytes()
    key = (int(rgb.shape[0]), int(rgb.shape[1]), int(rgb.shape[2]) if rgb.ndim == 3 else 1)
    if _WORD_CACHE is not None and _WORD_CACHE[0] == key and _WORD_CACHE[1] == sample:
        return _WORD_CACHE[2]
    native = _expand_glued_years(_recognize(rgb))
    if native:
        height, width = rgb.shape[:2]
        has_y, has_x = _labels_present(native, width, height)
        # The y strip is re-read even when some labels were found: a 4× pass
        # picks up 0, 1.0, and 1.2 that the full image skips.
        extra = _margin_words(rgb, need_y=True, need_x=not has_x)
        if not has_y or not has_x or extra:
            native = _expand_glued_years(_merge_words(native, extra))
    _WORD_CACHE = (key, sample, native)
    return native


def _expand_glued_years(words: list[_Word]) -> list[_Word]:
    """Split a token such as ``20202025`` into the two years inside its box.

    Endpoint ticks on a grapher are sometimes close enough that RapidOCR
    returns one string. Each half keeps its own center so the axis fit can
    use both.
    """

    widths = [
        word.x1 - word.x0
        for word in words
        if re.fullmatch(r"\d{4}", re.sub(r"\s+", "", _base(word.text)))
    ]
    typical = float(np.median(widths)) if widths else 36.0
    expanded: list[_Word] = []
    for word in words:
        compact = re.sub(r"\s+", "", _base(word.text))
        match = re.fullmatch(r"(\d{4})(\d{4})", compact)
        width = word.x1 - word.x0
        if match is None or width <= 1.55 * max(typical, 8.0):
            expanded.append(word)
            continue
        left_value = int(match.group(1))
        right_value = int(match.group(2))
        if not (
            1000 <= left_value <= 2100 and 1000 <= right_value <= 2100 and left_value != right_value
        ):
            expanded.append(word)
            continue
        mid = 0.5 * (word.x0 + word.x1)
        expanded.append(
            _Word(
                text=str(left_value),
                score=word.score,
                cx=0.5 * (word.x0 + mid),
                cy=word.cy,
                x0=word.x0,
                x1=mid,
                y0=word.y0,
                y1=word.y1,
            )
        )
        expanded.append(
            _Word(
                text=str(right_value),
                score=word.score,
                cx=0.5 * (mid + word.x1),
                cy=word.cy,
                x0=mid,
                x1=word.x1,
                y0=word.y0,
                y1=word.y1,
            )
        )
    return expanded


def _anchor_era_endpoints(group: list[_Word]) -> list[_Word]:
    """Put a BCE label on the outer edge of its text, not the glyph center.

    ``803,719 BCE`` is start-anchored and ``2025`` beside it is end-anchored.
    Their centers sit inside the axis and stretch the year scale.
    """

    if len(group) < 2:
        return group
    ordered = sorted(group, key=lambda word: word.cx)
    left, right = ordered[0], ordered[-1]
    upper = left.text.upper()
    if "BCE" not in upper and not upper.endswith("BC") and " BC" not in upper:
        return group

    def _move(word: _Word, cx: float) -> _Word:
        return _Word(word.text, word.score, cx, word.cy, word.x0, word.x1, word.y0, word.y1)

    return [
        _move(word, word.x0) if word is left else _move(word, word.x1) if word is right else word
        for word in group
    ]


def _split(words: list[_Word], area: PlotArea) -> tuple[list[_Word], list[_Word]]:
    x0, y0, x1, y1 = area.bbox
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    xs: list[_Word] = []
    ys: list[_Word] = []
    for word in words:
        in_x = x0 - 0.12 * width <= word.cx <= x1 + 0.08 * width
        in_y = y0 - 0.08 * height <= word.cy <= y1 + 0.12 * height
        below = word.cy >= y1 - 0.04 * height and word.cy <= y1 + 0.28 * height
        left = word.cx <= x0 - 2.0 and word.cx >= x0 - 0.45 * width
        # A y label sitting on the bottom tick is left of the spine. Treating
        # it as an x label pulls a 0 into the x row and the fit abstains.
        if left and in_y:
            ys.append(word)
        elif below and in_x and word.cx >= x0 - 4.0:
            xs.append(word)
    return xs, ys


def _dedupe(words: list[_Word], *, horizontal: bool) -> list[_Word]:
    ordered = sorted(words, key=lambda word: word.cx if horizontal else word.cy)
    kept: list[_Word] = []
    for word in ordered:
        if kept:
            previous = kept[-1]
            gap = abs(
                (word.cx if horizontal else word.cy) - (previous.cx if horizontal else previous.cy)
            )
            if gap < 8.0 and word.text == previous.text:
                if word.score > previous.score:
                    kept[-1] = word
                continue
        kept.append(word)
    return kept


def read_axes(
    rgb: np.ndarray,
    area: PlotArea,
    config: PipelineConfig | None = None,
) -> AxesOverride | None:
    """Build tick pairs from label text. ``None`` when OCR is missing or disagrees."""

    cfg = config or PipelineConfig()
    x_words, y_words = _split(_words(rgb), area)
    x_words = _dedupe(x_words, horizontal=True)
    y_words = _dedupe(y_words, horizontal=False)
    x0, _y0, _x1, y1 = area.bbox
    x_labels = [(word.cx, word.text) for word in x_words]
    y_labels = [(word.cy, word.text) for word in y_words]
    x_choice = choose_axis(x_labels, vertical=False, config=cfg)
    y_choice = choose_axis(y_labels, vertical=True, config=cfg)
    if x_choice is None or y_choice is None:
        return None
    x_pairs, x_scale = x_choice
    y_pairs, y_scale = y_choice
    return AxesOverride(
        x_ticks=tuple(
            TickInput(px=position, py=float(y1), value=value) for position, value in x_pairs
        ),
        y_ticks=tuple(
            TickInput(px=float(x0), py=position, value=value) for position, value in y_pairs
        ),
        x_scale=x_scale if isinstance(x_scale, AxisScale) else AxisScale(x_scale),
        y_scale=y_scale if isinstance(y_scale, AxisScale) else AxisScale(y_scale),
        source="ocr",
    )


def _cluster(words: list[_Word], key: str, tol: float) -> list[list[_Word]]:
    ordered = sorted(words, key=lambda word: float(getattr(word, key)))
    groups: list[list[_Word]] = []
    for word in ordered:
        coord = float(getattr(word, key))
        if groups:
            previous = float(getattr(groups[-1][-1], key))
            if abs(coord - previous) <= tol:
                groups[-1].append(word)
                continue
        groups.append([word])
    return groups


def _bottom_spine(
    gray: np.ndarray,
    y_ref: float,
    left_hint: float,
    right_hint: float,
    reach: float,
) -> tuple[float, float, float] | None:
    """Return ``(y, x_start, x_end)`` of the lowest long axis at or below ``y_ref``.

    The lowest numeric label is often one tick above the baseline (the zero
    tick was not read). Searching down about one tick interval finds that
    baseline when it is darker than the grid.
    """

    height, width = gray.shape
    y0 = max(0, int(round(y_ref)) - 6)
    y1 = min(height, int(round(y_ref + max(reach, 12.0))) + 1)
    if y1 <= y0:
        return None
    ink = gray[y0:y1] < 210
    min_run = max(40, int(0.28 * width))
    found: tuple[float, float, float] | None = None
    for row_index in range(ink.shape[0]):
        idx = np.flatnonzero(ink[row_index])
        if idx.size == 0:
            continue
        breaks = np.flatnonzero(np.diff(idx) > 4)
        starts = np.concatenate([[0], breaks + 1])
        ends = np.concatenate([breaks, [idx.size - 1]])
        best: tuple[int, int] | None = None
        for start, end in zip(starts, ends, strict=True):
            x_start = int(idx[start])
            x_end = int(idx[end])
            if x_end - x_start < min_run:
                continue
            if x_end < left_hint or x_start > right_hint:
                continue
            if best is None or (x_end - x_start) > (best[1] - best[0]):
                best = (x_start, x_end)
        if best is None:
            continue
        # The lowest qualifying row is the baseline, not the gridline at the
        # lowest label.
        found = (float(y0 + row_index), float(best[0]), float(best[1]))
    return found


def _raise_top_along_stroke(
    rgb: np.ndarray,
    left: float,
    right: float,
    top: float,
    spacing: float,
) -> float:
    """Follow a stroke that continues above the highest y tick.

    Grapher leaves unlabeled headroom above the top gridline, and the line is
    real ink there. The walk stops at the first gap, so a title or logo above
    that gap is not pulled into the frame.
    """

    if rgb.ndim != 3 or rgb.shape[2] < 3:
        return top
    lab = rgb2lab(rgb[:, :, :3])
    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    height, width = chroma.shape
    x0 = max(0, int(np.floor(left)))
    x1 = min(width, int(np.ceil(right)))
    if x1 - x0 < 10:
        return top
    cap = max(0, int(round(top - min(max(spacing, 8.0), 80.0))))
    start = min(height - 1, max(0, int(round(top))))

    def cols_at(row: int) -> np.ndarray:
        if row < 0 or row >= height:
            return np.zeros(0, dtype=np.int32)
        return np.flatnonzero(chroma[row, x0:x1] >= 12.0).astype(np.int32)

    prev = cols_at(start)
    if prev.size == 0 or prev.size > 80:
        return top
    new_top = float(start)
    gap = 0
    for row in range(start - 1, cap - 1, -1):
        cols = cols_at(row)
        if cols.size == 0 or cols.size > 80:
            gap += 1
            if gap >= 3:
                break
            continue
        delta = cols.astype(np.int32)[:, None] - prev.astype(np.int32)[None, :]
        if bool(np.any(np.abs(delta) <= 8)):
            new_top = float(row)
            prev = cols
            gap = 0
        else:
            gap += 1
            if gap >= 3:
                break
    return new_top


def _lower_bottom_along_stroke(
    rgb: np.ndarray,
    left: float,
    right: float,
    bottom: float,
    spacing: float,
) -> float:
    """Follow a stroke that continues below the lowest read y tick.

    Same-sex marriage and the craftsmen wage tail are drawn past the last
    label OCR kept. The walk stops at a gap, so the footer stays outside.
    """

    if rgb.ndim != 3 or rgb.shape[2] < 3:
        return bottom
    lab = rgb2lab(rgb[:, :, :3])
    chroma = np.sqrt(lab[:, :, 1] ** 2 + lab[:, :, 2] ** 2)
    height, width = chroma.shape
    x0 = max(0, int(np.floor(left)))
    x1 = min(width, int(np.ceil(right)))
    if x1 - x0 < 10:
        return bottom
    cap = min(height - 1, int(round(bottom + min(max(2.5 * spacing, 40.0), 160.0))))
    start = min(height - 1, max(0, int(round(bottom))))

    def cols_at(row: int) -> np.ndarray:
        if row < 0 or row >= height:
            return np.zeros(0, dtype=np.int32)
        return np.flatnonzero(chroma[row, x0:x1] >= 12.0).astype(np.int32)

    prev = cols_at(start)
    if prev.size == 0:
        return bottom
    new_bottom = float(start)
    gap = 0
    for row in range(start + 1, cap + 1):
        cols = cols_at(row)
        if cols.size == 0 or cols.size > 0.85 * (x1 - x0):
            gap += 1
            if gap >= 3:
                break
            continue
        delta = cols.astype(np.int32)[:, None] - prev.astype(np.int32)[None, :]
        if bool(np.any(np.abs(delta) <= 8)):
            new_bottom = float(row)
            prev = cols
            gap = 0
        else:
            gap += 1
            if gap >= 3:
                break
    return new_bottom


def _snap(position: float, target: float, limit: float = 48.0) -> float:
    if abs(position - target) <= limit:
        return target
    return position


def _span_from_labels(
    label_left: float,
    label_right: float,
    *,
    spine_left: float | None = None,
    spine_right: float | None = None,
    y_axis: float | None = None,
) -> tuple[float, float]:
    """Plot width from every reliable edge, never from the shortest one.

    A dark piece of the series sitting on a light axis is a short horizontal
    run. Using that run as the only width cuts the frame off inside the ticks
    that were actually read.
    """

    left = [label_left]
    right = [label_right]
    if y_axis is not None:
        left.append(y_axis)
    if spine_left is not None:
        left.append(spine_left)
    if spine_right is not None:
        right.append(spine_right)
    return min(left), max(right)


def _x_tick_marks(
    gray: np.ndarray,
    bottom: float,
    label_top: float,
    *,
    label_left: float | None = None,
    label_right: float | None = None,
) -> list[float]:
    """Centers of short vertical tick marks just below the x baseline.

    Grapher anchors the first and last x labels to the plot edge, so their
    text centers sit inside the true tick by half a label. Interior labels are
    centered. Reading the marks puts the endpoint ticks back on the frame;
    rows without marks keep the text positions. The search stays under the x
    label row, so descenders of the left y labels are not marks.
    """

    if gray.ndim != 2 or gray.size == 0:
        return []
    height, width = gray.shape
    y0 = max(0, int(np.floor(bottom)) + 1)
    y1 = min(height, int(np.ceil(label_top)), y0 + 8)
    if y1 - y0 < 2:
        return []
    band = gray[y0:y1, :] < 240
    counts = band.sum(axis=0)
    need = max(2, int(np.ceil(0.45 * (y1 - y0))))
    columns = np.flatnonzero(counts >= need)
    if label_left is not None:
        columns = columns[columns >= int(np.floor(label_left)) - 2]
    if label_right is not None:
        columns = columns[columns <= int(np.ceil(label_right)) + 2]
    if columns.size == 0:
        return []
    starts = np.concatenate(([0], np.flatnonzero(np.diff(columns) > 1) + 1))
    ends = np.concatenate((starts[1:] - 1, [columns.size - 1]))
    marks: list[float] = []
    for start, end in zip(starts, ends, strict=True):
        span = int(columns[end] - columns[start] + 1)
        if span <= 8 and columns[end] < width:
            marks.append(float(columns[start] + columns[end]) / 2.0)
    return marks


def _snap_x_to_ticks(
    pairs: list[tuple[float, float]],
    marks: list[float],
) -> list[tuple[float, float]]:
    """Move an edge-anchored x label onto its tick mark.

    Only a gross offset is corrected. Interior labels already sit on their
    marks, and a one-pixel nudge there can move a well-calibrated axis enough
    to change a marginal score. The Grapher first/last label is off by about
    half a label, which is what this picks up.
    """

    if len(marks) < 2 or not pairs:
        return pairs
    ordered = sorted(position for position, _value in pairs)
    gaps = np.diff(np.asarray(ordered, dtype=np.float64))
    gap = float(np.median(gaps)) if gaps.size else 0.0
    if gap <= 0:
        return pairs
    limit = max(6.0, 0.45 * gap)
    min_offset = 2.5
    mark_array = np.asarray(marks, dtype=np.float64)
    candidates: list[tuple[float, int, int]] = []
    for index, (position, _value) in enumerate(pairs):
        mark_index = int(np.argmin(np.abs(mark_array - position)))
        distance = abs(float(mark_array[mark_index]) - position)
        if min_offset <= distance <= limit:
            candidates.append((distance, index, mark_index))
    if not candidates:
        return pairs
    assigned: dict[int, float] = {}
    used: set[int] = set()
    for _distance, index, mark_index in sorted(candidates):
        if index in assigned or mark_index in used:
            continue
        assigned[index] = float(mark_array[mark_index])
        used.add(mark_index)
    return [(assigned.get(index, position), value) for index, (position, value) in enumerate(pairs)]


def read_frame(
    rgb: np.ndarray,
    config: PipelineConfig | None = None,
) -> tuple[PlotArea, AxesOverride] | None:
    """Locate the plot from tick labels when the spines are too light to detect.

    Used only after spine detection abstains, so figures that already have a
    dark axis box keep that box. Label centers are the tick positions, except
    that a visibly edge-anchored first/last label is moved onto its short x
    tick mark. A long horizontal stroke under the x labels, when one exists,
    also replaces the outer label centers so start-anchored and end-anchored
    endpoint text does not pull the box inward.
    """

    cfg = config or PipelineConfig()
    height, width = rgb.shape[:2]
    numeric = [word for word in _words(rgb) if parse_label(word.text)]
    if len(numeric) < 4:
        return None
    # Y labels on these charts are end-anchored, so their right edges line up
    # even when a short "0" has a center near the first x label. Claim that
    # column first so the bottom tick is not absorbed into the x row.
    y_group: list[_Word] | None = None
    y_key: tuple[int, float] | None = None
    for group in _cluster(numeric, "x1", 14.0):
        if len(group) < 2:
            continue
        ys = [word.cy for word in group]
        if max(ys) - min(ys) < 0.15 * height:
            continue
        median_x = float(np.median([word.x1 for word in group]))
        key = (len(group), -median_x)
        if y_key is None or key > y_key:
            y_key = key
            y_group = group
    if y_group is None:
        return None
    used = {(word.cx, word.cy, word.text) for word in y_group}
    remaining = [word for word in numeric if (word.cx, word.cy, word.text) not in used]
    x_group: list[_Word] | None = None
    best_key: tuple[int, float] | None = None
    for group in _cluster(remaining, "cy", 16.0):
        if len(group) < 2:
            continue
        xs = [word.cx for word in group]
        if max(xs) - min(xs) < 0.18 * width:
            continue
        median_y = float(np.median([word.cy for word in group]))
        if median_y < 0.08 * height:
            continue
        key = (len(group), median_y)
        if best_key is None or key > best_key:
            best_key = key
            x_group = group
    if x_group is None:
        return None
    x_group = _anchor_era_endpoints(x_group)
    x_choice = choose_axis([(word.cx, word.text) for word in x_group], vertical=False, config=cfg)
    y_choice = choose_axis([(word.cy, word.text) for word in y_group], vertical=True, config=cfg)
    if x_choice is None or y_choice is None:
        return None
    x_pairs, x_scale = x_choice
    y_pairs, y_scale = y_choice
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    y_positions = sorted(pos for pos, _value in y_pairs)
    if len(y_positions) >= 2:
        spacing = float(np.median(np.diff(np.asarray(y_positions, dtype=np.float64))))
    else:
        spacing = 36.0
    spine = _bottom_spine(
        gray,
        y_positions[-1],
        min(pos for pos, _value in x_pairs),
        max(pos for pos, _value in x_pairs),
        max(18.0, 1.6 * spacing),
    )
    label_left = min(pos for pos, _value in x_pairs)
    label_right = max(pos for pos, _value in x_pairs)
    if spine is not None:
        _spine_y, spine_left, spine_right = spine
        snapped: list[tuple[float, float]] = []
        for pos, value in x_pairs:
            if pos == label_left:
                snapped.append((_snap(pos, spine_left), value))
            elif pos == label_right:
                snapped.append((_snap(pos, spine_right), value))
            else:
                snapped.append((pos, value))
        x_pairs = snapped
        left, right = _span_from_labels(
            label_left,
            label_right,
            spine_left=spine_left,
            spine_right=spine_right,
        )
        bottom = float(spine[0])
    else:
        left, right = _span_from_labels(label_left, label_right)
        bottom = max(pos for pos, _value in y_pairs)
    # The first and last x labels are edge-anchored in Grapher exports, so
    # their glyph centers sit inside the true ticks. Snap to the marks when
    # they are visible; without marks the text positions remain.
    marks = _x_tick_marks(
        gray,
        bottom,
        min(word.y0 for word in x_group),
        label_left=min(word.x0 for word in x_group),
        label_right=max(word.x1 for word in x_group),
    )
    x_pairs = _snap_x_to_ticks(x_pairs, marks)
    label_left = min(pos for pos, _value in x_pairs)
    label_right = max(pos for pos, _value in x_pairs)
    if spine is not None:
        _spine_y, spine_left, spine_right = spine
        left, right = _span_from_labels(
            label_left,
            label_right,
            spine_left=spine_left,
            spine_right=spine_right,
        )
    else:
        left, right = _span_from_labels(label_left, label_right)
    top = min(pos for pos, _value in y_pairs)
    top = _raise_top_along_stroke(rgb, left, right, top, spacing)
    bottom = _lower_bottom_along_stroke(rgb, left, right, bottom, spacing)
    if right - left < 30.0 or bottom - top < 30.0:
        return None
    # Pad past the stroke. The foreground mask insets by one pixel, and a
    # series that rides the baseline would otherwise be clipped.
    pad = 3.0
    left_i = int(np.clip(round(left - pad), 0, width - 1))
    right_i = int(np.clip(round(right + pad), 0, width - 1))
    top_i = int(np.clip(round(top - pad), 0, height - 1))
    bottom_i = int(np.clip(round(bottom + pad), 0, height - 1))
    if right_i - left_i < 20 or bottom_i - top_i < 20:
        return None
    area = PlotArea(
        bbox=(left_i, top_i, right_i, bottom_i),
        x_axis_px=float(bottom_i),
        y_axis_px=float(left_i),
        score=0.6,
        corners=(
            (float(left_i), float(top_i)),
            (float(right_i), float(top_i)),
            (float(right_i), float(bottom_i)),
            (float(left_i), float(bottom_i)),
        ),
    )
    axes = AxesOverride(
        x_ticks=tuple(
            TickInput(px=position, py=float(bottom_i), value=value) for position, value in x_pairs
        ),
        y_ticks=tuple(
            TickInput(px=float(left_i), py=position, value=value) for position, value in y_pairs
        ),
        x_scale=x_scale if isinstance(x_scale, AxisScale) else AxisScale(x_scale),
        y_scale=y_scale if isinstance(y_scale, AxisScale) else AxisScale(y_scale),
        source="ocr",
    )
    return area, axes
