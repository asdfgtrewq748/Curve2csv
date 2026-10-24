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

### Notes

- Regions that cannot be read are left empty and flagged. The main output never interpolates.
- M1 calibration uses caller-supplied or sidecar tick positions. Automatic tick-label OCR is not in this build. Log axes work when the caller sets the scale. The Android package cannot bundle RapidOCR: the Chaquopy index has no onnxruntime wheel. The on-device fallback is typed axis endpoints on the detected plot box.
