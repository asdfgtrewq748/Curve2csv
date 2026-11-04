# Week 2 slice report: evidence plumbing and human-confirm API

Branch: `w2-evidence` (base tip `8a145ef`, merge of PR #9).
Status: local commit on `w2-evidence` (the commit containing this report);
no threshold was lowered and the classical tracker was kept. Full OWID was
intentionally skipped after a one-figure smoke.

## 1. Evidence / honesty plumbing

### Gap vs bridge vs empty

- `DataPoint.status` is now explicit: `ok`, `flagged`, `bridge`, or `empty`.
  `empty` means the coordinate is blank (not interpolated). `bridge` is the only
  filled gap and always has `interpolated=1`.
- CSV has `status`, `segment_id`, and `calibration_id` columns after the existing
  `interpolated` column. JSON points carry the same fields; each series also has a
  `segments` summary (`start_x`, `end_x`, `n_points`, `n_bridged`, `n_empty`).
- `segment_id` is assigned to contiguous line runs. A plain missing column starts
  a new segment; an occlusion bridge is inserted column-by-column and stays in
  the same segment. `clear_range` re-runs this assignment so a locally cleared
  range is its own empty region.
- The QA overlay now draws plain gaps as a pale red band with a red rule below
  the axis and dashed red boundaries. Bridges remain magenta open squares. Line
  segments are not connected across a `segment_id` change.

### Fabrication reporting

- `fabrication_count` still means: an unflagged, confidence >= 0.5 output point
  that lands in a generator-invisible x interval or outside the plot box.
  Bridged points are excluded.
- The synthetic aggregate is asserted to equal the sum of the per-sample
  counters before the result JSON is written. `score_sample` remains the only
  source of that counter.
- On the real OWID set there is no invisible-range mask. The new per-figure
  `fabrication_count` there is deliberately narrower and report-only:
  unflagged, confidence >= 0.5 points outside the published x/y ranges. It is
  not in the real pass rule. The pass rule, thresholds, and GT files are
  unchanged.

### Ink support

- New report-only `ink_support` metric: for each measured (non-empty,
  non-bridged) point, check whether same-color ink exists within 2 px using
  CIEDE2000 <= 18. Reports `ink_support_fraction` and `ink_support_checked` per
  figure, and a median/check count in aggregates. It does not feed any gate.
- It is computed in both `benchmarks.metrics` (synthetic) and
  `benchmarks.real.evaluate` (real). The synthetic smoke JSON now includes it.

## 2. Human-confirm API skeleton

Public functions in `curve2csv/api.py` and re-exported from `curve2csv`:

- `confirm_plot_box(result, bbox)` - re-extract with a confirmed rectangle,
  keeping the existing calibration unless `axes` is supplied. The area source is
  `manual:plot_box`.
- `confirm_axis_calibration(result, axes)` - re-extract with confirmed tick
  pairs and keep the confirmed box.
- `pick_series(result, click_or_stroke)` - keep the nearest series for a click,
  or every touched series for a short pixel stroke. No coordinates are added.
- `clear_range(result, x_min, x_max, series_id=None)` - force the range empty.
  Points keep their pixel evidence but get blank `x`/`y`, `MANUAL`, no
  `INTERPOLATED` bit, and the range is merged into `series.gaps`.

CLI hooks: `curve2csv extract ... --plot-box x0,y0,x1,y1` and repeatable
`--clear-range XMIN:XMAX` or `--clear-range SERIES:XMIN:XMAX`. The edited
result is re-exported with the new fields.

No GUI polish was added in this slice; the API and CLI are the tested surface.

## 3. Tests and measurements

Commands run from `/workspace/repos/Curve2csv` with `.venv/bin/python`:

- `pytest -q`: **61 passed, 1 skipped** (the skipped test is the existing PDF
  optional-dependency case).
- `ruff check src tests benchmarks`: pass.
- `mypy --strict src/curve2csv`: pass.
- New tests cover exported status/segment/calibration fields, JSON schema,
  confirmed box/calibration, click/stroke series picking, and "clear range
  leaves empty, does not interpolate" in both API and CLI paths.
- New metric tests cover ink support and the fabrication aggregate = row-sum
  invariant.

Smoke before/after (same 60 generated figures, sidecar axes, same thresholds):

| metric | before (`HEAD`) | after |
|---|---:|---:|
| `fabrication_count` | 59 | **59** |
| `bridged_count` | 92 | 92 |
| `curve_nrmse_range_median` | 0.858736 | 0.858736 |
| `x_coverage_median` | 0.7975 | 0.7975 |
| `series_match_acc` | 0.813492 | 0.813492 |
| `scatter_f1_median` | 0.896552 | 0.896552 |
| `axis_calib_rel_err_median` | 3.06e-15 | 3.06e-15 |
| `runtime_s_median` | 0.2882 | 0.3422 |

The hard `fabrication_count == 0` gate still fails at 59, exactly as before; that
is the recorded existing state, not a regression. The smoke regression comparison
reports `smoke regression: ok`. Ink support on that run: median **1.0000**,
31962 measured points checked.

Real set: full OWID was skipped because it is optional for this slice. A single
representative real figure (`co2-long-term-concentration`) was re-scored through
the new real path: still correct (`reason=ok`), `fabrication_count=0`,
`ink_support_fraction=1.0` (694 points). Existing `benchmarks/results/real-v1*`
files were not regenerated.

## 4. Constraints respected

- Single-curve priority; no multi-curve separation changes.
- No chart-specific cheats, no GT edits, no threshold changes
  (`benchmarks/configs/m1.yaml` unchanged).
- The tracker, bridge length, and gap rules are unchanged.
- Push/PR: `git push origin w2-evidence` was attempted with
  `GIT_TERMINAL_PROMPT=0`; GitHub asked for a username, so the branch was not
  pushed. No GitHub PR was opened. The commit is local on `w2-evidence`; the
  hash is the tip of that branch.
