"""Color-constrained column path for one series, plus a short occlusion bridge.

The path is a Viterbi chain over this series' own vertical runs. A run whose
color does not match the series loses to the occluded state, so the tracker
does not jump onto another stroke. The occluded state emits a point only for a
narrow bridge: another series covers the predicted row, the hole is at most
``round(line_width) + OCCLUSION_SLACK_PX`` columns, and both sides already have
a supported run of this series. ``OCCLUSION_SLACK_PX`` is 2. Plain gaps, marker
gaps, and plot edges stay empty.

Penalties live here, not in :class:`PipelineConfig`. A thin step costs at most
0.90, and one occluded column costs 1.40, so a steep stroke stays on its ink.
A run whose color is another series costs an extra 6 and loses to occlusion.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from curve2csv.color_math import deltaE_ciede2000

OCCLUSION_SLACK_PX = 2
_JUMP_CAP_PX = 36.0
_THICK_RATIO = 2.2
_MIN_SUPPORT = 16
_INF = 1.0e6
_OCC_EMIT = 1.40
_OCC_ENTER = 0.40


@dataclass(frozen=True)
class TrackNode:
    """One column of the chosen path. ``kind`` is ``ink`` or ``bridge``."""

    col: int
    py: float
    kind: str
    thickness: float
    color_delta: float
    n_runs: int


@dataclass(frozen=True)
class _Run:
    rows: np.ndarray
    py: float
    thickness: int
    delta_e: float


def _runs(rows: np.ndarray) -> list[np.ndarray]:
    if rows.size == 0:
        return []
    splits = np.where(np.diff(rows) > 2)[0] + 1
    return [part for part in np.split(rows, splits) if part.size]


def _connected(prev: np.ndarray, rows: np.ndarray) -> bool:
    if prev.size == 0 or rows.size == 0:
        return False
    lo = int(prev[0]) - 8
    hi = int(prev[-1]) + 8
    return bool(np.any((rows >= lo) & (rows <= hi)))


def _emission(run: _Run, est_width: float, thin_width: float) -> float:
    # A steep stroke covers more rows in one column than the nominal width.
    # That column must stay cheaper than occlusion. Only a swatch (many times
    # the stroke width) loses to the occluded state. A 1px fringe loses to the core.
    width = max(est_width, 1.0)
    ratio = float(run.thickness) / width
    cost = 0.12
    if ratio < 1.0:
        cost += 0.35 * (1.0 - ratio)
    elif ratio > 8.0:
        cost += 2.0
    if run.delta_e > 28.0:
        cost += 6.0
    elif run.delta_e > 17.0:
        # A mild mismatch must stay cheaper than the occluded state, or a
        # JPEG-shifted core pixel would delete the stroke.
        cost += 0.25
    return cost


def _step_cost(
    dy: float,
    thickness: float,
    est_width: float,
    thin_width: float,
    *,
    connected: bool,
) -> float:
    if thickness > _THICK_RATIO * est_width and (not connected or abs(dy) > _JUMP_CAP_PX):
        return _INF
    width = max(thin_width, 1.0)
    # A steep thin stroke moves many pixels per column and must stay cheaper
    # than one occluded column. The cap is what enforces that.
    return min(0.90, 0.04 * min(abs(dy), 80.0) / width)


def _column_runs(
    mask: np.ndarray,
    col: int,
    y0: int,
    y1: int,
    lab_image: np.ndarray | None,
    color_lab: np.ndarray | None,
) -> list[_Run]:
    local = np.flatnonzero(mask[y0:y1, col])
    found: list[_Run] = []
    for part in _runs(local):
        image_rows = part + y0
        delta = 0.0
        if lab_image is not None and color_lab is not None and image_rows.size:
            samples = lab_image[image_rows, col]
            delta = float(np.min(deltaE_ciede2000(samples, color_lab)))
        found.append(
            _Run(
                rows=image_rows,
                py=float(np.mean(image_rows) + 0.5),
                thickness=int(image_rows.size),
                delta_e=delta,
            )
        )
    return found


def _other_covers(other_mask: np.ndarray, col: int, py: float, thin_width: float) -> bool:
    height = other_mask.shape[0]
    radius = max(1, int(round(thin_width)))
    row = int(np.clip(round(py - 0.5), 0, height - 1))
    lo = max(0, row - radius)
    hi = min(height, row + radius + 1)
    return bool(np.any(other_mask[lo:hi, col]))


def _bridge_columns(
    left: list[tuple[_Run, int]],
    right: list[tuple[_Run, int]],
    *,
    x0: int,
    x1: int,
    thin_width: float,
    other_mask: np.ndarray | None,
) -> list[TrackNode]:
    if other_mask is None or len(left) < _MIN_SUPPORT or len(right) < _MIN_SUPPORT:
        return []
    left_col = left[-1][1]
    right_col = right[0][1]
    gap = right_col - left_col - 1
    max_gap = max(1, int(round(thin_width))) + OCCLUSION_SLACK_PX
    if gap < 1 or gap > max_gap:
        return []
    left_y = left[-1][0].py
    right_y = right[0][0].py
    dy_limit = max(_JUMP_CAP_PX, 4.0 * thin_width) * float(gap)
    if abs(right_y - left_y) > dy_limit:
        return []
    span = float(right_col - left_col)
    nodes: list[TrackNode] = []
    for col in range(left_col + 1, right_col):
        if col <= x0 + 1 or col >= x1 - 2:
            return []
        t = (col - left_col) / span
        py = (1.0 - t) * left_y + t * right_y
        if not _other_covers(other_mask, col, py, thin_width):
            return []
        nodes.append(TrackNode(col, py, "bridge", 0.0, 0.0, 0))
    return nodes


def track_series(
    mask: np.ndarray,
    bbox: tuple[int, int, int, int],
    *,
    est_width: float,
    thin_width: float,
    color_lab: tuple[float, float, float] | None,
    lab_image: np.ndarray | None,
    other_mask: np.ndarray | None,
) -> list[TrackNode]:
    """Return the ink path and any approved occlusion bridges, in column order."""

    x0, y0, x1, y1 = bbox
    if x1 <= x0:
        return []
    color = None if color_lab is None else np.asarray(color_lab, dtype=np.float64)
    width = max(1, x1 - x0)
    columns: list[list[_Run]] = []
    for col in range(x0, x1):
        runs = _column_runs(mask, col, y0, y1, lab_image, color)
        if len(runs) > 6:
            runs.sort(key=lambda run: _emission(run, est_width, thin_width))
            runs = runs[:6]
        columns.append(runs)

    cost_run: list[np.ndarray] = []
    cost_occ: list[float] = []
    prev_run: list[np.ndarray] = []
    prev_kind: list[np.ndarray] = []
    prev_occ_kind: list[int] = []
    prev_occ_index: list[int] = []
    anchor_y: list[np.ndarray] = []
    anchor_col: list[np.ndarray] = []
    occ_anchor_y: list[float] = []
    occ_anchor_col: list[int] = []

    for index, runs in enumerate(columns):
        n = len(runs)
        run_cost = np.full(n, _INF, dtype=np.float64)
        run_prev = np.full(n, -1, dtype=np.int32)
        run_kind = np.zeros(n, dtype=np.int32)  # 0 = run, 1 = occluded
        run_anchor_y = np.full(n, np.nan, dtype=np.float64)
        run_anchor_col = np.full(n, -1, dtype=np.int32)
        col = x0 + index
        if index == 0:
            for i, run in enumerate(runs):
                run_cost[i] = _emission(run, est_width, thin_width)
                run_anchor_y[i] = run.py
                run_anchor_col[i] = col
            cost_run.append(run_cost)
            cost_occ.append(_OCC_EMIT)
            prev_run.append(run_prev)
            prev_kind.append(run_kind)
            prev_occ_kind.append(-1)
            prev_occ_index.append(-1)
            anchor_y.append(run_anchor_y)
            anchor_col.append(run_anchor_col)
            occ_anchor_y.append(float("nan"))
            occ_anchor_col.append(-1)
            continue

        prev_runs = columns[index - 1]
        best_occ = _INF
        best_occ_kind = -1
        best_occ_index = -1
        best_occ_anchor_y = float("nan")
        best_occ_anchor_col = -1
        for j, _prev in enumerate(prev_runs):
            arrive = float(cost_run[index - 1][j]) + _OCC_ENTER
            if arrive < best_occ:
                best_occ = arrive
                best_occ_kind = 0
                best_occ_index = j
                best_occ_anchor_y = float(anchor_y[index - 1][j])
                best_occ_anchor_col = int(anchor_col[index - 1][j])
        stay = cost_occ[index - 1]
        if stay < best_occ:
            best_occ = stay
            best_occ_kind = 1
            best_occ_index = 0
            best_occ_anchor_y = occ_anchor_y[index - 1]
            best_occ_anchor_col = occ_anchor_col[index - 1]
        best_occ += _OCC_EMIT

        largest = max(runs, key=lambda run: run.thickness) if runs else None
        for i, run in enumerate(runs):
            best = _INF
            kind = 0
            prev_i = -1
            kept_anchor_y = run.py
            kept_anchor_col = col
            emit = _emission(run, est_width, thin_width)
            for j, prev in enumerate(prev_runs):
                # A thick riser or swatch is not a sample. The largest run owns
                # the column: a thinner fragment inside it must not be followed.
                if largest is not None and float(largest.thickness) > _THICK_RATIO * est_width:
                    joined = _connected(prev.rows, largest.rows)
                    if not joined or abs(largest.py - prev.py) > _JUMP_CAP_PX:
                        continue
                step = _step_cost(
                    run.py - prev.py,
                    float(run.thickness),
                    est_width,
                    thin_width,
                    connected=_connected(prev.rows, run.rows),
                )
                if step >= _INF:
                    continue
                arrive = float(cost_run[index - 1][j]) + step + emit
                if arrive < best:
                    best = arrive
                    kind = 0
                    prev_i = j
                    kept_anchor_y = run.py
                    kept_anchor_col = col
            if np.isfinite(occ_anchor_y[index - 1]):
                riser = (
                    largest is not None
                    and float(largest.thickness) > _THICK_RATIO * est_width
                    and abs(largest.py - occ_anchor_y[index - 1]) > _JUMP_CAP_PX
                )
                step = (
                    _INF
                    if riser
                    else _step_cost(
                        run.py - occ_anchor_y[index - 1],
                        float(run.thickness),
                        est_width,
                        thin_width,
                        connected=False,
                    )
                )
            else:
                step = 0.15
            arrive = cost_occ[index - 1] + step + emit
            if step < _INF and arrive < best:
                best = arrive
                kind = 1
                prev_i = 0
                kept_anchor_y = run.py
                kept_anchor_col = col
            run_cost[i] = best
            run_kind[i] = kind
            run_prev[i] = prev_i
            run_anchor_y[i] = kept_anchor_y
            run_anchor_col[i] = kept_anchor_col

        cost_run.append(run_cost)
        cost_occ.append(best_occ)
        prev_run.append(run_prev)
        prev_kind.append(run_kind)
        prev_occ_kind.append(best_occ_kind)
        prev_occ_index.append(best_occ_index)
        anchor_y.append(run_anchor_y)
        anchor_col.append(run_anchor_col)
        occ_anchor_y.append(best_occ_anchor_y)
        occ_anchor_col.append(best_occ_anchor_col)

    chosen: list[_Run | None] = [None] * width
    if width:
        last_runs = columns[-1]
        best_run = float(np.min(cost_run[-1])) if last_runs else _INF
        if last_runs and best_run < _INF and best_run <= cost_occ[-1]:
            state_kind = 0
            state_index = int(np.argmin(cost_run[-1]))
        else:
            state_kind = 1
            state_index = 0
        for index in range(width - 1, -1, -1):
            if state_kind == 0 and 0 <= state_index < len(columns[index]):
                chosen[index] = columns[index][state_index]
                kind = int(prev_kind[index][state_index])
                prev_i = int(prev_run[index][state_index])
            else:
                chosen[index] = None
                kind = prev_occ_kind[index]
                prev_i = prev_occ_index[index]
            if index == 0 or kind < 0 or prev_i < 0:
                break
            state_kind = kind
            state_index = prev_i

    segments: list[list[tuple[_Run, int]]] = []
    current: list[tuple[_Run, int]] = []
    for index, picked in enumerate(chosen):
        if picked is None:
            if current:
                segments.append(current)
                current = []
            continue
        current.append((picked, x0 + index))
    if current:
        segments.append(current)

    kept = [segment for segment in segments if len(segment) >= _MIN_SUPPORT]
    nodes: list[TrackNode] = []
    for seg_index, segment in enumerate(kept):
        if seg_index > 0:
            nodes.extend(
                _bridge_columns(
                    kept[seg_index - 1],
                    segment,
                    x0=x0,
                    x1=x1,
                    thin_width=thin_width,
                    other_mask=other_mask,
                )
            )
        for run, col in segment:
            column_runs = columns[col - x0]
            nodes.append(
                TrackNode(
                    col=col,
                    py=run.py,
                    kind="ink",
                    thickness=float(run.thickness),
                    color_delta=run.delta_e,
                    n_runs=len(column_runs),
                )
            )
    nodes.sort(key=lambda node: node.col)
    return nodes
