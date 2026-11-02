"""CSV columns, empty abstentions, and JSON schema."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import jsonschema
import numpy as np
from tests.helpers import line_figure

from curve2csv.api import extract
from curve2csv.io.export import CSV_COLUMNS, write_csv
from curve2csv.types import Abstain, DataPoint, ExtractionResult, LoadedImage, PointFlag, Series


def test_export_columns_schema_and_blank_abstain(tmp_path: Path) -> None:
    x = np.linspace(0.0, 4.0, 80)
    image, axes = line_figure(x, [(np.sin(x), "#d62728")])
    result = extract(image, axes=axes, out=tmp_path)
    csv_path = tmp_path / "extraction.csv"
    with csv_path.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == CSV_COLUMNS
    blank = ExtractionResult(
        schema_version="1.0",
        source=LoadedImage(rgb=np.zeros((8, 8, 3), dtype=np.uint8), source="memory", sha256="0"),
        plot_area=Abstain("plot_area", "no_axis_found"),
        calibration={},
        series=[
            Series(
                series_id="s0",
                kind="line",
                label=None,
                color_hex="#d62728",
                points=[DataPoint(None, None, 1.5, 2.5, 0.1, PointFlag.LOW_CONFIDENCE)],
                gaps=[],
                coverage=0.0,
                confidence=0.1,
            )
        ],
        image_confidence=0.0,
        abstentions=[],
        config_hash="test",
    )
    blank_path = tmp_path / "blank.csv"
    write_csv(blank, blank_path)
    with blank_path.open(encoding="utf-8") as handle:
        blank_rows = list(csv.reader(handle))
    assert blank_rows[1][3] == "" and blank_rows[1][4] == ""
    # Force one abstained point through the writer by checking the schema on the real file,
    # then blank a copy's numeric fields are already covered when confidence drops.
    document = json.loads((tmp_path / "extraction.json").read_text(encoding="utf-8"))
    schema_path = (
        Path(__import__("curve2csv").__file__).resolve().parent / "schema" / "result.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(document, schema)
    assert (tmp_path / "extraction.overlay.png").stat().st_size > 0
    assert result.series
