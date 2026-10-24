# Curve2csv

Digitize scientific line, scatter, and bar charts into CSV, JSON, and a QA overlay.

**Status:** milestone M1 (linear axes, sidecar calibration, synthetic benchmark) is in progress. Measured numbers live in `benchmarks/results/` after a benchmark run. This page does not quote them.

The main output never invents points. A column the pipeline cannot read is left empty and flagged.

## Install

```bash
pip install -e ".[dev,bench]"
```

Python 3.10 or newer.

## Commands

```bash
pip install -e ".[dev,bench]"
python -m benchmarks.generator.cli --config benchmarks/configs/m1.yaml --split test --out data/synth-v0.1
python -m benchmarks.evaluate --config benchmarks/configs/m1.yaml --data data/synth-v0.1 --split test \
       --out benchmarks/results --tag M1
python -m benchmarks.report benchmarks/results/M1.json > benchmarks/results/M1.md
make bench-smoke   # CI: generate the smoke split, evaluate, compare with baseline/smoke.json
```

Debug one figure with caller-supplied ticks, or with the four axis endpoints:

```bash
python -m curve2csv IMG --axes axes.json --out DIR
python -m curve2csv extract IMG -o DIR --axes axes.json
python -m curve2csv extract IMG -o DIR --xmin 0 --xmax 1 --ymin 0 --ymax 1
```

`axes.json` is `{"x": {"ticks": [{"px", "py", "value"}]}, "y": {...}}`. `--x-log` and `--y-log` mark an endpoint pair as log10. With neither `--axes` nor all four limits, the command exits 2. This build does not read tick labels.

## Desktop window

With no arguments, `curve2csv` opens a window (Tkinter): open an image or one PDF page, click two corners to crop, type the axis endpoints, extract, rename a series label, and export the CSV, JSON, and overlay. `pip install -e ".[gui]"` adds PDF rendering (`pypdfium2`) and drag-and-drop (`tkinterdnd2`). Tick labels are still typed, not recognized.

A packaged Windows build is produced on `windows-latest` and uploaded as `curve2csv-windows-exe` (`dist/curve2csv/curve2csv.exe` plus the libraries beside it). The workflow runs:

```bash
curve2csv --headless-smoke IMAGE -o DIR
```

That prints `SMOKE_OK` when the CSV and overlay exist. There is no macOS app.

## Android

The debug app lives in `android/`. It is a Chaquopy 17 project (Python 3.10) because that is the combination that produced an APK: the Chaquopy Android index has an OpenCV 4.5.1.48 wheel for CPython 3.10, and none for 3.11+. NumPy is 1.26.2 and Pillow is 11.0.0, the newest wheels on that index. `minSdk` is 24. Build with `./gradlew :app:assembleDebug` from `android/` (the host Python must be 3.10; set `CURVE2CSV_PYTHON` if `python3.10` is not on `PATH`). GitHub Actions uploads `curve2csv-debug-apk`.

On device the flow is: take a photo or pick an image, tap two corners to crop, type the axis endpoints, extract, then share the CSV. Processing stays on the device and uses the same Python package. Tick-label OCR is not in the APK. RapidOCR needs onnxruntime, and that index has no Android wheel for it. The fallback is typed endpoints on the detected plot box, not a guessed scale.

## Layout

See `ARCHITECTURE.md`, `BENCHMARK.md`, and `ROADMAP.md`.

## License

MIT. Copyright 2026 asdfgtrewq748.

---

# 曲线转 CSV

把科研图里的折线、散点和柱子转成 CSV、JSON 和一张 QA 叠加图。

**状态：** M1（线性坐标、外部刻度、合成基准）进行中。实测数字在跑完基准后写入 `benchmarks/results/`，本页不引用未验证的性能数字。

读不出来的位置留空并打标，主输出不插值。

## 安装与命令

```bash
pip install -e ".[dev,bench]"
python -m benchmarks.generator.cli --config benchmarks/configs/m1.yaml --split test --out data/synth-v0.1
python -m benchmarks.evaluate --config benchmarks/configs/m1.yaml --data data/synth-v0.1 --split test \
       --out benchmarks/results --tag M1
python -m benchmarks.report benchmarks/results/M1.json > benchmarks/results/M1.md
make bench-smoke
```

调试入口：`python -m curve2csv IMG --axes axes.json --out DIR`，或 `python -m curve2csv extract IMG -o DIR --xmin 0 --xmax 1 --ymin 0 --ymax 1`。没有刻度文件、也没有四个端点时退出码为 2。无参数时打开桌面窗口。`curve2csv --headless-smoke IMAGE -o DIR` 不打开窗口并打印 `SMOKE_OK`。Windows 可执行文件由 GitHub Actions 上传为 `curve2csv-windows-exe`。没有 macOS 应用。

Android 调试包在 `android/`，用 Chaquopy 17 和 Python 3.10 打包（OpenCV 的 Android 轮子只有 3.10 的 4.5.1.48）。`minSdk` 为 24。拍照或从相册选取、点两下裁剪、手填坐标端点、导出 CSV。设备上不带 OCR：Chaquopy 索引没有 onnxruntime 的 Android 轮子，所以不假装识别刻度文字，改由使用者填写端点。GitHub Actions 产物名为 `curve2csv-debug-apk`。

设计说明见 `ARCHITECTURE.md`、`BENCHMARK.md`、`ROADMAP.md`。许可证为 MIT。
