"""Minimal debug entry: ``python -m curve2csv IMG --axes axes.json --out DIR``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from curve2csv.api import extract
from curve2csv.errors import InputError
from curve2csv.types import AxesOverride, AxisScale, TickInput


def _load_axes(path: Path) -> AxesOverride:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise InputError("axes file must be a JSON object")

    def _ticks(block: object) -> tuple[TickInput, ...]:
        if not isinstance(block, dict) or not isinstance(block.get("ticks"), list):
            raise InputError("axes file needs x.ticks and y.ticks")
        ticks: list[TickInput] = []
        for item in block["ticks"]:
            if not isinstance(item, dict) or "value" not in item or "px" not in item:
                raise InputError("each tick needs px and value")
            py = item.get("py")
            ticks.append(
                TickInput(
                    px=float(item["px"]),
                    value=float(item["value"]),
                    py=None if py is None else float(py),
                )
            )
        return tuple(ticks)

    def _scale(block: object) -> AxisScale:
        if isinstance(block, dict) and block.get("scale") == "log10":
            return AxisScale.LOG10
        return AxisScale.LINEAR

    return AxesOverride(
        x_ticks=_ticks(payload.get("x")),
        y_ticks=_ticks(payload.get("y")),
        x_scale=_scale(payload.get("x")),
        y_scale=_scale(payload.get("y")),
        source="manual",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="curve2csv", description="Digitize a chart image.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--axes", type=Path, required=True, help="JSON tick pairs (px, py, value)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.v else logging.WARNING, format="%(levelname)s %(message)s"
    )
    try:
        axes = _load_axes(args.axes)
        result = extract(args.image, axes=axes, out=args.out)
    except InputError as exc:
        logging.error("%s", exc)
        return 2
    logging.info("series=%d confidence=%.3f", len(result.series), result.image_confidence)
    return 0


if __name__ == "__main__":
    sys.exit(main())
