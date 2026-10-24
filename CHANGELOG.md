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

### Notes

- Regions that cannot be read are left empty and flagged. The main output never interpolates.
- M1 calibration uses caller-supplied or sidecar tick positions. OCR, log axes, and automatic tick reading are intentionally absent.
