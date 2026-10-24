.PHONY: install lint test bench-smoke bench-test update-baseline

PY ?= python
CONFIG ?= benchmarks/configs/m1.yaml
DATA ?= data/synth-v0.1

install:
	$(PY) -m pip install -e ".[dev,bench]"

lint:
	ruff check src tests benchmarks
	ruff format --check src tests benchmarks
	mypy --strict src/curve2csv

test:
	pytest --cov=curve2csv --cov-fail-under=80

bench-smoke:
	$(PY) -m benchmarks.generator.cli --config $(CONFIG) --split smoke --out $(DATA)
	$(PY) -m benchmarks.evaluate --config $(CONFIG) --data $(DATA) --split smoke --out benchmarks/results --tag smoke --baseline benchmarks/baseline/smoke.json

bench-test:
	$(PY) -m benchmarks.generator.cli --config $(CONFIG) --split test --out $(DATA)
	$(PY) -m benchmarks.evaluate --config $(CONFIG) --data $(DATA) --split test --out benchmarks/results --tag M1
	$(PY) -m benchmarks.report benchmarks/results/M1.json > benchmarks/results/M1.md

update-baseline:
	$(PY) -m benchmarks.generator.cli --config $(CONFIG) --split smoke --out $(DATA)
	$(PY) -m benchmarks.evaluate --config $(CONFIG) --data $(DATA) --split smoke --out benchmarks/results --tag smoke --write-baseline benchmarks/baseline/smoke.json
