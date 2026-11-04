# Week 1 wave 2 report (PR #9 lineage)

Branch: `pr-9`, based on tip `59b6171` (wave 1). Work is committed locally; no
GitHub PR was opened. No GitHub authentication was attempted because the task
only requires a local commit and this report.

## Outcome

The smallest general fix that paid off was x endpoint tick alignment. Grapher
exports edge-anchor the first and last x labels, so OCR text centers are about
half a label inside the true tick. The old frame and x fit were therefore
compressed inward. `read_frame` now reads the visible short tick marks under the
axis, moves only labels offset by at least 2.5 px, and rebuilds the frame from
those endpoints. The 2.5 px floor is deliberate: snapping sub-pixel interior
jitter changed a passing CO2 chart into a failure.

Measured with the versions in `benchmarks/requirements.lock` (Python 3.13.5,
numpy 2.1.3, OpenCV 4.10.0.84, scipy 1.14.1, rapidocr-onnxruntime 1.4.4,
matplotlib 3.9.2, onnxruntime 1.23.2), same split, same pass rule, same GT:

| split | before | after | net |
|---|---:|---:|---:|
| held-out | 42/61 | 47/61 | +5 |
| single-curve held-out | 38/46 | 43/46 | +5 |
| dev | 33/49 | 35/49 | +2 |
| full set | 75/110 | 82/110 | +7 |

Strict and with-bridge are identical in both runs. No previously passing chart
regressed. The baseline was reproduced exactly (75/110) by disabling only
`_x_tick_marks`, so the +7 is attributable to this patch and not to a different
environment.

## Charts gained

| chart | split | before NRMSE / coverage | after NRMSE / coverage |
|---|---|---:|---:|
| `wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000` | held-out | 2.686 / 0.750 | 0.266 / 1.000 |
| `growth-of-global-trade` | held-out | 1.533 / 0.870 | 0.159 / 1.000 |
| `uk-gdp-growth-19572016` | held-out | 7.211 / 0.465 | 0.785 / 0.970 |
| `rubella-cases-in-the-united-states` | held-out | 3.047 / 0.800 | 0.560 / 0.945 |
| `diphtheria-cases-in-the-united-states` | held-out | 3.646 / 0.835 | 0.651 / 0.965 |
| `northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c` | dev | recorded fail | ok |
| `working-hours-uk-millennium` | dev | recorded fail | ok |

`co2-long-term-concentration` is unchanged at 0.985 / 0.920.

## Craftsmen isolation

- Plot area comes from `read_frame`; the OWID spines are too light for
  `detect_plot_area`.
- OCR x label centers: 1200 at 55.5 px, 1300 at 139.5, ..., 2000 at 817.5.
- True ticks below the baseline: 39.5, 138.5, ..., 832.5.
- The first and last labels are edge-anchored, so their centers are 16 px and
  15 px inside the tick. Interior labels are within about 1 px.
- The old fit compressed the year scale and put the right frame at x≈817. The
  blue stroke continues to x≈834, so part of the visible line to 2000 was
  outside the box.
- Using the endpoint ticks moves the frame from `(53, 106, 821, 535)` to
  `(36, 106, 836, 535)` and the score from 2.686 / 0.750 to 0.266 / 1.000.
  The extracted line grows from 761 to 777 columns. There are no bridges and
  no tracker holes. The y ticks were already fine. GT was not changed.

## Other touched charts

- `growth-of-global-trade`: the right edge was clipped at x≈820; the true 2000
  tick is at 832.5. Following the already-visible stroke to x≈834 gives
  0.159 / 1.000. No tail was invented.
- `uk-gdp-growth-19572016`: visible anchors remain 8% / −10% and 1957 / 2020.
  The endpoint tick frame changes the x slope from 0.09918 to 0.09610 and the
  score from 7.211 / 0.465 to 0.785 / 0.970. No chart-specific override was
  added. The external 0.67 / 0.980 correlation is still not reproduced, but the
  official NRMSE/coverage now passes on the same visible green line.
- `rubella` and `diphtheria`: the left endpoint label is anchored inward, so
  the old frame started at x=76. The true tick is at x=60; recovering the early
  visible ink turns both into passes.
- `co2-long-term-concentration`: the first version of the patch also moved
  interior labels by about 1 px. It improved the least-squares residual but
  changed x sampling and turned 0.985 / 0.920 into 2.756 / 0.940. The 2.5 px
  offset floor restricts the fix to visibly edge-anchored labels and keeps CO2
  passing.

## Code and constraints

Changed files:

- `src/curve2csv/ocr/read.py`: `_x_tick_marks`, `_snap_x_to_ticks`, and the
  frame recomputation in `read_frame`.
- `tests/unit/test_ocr.py`: unit coverage for mark detection and the 2.5 px
  guard behavior.
- `docs/W1_WAVE2.md` and `docs/DIAGNOSE_heldout_fails.md`: isolation and
  before/after notes.
- `benchmarks/results/real-v1.json` / `.md`, `real-v1-held-out.json` / `.md`,
  and the two baseline copies used for the comparison.
- `BENCHMARK.md` and `CHANGELOG.md`: measured wave-2 entry.

No GT file, pass threshold, tracker penalty, mask rule, or occlusion bridge
length changed. No point was fabricated. Short occlusion bridges remain marked
`interpolated=1` and are still excluded from strict scoring.

## Smoke and tests

- Smoke was regenerated and scored with the same tooling: `fabrication_count`
  59, `bridged_count` 92, `curve_nrmse_range_median` 0.859,
  `x_coverage_median` 0.798, `series_match_acc` 0.813. This is identical to the
  baseline smoke, so the patch does not add synthetic false points.
- `tests/unit/test_ocr.py`, `tests/unit/test_real_metrics.py`: 16 passed.
- Ruff check and format check pass on the changed Python files.
- The full 110-chart rerun was feasible and was run; the baseline was rerun in
  the same environment with only `_x_tick_marks` disabled.

## Reproduction

```bash
python -m benchmarks.real.evaluate --split all
python -m benchmarks.real.evaluate --split held-out

# baseline in the same environment
python - <<'PY'
import sys
import curve2csv.ocr.read as ocr
ocr._x_tick_marks = lambda *args, **kwargs: []
import benchmarks.real.evaluate as evaluate
sys.argv = ["evaluate", "--split", "all"]
evaluate.main()
PY
```

Saved measurements: `benchmarks/results/real-v1.json` (after, full set),
`benchmarks/results/real-v1-held-out.json` (after, held-out),
`benchmarks/results/real-v1-baseline-locked.json` (baseline full set), and
`benchmarks/results/real-v1-heldout-baseline-locked.json` (baseline held-out).
