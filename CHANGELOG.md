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
- Real-figure accuracy on `owid-grapher-v1`, measured at `cbbe5f1` with Python 3.12.3 and onnxruntime 1.31.0: dev 25/49 (51.0%), held-out 27/61 (44.3%), full set 52/110 (47.3%). The 90% target was not met. Most misses are x-coverage below 0.90: a near-vertical column is left as a gap, and flagged samples are removed before scoring. Per-figure reasons are in `benchmarks/results/real-v1.md`.
- `make bench-smoke` still matches the checked-in smoke regression metrics. `fabrication_count` on that 60-figure smoke split was 46; the hard gate is 0. The 2000-figure synth-test was not re-run. Its published numbers stay the ones recorded at `553d01d`. Flag changes in this commit can move `fabrication_count` if that split is scored again.
- CI installs from `benchmarks/requirements.lock`. Packages that dropped Python 3.10 wheels are pinned to the newest release that still has one (`contourpy` 1.3.2, `fonttools` 4.65.0, `coverage` 7.16.2, `ImageIO` 2.38.0, `networkx` 3.4.2, `tifffile` 2025.5.10, `onnxruntime` 1.23.2, `shapely` 2.1.2). The Tk window is omitted from the 80% coverage gate; the headless smoke covers that entry point.
