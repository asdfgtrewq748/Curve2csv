"""The real-figure accuracy rule, on arrays rather than images."""

from __future__ import annotations

import numpy as np

from benchmarks.real.metrics import pair_metrics, score_figure


def _line(n: int = 400) -> np.ndarray:
    x = np.linspace(0.0, 10.0, n)
    return np.column_stack([x, 0.2 * x + 1.0])


def _score(gt: list[np.ndarray], pred: list[np.ndarray]) -> dict[str, object]:
    return score_figure(
        gt,
        pred,
        x_scale="linear",
        y_scale="linear",
        x_range=(0.0, 10.0),
        y_range=(0.0, 5.0),
        plot_w=400.0,
    )


def test_exact_line_is_correct() -> None:
    gt = _line()
    scored = _score([gt], [gt.copy()])
    assert scored["correct"] is True
    assert scored["reason"] == "ok"
    assert scored["worst_nrmse"] is not None and scored["worst_nrmse"] < 0.1
    assert scored["worst_coverage"] == 1.0
    assert scored["slope_rel_err"] is not None and scored["slope_rel_err"] < 1e-6


def test_missing_half_fails_coverage() -> None:
    gt = _line()
    pred = gt[gt[:, 0] <= 4.0]
    nrmse, coverage = pair_metrics(
        gt,
        pred,
        x_scale="linear",
        y_scale="linear",
        x_range=(0.0, 10.0),
        y_range=(0.0, 5.0),
        plot_w=400.0,
    )
    assert nrmse is not None and nrmse <= 2.0
    assert coverage < 0.90
    scored = _score([gt], [pred])
    assert scored["correct"] is False
    assert scored["reason"] == "x_coverage"


def test_extra_series_is_not_a_match() -> None:
    gt = _line()
    scored = _score([gt], [gt.copy(), gt.copy()])
    assert scored["correct"] is False
    assert scored["reason"] == "series_count"


def test_outliers_fail_nrmse_while_most_of_the_span_is_covered() -> None:
    gt = _line()
    pred = gt.copy()
    pred[::20, 1] += 2.5
    scored = _score([gt], [pred])
    assert scored["correct"] is False
    assert scored["reason"] == "nrmse"
    assert scored["worst_coverage"] is not None and scored["worst_coverage"] >= 0.90
