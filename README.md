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

Debug one figure with caller-supplied ticks:

```bash
python -m curve2csv IMG --axes axes.json --out DIR
```

`axes.json` is `{"x": {"ticks": [{"px", "py", "value"}]}, "y": {...}}`.

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

调试入口：`python -m curve2csv IMG --axes axes.json --out DIR`。

设计说明见 `ARCHITECTURE.md`、`BENCHMARK.md`、`ROADMAP.md`。许可证为 MIT。
