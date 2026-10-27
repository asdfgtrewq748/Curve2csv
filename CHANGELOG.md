# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- Core digitizing pipeline for linear-axis line, scatter, and bar charts: plot-area detection, sidecar/manual calibration, color separation, extraction, confidence, and flags.
- Export of CSV, JSON (`schema_version` 1.0), a QA overlay PNG, and a metrics file on every extraction.
- Reproducible synthetic benchmark generator (`synth-v0.1`), evaluator, and smoke regression gate.
- Unit, property, golden, and generator tests. GitHub Actions runs lint, mypy, pytest, and `make bench-smoke`.
- `curve2csv extract IMAGE -o DIR` with `--axes` or `--xmin/--xmax/--ymin/--ymax` (optional `--x-log` / `--y-log`).
- Android debug app (`android/`, Chaquopy, Python 3.10, minSdk 24): photo or gallery, two-tap crop, typed axis endpoints, on-device extract, share CSV. GitHub Actions uploads `curve2csv-debug-apk`.
- CIELAB and CIEDE2000 in pure NumPy (`color_math.py`) so the core imports on Android, where scikit-image has no wheel.
- Desktop window (`curve2csv` with no arguments, or `curve2csv gui`): open an image or a PDF page, optional two-click crop, typed axis endpoints, QA overlay, series rename, export. Optional `gui` extra adds PDF rendering and file drop.
- `curve2csv --headless-smoke IMAGE -o DIR` runs one extract without a window and prints `SMOKE_OK`. GitHub Actions builds a Windows exe with PyInstaller and uploads `curve2csv-windows-exe`.
- Desktop and CLI tick-label OCR via RapidOCR (`rapidocr-onnxruntime`, Apache-2.0) when the `ocr` extra is installed. Linear and log10 axes are calibrated from the labels. Typed endpoints stay the fallback when the labels do not agree. The Windows exe collects the ONNX runtime and models.
- Real-figure set `owid-grapher-v1`: Our World in Data line and scatter grapher PNGs with CSV ground truth and SVG tick ranges, CC BY 4.0, split into dev and held-out before scoring. A chart is included when it shows 1–6 series (`selectedEntityNames`, the same cap as `max_series`). Stacked area and bar charts are excluded from the published chart type. See `BENCHMARK.md` and `benchmarks/results/real-v1.md`.

### Notes

- Regions that cannot be read are left empty and flagged. The main output never interpolates.
- The Android package cannot bundle RapidOCR: the Chaquopy index has no onnxruntime wheel. The on-device fallback is typed axis endpoints on the detected plot box. Desktop OCR is not part of the APK.
- Real-figure accuracy on `owid-grapher-v1` before this extraction pass, measured at `cbbe5f1` with Python 3.12.3 and onnxruntime 1.31.0: dev 25/49 (51.0%), held-out 27/61 (44.3%), full set 52/110 (47.3%).
- Real-figure accuracy after recovering clipped frames and connected steep strokes, same split and pass rule, Python 3.12.3: dev 31/49 (63.3%), held-out 38/61 (62.3%), full set 69/110 (62.7%). The 90% target was not met. Held-out failures: series_count 7, nrmse_and_coverage 7, x_coverage 6, no_calibration 3. Full-set failures: nrmse_and_coverage 13, x_coverage 13, series_count 10, no_calibration 5. Per-figure reasons are in `benchmarks/results/real-v1.md`. No points are interpolated.
- Real-figure accuracy after merging each stroke with its anti-aliased fringe, same split and pass rule, Python 3.12.3: dev 31/49 (63.3%), held-out 39/61 (63.9%), full set 70/110 (63.6%). The 90% target was not met. `fish-catch-uk` is the one newly passing chart. No previously passing chart regressed. Held-out failures: x_coverage 8, nrmse_and_coverage 7, series_count 4, no_calibration 3. Full-set failures: x_coverage 15, nrmse_and_coverage 14, series_count 6, no_calibration 5. `global-smallpox-cases`, `diphtheria-cases-in-the-united-states`, `rubella-cases-in-the-united-states`, and `deaths-from-smallpox-in-london` stay failures: median signed error is about 0, and a run of years sits tens of pixels off the published CSV. The trace is the ink; those charts are not rewritten to match the CSV. `cumulative-space-visits` (Russia) stays a scatter with empty gaps. Per-figure reasons are in `benchmarks/results/real-v1.md`.
- Learned extractor (`--extractor learned`), trained only on synthetic charts (seed 20261025, 80/8, 400 steps) and measured at `ab65cf9` with Python 3.12.3: dev 0/49 (0%), held-out 0/61 (0%), full set 0/110 (0%). The rule-path table on the same split stays dev 31/49 (63.3%), held-out 39/61 (63.9%), full set 70/110 (63.6%). The 90% target was not met, and this pass stops here. Learned held-out failures: series_count 52, x_coverage 5, no_calibration 3, nrmse_and_coverage 1. Full-set failures: series_count 92, x_coverage 11, no_calibration 5, nrmse_and_coverage 2. Of the held-out series_count misses, 37 predict exactly one extra series; on 10 of those the matched series already have NRMSE ≤ 2% and x-coverage ≥ 0.90. The next lever is to keep a stroke and its anti-aliased fringe in one cluster. Per-figure rows are in `benchmarks/results/real-v1-learned.md`. The rule-path rows stay in `benchmarks/results/real-v1.md`.
- Learned-path smoke (60 figures, sidecar axes, same scorer): `fabrication_count` 21, `curve_nrmse_range_median` 2.198, `x_coverage_median` 0.346, `series_match_acc` 0.417, `scatter_f1_median` 0.897. The default extractor remains `rules`, so `make bench-smoke` still scores the rule path. ONNX weights are 84488 bytes and 20449 parameters, sha256 `3e49085c899725a9037549cbc4dbef514567f30d881d23d58880f21c580e98bf`. OWID CPU time is 0.856 s/image mean (0.729 s median); separation inside that is 86 ms mean (81 ms median). Smoke CPU time is 0.455 s/image mean. Android keeps the rule path.
- `make bench-smoke` still matches the checked-in smoke regression metrics (`curve_nrmse_range_median` 0.859). `fabrication_count` on that 60-figure smoke split is still 46 on the rule path; the hard gate remains 0. Those points are on-color ink inside generator-invisible x ranges. Keeping broken-stroke fragments, and clearing the crossing flag on a single ridge, both counted additional invisible-range points, so neither shipped. The 2000-figure synth-test was not re-run. Its published numbers stay the ones recorded at `553d01d`.
- CI installs from `benchmarks/requirements.lock`. Packages that dropped Python 3.10 wheels are pinned to the newest release that still has one (`contourpy` 1.3.2, `fonttools` 4.65.0, `coverage` 7.16.2, `ImageIO` 2.38.0, `networkx` 3.4.2, `tifffile` 2025.5.10, `onnxruntime` 1.23.2, `shapely` 2.1.2). The Tk window is omitted from the 80% coverage gate; the headless smoke covers that entry point.
