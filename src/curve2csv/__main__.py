"""Minimal debug entry: ``python -m curve2csv IMG --axes axes.json --out DIR``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from curve2csv.api import extract, extract_with_limits
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


def _run_extract(
    image: Path,
    out: Path,
    axes_path: Path | None,
    limits: dict[str, float] | None,
    x_log: bool,
    y_log: bool,
) -> int:
    try:
        if axes_path is not None:
            result = extract(image, axes=_load_axes(axes_path), out=out)
        elif limits is not None:
            result = extract_with_limits(
                image,
                xmin=limits["xmin"],
                xmax=limits["xmax"],
                ymin=limits["ymin"],
                ymax=limits["ymax"],
                x_scale=AxisScale.LOG10 if x_log else AxisScale.LINEAR,
                y_scale=AxisScale.LOG10 if y_log else AxisScale.LINEAR,
                out=out,
            )
        else:
            raise InputError("pass --axes or all of --xmin --xmax --ymin --ymax")
    except InputError as exc:
        logging.error("%s", exc)
        return 2
    logging.info("series=%d confidence=%.3f", len(result.series), result.image_confidence)
    return 0


def _legacy(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="curve2csv", description="Digitize a chart image.")
    parser.add_argument("image", type=Path)
    parser.add_argument("--axes", type=Path, required=True, help="JSON tick pairs (px, py, value)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.v else logging.WARNING, format="%(levelname)s %(message)s"
    )
    return _run_extract(args.image, args.out, args.axes, None, False, False)


def _extract_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="curve2csv extract",
        description="Digitize one figure into CSV, JSON, and a QA overlay.",
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--axes", type=Path, help="JSON tick pairs (px, py, value)")
    parser.add_argument("--xmin", type=float)
    parser.add_argument("--xmax", type=float)
    parser.add_argument("--ymin", type=float)
    parser.add_argument("--ymax", type=float)
    parser.add_argument("--x-log", action="store_true")
    parser.add_argument("--y-log", action="store_true")
    parser.add_argument("-v", action="count", default=0)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.v else logging.WARNING, format="%(levelname)s %(message)s"
    )
    limits = None
    named = (args.xmin, args.xmax, args.ymin, args.ymax)
    if any(value is not None for value in named):
        if any(value is None for value in named):
            logging.error("axis limits need --xmin, --xmax, --ymin, and --ymax together")
            return 2
        assert args.xmin is not None and args.xmax is not None
        assert args.ymin is not None and args.ymax is not None
        limits = {"xmin": args.xmin, "xmax": args.xmax, "ymin": args.ymin, "ymax": args.ymax}
    if args.axes is None and limits is None:
        logging.error(
            "no axis source. Pass --axes, or --xmin/--xmax/--ymin/--ymax. "
            "Tick-label OCR is not bundled; labels are not read automatically."
        )
        return 2
    return _run_extract(args.image, args.out, args.axes, limits, args.x_log, args.y_log)


def _headless_smoke(argv: list[str]) -> int:
    """Run one extract without opening a window. Prints SMOKE_OK or SMOKE_FAIL."""

    parser = argparse.ArgumentParser(prog="curve2csv --headless-smoke")
    parser.add_argument("image", type=Path)
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--xmin", type=float, default=0.0)
    parser.add_argument("--xmax", type=float, default=3.0)
    parser.add_argument("--ymin", type=float, default=-1.2)
    parser.add_argument("--ymax", type=float, default=1.2)
    args = parser.parse_args(argv)
    code = _run_extract(
        args.image,
        args.out,
        None,
        {"xmin": args.xmin, "xmax": args.xmax, "ymin": args.ymin, "ymax": args.ymax},
        False,
        False,
    )
    csv_path = args.out / f"{args.image.stem}.csv"
    overlay = args.out / f"{args.image.stem}.overlay.png"
    if code != 0 or not csv_path.is_file() or csv_path.stat().st_size == 0 or not overlay.is_file():
        print("SMOKE_FAIL")
        return 1 if code == 0 else code
    print("SMOKE_OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--headless-smoke":
        return _headless_smoke(args[1:])
    if args and args[0] == "extract":
        return _extract_command(args[1:])
    if not args or args[0] == "gui":
        from curve2csv.gui import run_gui

        return run_gui()
    return _legacy(args)


if __name__ == "__main__":
    sys.exit(main())
