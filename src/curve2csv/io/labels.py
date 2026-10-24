"""Manual series-label edits on an already written CSV and JSON pair."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from curve2csv.errors import InputError


def rename_series_label(csv_path: Path, json_path: Path, series_id: str, label: str) -> None:
    """Replace one series label. Does not change coordinates."""

    if any(char in label for char in ",\r\n"):
        raise InputError("a series label cannot contain a comma or a newline")
    rows = list(csv.reader(csv_path.read_text(encoding="utf-8").splitlines()))
    if not rows or rows[0][:2] != ["series_id", "series_label"]:
        raise InputError("CSV is missing series_id and series_label columns")
    found = False
    for row in rows[1:]:
        if row and row[0] == series_id:
            row[1] = label
            found = True
    if not found:
        raise InputError(f"no series with id {series_id}")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)
    document = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("series"), list):
        raise InputError("JSON is missing a series list")
    matched = False
    for series in document["series"]:
        if isinstance(series, dict) and series.get("series_id") == series_id:
            series["label"] = label
            matched = True
    if not matched:
        raise InputError(f"JSON has no series with id {series_id}")
    json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
