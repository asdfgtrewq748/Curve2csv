"""Download a frozen Our World in Data line and scatter set with published CSV truth.

The raster is the grapher PNG. Ground truth is the CSV restricted to the
entities the chart displays. Axis range and linear/log come from the SVG
tick text, not from OCR. Images are CC BY 4.0 and are stored in the repo.
The dev / held-out split is ``sha256(slug) % 5 < 2`` and is written before
any extraction score exists.

Run from the repository root::

    python -m benchmarks.real.fetch --target 110
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import random
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from curve2csv.ocr.parse import choose_axis

ROOT = Path(__file__).resolve().parents[2]
REAL = Path(__file__).resolve().parent
SITEMAP = "https://ourworldindata.org/sitemap.xml"
UA = (
    "Mozilla/5.0 (compatible; curve2csv-benchmark/0.1; "
    "+https://github.com/asdfgtrewq748/Curve2csv)"
)
LICENSE = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
SEED = 20261025
_ID_COLUMNS = {"entity", "code", "year"}
# The grapher PNG is the first chart tab. Area and bar charts are not curves.
_LINE_TYPES = {"LineChart", "ScatterPlot"}
# Matches PipelineConfig.max_series. A catalog sample of 120 grapher configs
# put only about a third of charts in the 1–3 entity band, which would finish
# short of 100 figures. 1–6 is the inclusion rule, chosen before scoring.
_MAX_ENTITIES = 6


def is_line_figure(config: dict[str, Any], svg: str) -> bool:
    """True for a line or scatter grapher, decided from the published files.

    Stacked areas and bars are rejected from the SVG class or the first
    ``chartTypes`` entry. The decision does not look at an extraction score.
    """

    types = config.get("chartTypes")
    if isinstance(types, list) and types and types[0] not in _LINE_TYPES:
        return False
    if re.search(r'class="[^"]*\b(?:Areas|Bars)\b', svg):
        return False
    return True


def is_dev(slug: str) -> bool:
    """Frozen split. Dev is two of five hash buckets; the rest is held-out."""

    digest = int(hashlib.sha256(slug.encode("utf-8")).hexdigest(), 16)
    return digest % 5 < 2


def _get(url: str, attempts: int = 2) -> bytes:
    delay = 0.4
    last: Exception | None = None
    for _ in range(attempts):
        request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in {403, 429, 500, 502, 503, 504}:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"failed to fetch {url}: {last}")


def _slugs() -> list[str]:
    raw = _get(SITEMAP).decode("utf-8", errors="replace")
    found = re.findall(r"https://ourworldindata.org/grapher/([^<\s\"']+)", raw)
    slugs = []
    seen: set[str] = set()
    for slug in found:
        if "/" in slug or "?" in slug or slug.endswith((".png", ".csv", ".svg", ".json")):
            continue
        if slug not in seen:
            seen.add(slug)
            slugs.append(slug)
    return slugs


def _svg_labels(svg: str) -> tuple[list[tuple[float, str]], list[tuple[float, str]], float]:
    view = re.search(
        r'viewBox="\s*([+-eE\d.]+)\s+([+-eE\d.]+)\s+([+-eE\d.]+)\s+([+-eE\d.]+)"',
        svg,
    )
    width = float(view.group(3)) if view is not None else 850.0
    height = float(view.group(4)) if view is not None else 600.0
    texts: list[tuple[float, float, str]] = []
    for match in re.finditer(r"<text([^>]*)>(.*?)</text>", svg, flags=re.DOTALL):
        attrs, body = match.group(1), match.group(2)
        body = html.unescape(re.sub(r"<[^>]+>", "", body)).strip()
        if not body:
            continue
        x_match = re.search(r'\bx="([+-eE\d.]+)"', attrs)
        y_match = re.search(r'\by="([+-eE\d.]+)"', attrs)
        if x_match is None or y_match is None:
            continue
        texts.append((float(x_match.group(1)), float(y_match.group(1)), body))

    def _rows() -> list[tuple[float, str]] | None:
        ordered = sorted(texts, key=lambda item: item[1])
        groups: list[list[tuple[float, float, str]]] = []
        for item in ordered:
            if groups and abs(item[1] - groups[-1][-1][1]) <= 8.0:
                groups[-1].append(item)
            else:
                groups.append([item])
        best: list[tuple[float, float, str]] | None = None
        best_key: tuple[int, float] | None = None
        for group in groups:
            xs = [item[0] for item in group]
            if len(group) < 2 or max(xs) - min(xs) < 0.18 * width:
                continue
            key = (len(group), float(np.median([item[1] for item in group])))
            if best_key is None or key > best_key:
                best_key = key
                best = group
        if best is None:
            return None
        return [(item[0], item[2]) for item in best]

    def _cols(skip: set[str]) -> list[tuple[float, str]] | None:
        kept = [item for item in texts if item[2] not in skip]
        ordered = sorted(kept, key=lambda item: item[0])
        groups: list[list[tuple[float, float, str]]] = []
        for item in ordered:
            if groups and abs(item[0] - groups[-1][-1][0]) <= 12.0:
                groups[-1].append(item)
            else:
                groups.append([item])
        best: list[tuple[float, float, str]] | None = None
        best_key: tuple[int, float] | None = None
        for group in groups:
            ys = [item[1] for item in group]
            if len(group) < 2 or max(ys) - min(ys) < 0.15 * height:
                continue
            key = (len(group), -float(np.median([item[0] for item in group])))
            if best_key is None or key > best_key:
                best_key = key
                best = group
        if best is None:
            return None
        return [(item[1], item[2]) for item in best]

    x_labels = _rows()
    if x_labels is None:
        return [], [], width
    skip = {text for _pos, text in x_labels}
    y_labels = _cols(skip) or []
    return x_labels, y_labels, width


def _axis_frame(svg: str) -> dict[str, Any] | None:
    x_labels, y_labels, view_w = _svg_labels(svg)
    x_choice = choose_axis(x_labels, vertical=False)
    y_choice = choose_axis(y_labels, vertical=True)
    if x_choice is None or y_choice is None:
        return None
    x_pairs, x_scale = x_choice
    y_pairs, y_scale = y_choice
    xs = [pos for pos, _value in x_pairs]
    plot_w = float(max(xs) - min(xs))
    if plot_w < 30.0 or view_w <= 0:
        return None
    return {
        "x_scale": x_scale.value,
        "y_scale": y_scale.value,
        "x_range": [float(min(v for _p, v in x_pairs)), float(max(v for _p, v in x_pairs))],
        "y_range": [float(min(v for _p, v in y_pairs)), float(max(v for _p, v in y_pairs))],
        "plot_w_viewbox": plot_w,
        "viewbox_w": float(view_w),
    }


def _inside(value: float, lo: float, hi: float, scale: str) -> bool:
    if scale == "log10":
        if value <= 0 or lo <= 0 or hi <= 0:
            return False
        value, lo, hi = np.log10(value), np.log10(lo), np.log10(hi)
    span = abs(hi - lo)
    pad = 0.02 * span if span > 0 else 0.0
    return min(lo, hi) - pad <= value <= max(lo, hi) + pad


def _series_from_csv(
    payload: bytes,
    entities: list[str],
    frame: dict[str, Any],
) -> tuple[dict[str, list[list[float]]], str] | str:
    text = payload.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return "empty_csv"
    fields = list(rows[0].keys())
    year_name = next((name for name in fields if name.lower() == "year"), None)
    entity_name = next((name for name in fields if name.lower() == "entity"), None)
    if year_name is None or entity_name is None:
        return "no_year_entity"
    value_names = [
        name
        for name in fields
        if name.lower() not in _ID_COLUMNS and not name.lower().endswith("(annotations)")
    ]
    wanted = set(entities)
    populated = []
    for name in value_names:
        if any(row.get(entity_name) in wanted and (row.get(name) or "").strip() for row in rows):
            populated.append(name)
    if len(populated) != 1:
        return "multi_or_empty_value"
    value_name = populated[0]
    x_lo, x_hi = frame["x_range"]
    y_lo, y_hi = frame["y_range"]
    grouped: dict[str, list[list[float]]] = {name: [] for name in entities}
    outside = {name: 0 for name in entities}
    seen = {name: 0 for name in entities}
    for row in rows:
        entity = row.get(entity_name) or ""
        if entity not in wanted:
            continue
        try:
            year = float(row[year_name])
            raw = (row.get(value_name) or "").strip()
            if raw == "":
                continue
            value = float(raw)
        except ValueError:
            continue
        if not np.isfinite(year) or not np.isfinite(value):
            continue
        if not _inside(year, x_lo, x_hi, frame["x_scale"]):
            continue
        seen[entity] += 1
        if not _inside(value, y_lo, y_hi, frame["y_scale"]):
            outside[entity] += 1
            continue
        grouped[entity].append([year, value])
    for name in entities:
        if seen[name] < 10 or len(grouped[name]) < 10:
            return "too_few_points"
        if outside[name] > 0.2 * seen[name]:
            return "values_outside_axis"
        grouped[name].sort(key=lambda pair: pair[0])
    return grouped, value_name


def _consider(slug: str) -> tuple[str, dict[str, Any] | None, bytes | None]:
    base = f"https://ourworldindata.org/grapher/{slug}"
    try:
        config = json.loads(_get(base + ".config.json"))
    except Exception as exc:  # noqa: BLE001 - a skipped chart is a recorded reason
        return f"config:{type(exc).__name__}", None, None
    if not isinstance(config, dict):
        return "config_shape", None, None
    entities = config.get("selectedEntityNames") or []
    if not isinstance(entities, list) or not 1 <= len(entities) <= _MAX_ENTITIES:
        return "entity_count", None, None
    if any(not isinstance(name, str) or not name for name in entities):
        return "entity_count", None, None
    # The PNG is the large object. Download it only after the SVG and CSV
    # have already qualified the chart, so rejected slugs stay cheap.
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            csv_fut = pool.submit(_get, base + ".csv")
            svg_fut = pool.submit(_get, base + ".svg")
            csv_bytes = csv_fut.result()
            svg_bytes = svg_fut.result()
    except Exception as exc:  # noqa: BLE001
        return f"download:{type(exc).__name__}", None, None
    svg = svg_bytes.decode("utf-8", errors="replace")
    if not is_line_figure(config, svg):
        return "not_line_chart", None, None
    frame = _axis_frame(svg)
    if frame is None:
        return "no_svg_axes", None, None
    series = _series_from_csv(csv_bytes, list(entities), frame)
    if isinstance(series, str):
        return series, None, None
    grouped, value_name = series
    try:
        png_bytes = _get(base + ".png")
        image = Image.open(io.BytesIO(png_bytes))
        png_w, png_h = image.size
    except Exception as exc:  # noqa: BLE001
        return f"download:{type(exc).__name__}", None, None
    if png_w < 200 or png_h < 150:
        return "bad_png", None, None
    plot_w = frame["plot_w_viewbox"] * (png_w / frame["viewbox_w"])
    document = {
        "slug": slug,
        "split": "dev" if is_dev(slug) else "held-out",
        "title": config.get("title") or slug,
        "source_url": base,
        "csv_url": base + ".csv",
        "svg_url": base + ".svg",
        "png_url": base + ".png",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "attribution": "Our World in Data",
        "entities": list(entities),
        "y_column": value_name,
        "x_scale": frame["x_scale"],
        "y_scale": frame["y_scale"],
        "x_range": frame["x_range"],
        "y_range": frame["y_range"],
        "plot_w": plot_w,
        "png_size": [png_w, png_h],
        "series": grouped,
    }
    return "ok", document, png_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=110)
    args = parser.parse_args()
    slugs = _slugs()
    random.Random(SEED).shuffle(slugs)
    figures = REAL / "figures"
    ground = REAL / "gt"
    figures.mkdir(parents=True, exist_ok=True)
    ground.mkdir(parents=True, exist_ok=True)
    accepted: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}

    def _cached(slug: str) -> tuple[str, dict[str, Any], bytes] | None:
        png_path = figures / f"{slug}.png"
        gt_path = ground / f"{slug}.json"
        if not png_path.is_file() or not gt_path.is_file():
            return None
        document = json.loads(gt_path.read_text(encoding="utf-8"))
        entities = document.get("entities") or []
        if not isinstance(entities, list) or not 1 <= len(entities) <= _MAX_ENTITIES:
            return None
        return "ok", document, png_path.read_bytes()

    # Downloads in a batch overlap. Acceptance follows the shuffled sitemap
    # order, so the stored set does not depend on which request returned first.
    workers = 12
    cursor = 0
    while len(accepted) < args.target and cursor < len(slugs):
        batch = slugs[cursor : cursor + workers]
        cursor += len(batch)
        cached = {slug: hit for slug in batch if (hit := _cached(slug)) is not None}
        pending = [slug for slug in batch if slug not in cached]
        mapped = {}
        if pending:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                mapped = {slug: pool.submit(_consider, slug) for slug in pending}
        ordered: list[tuple[str, tuple[str, dict[str, Any] | None, bytes | None]]] = []
        for slug in batch:
            if slug in cached:
                ordered.append((slug, cached[slug]))
                continue
            try:
                ordered.append((slug, mapped[slug].result()))
            except Exception as exc:  # noqa: BLE001
                ordered.append((slug, (f"error:{type(exc).__name__}", None, None)))
        for slug, (reason, document, png) in ordered:
            reasons[reason] = reasons.get(reason, 0) + 1
            if document is None or png is None or len(accepted) >= args.target:
                continue
            (figures / f"{slug}.png").write_bytes(png)
            (ground / f"{slug}.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
            index = {key: value for key, value in document.items() if key != "series"}
            index["n_points"] = {name: len(points) for name, points in document["series"].items()}
            accepted.append(index)
            print(f"accept {len(accepted):3d} {index['split']:8s} {slug}", flush=True)
        if cursor % 48 == 0:
            top = sorted(reasons.items(), key=lambda item: -item[1])[:6]
            print(f"scanned {cursor} accept {len(accepted)} {top}", flush=True)
    manifest = {
        "dataset": "owid-grapher-v1",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "attribution": "Our World in Data",
        "seed": SEED,
        "split_rule": "dev if int(sha256(slug).hexdigest(), 16) % 5 < 2 else held-out",
        "accuracy": (
            "A figure is correct when the number of predicted series that still "
            "have an unflagged finite point equals the number of ground-truth "
            "series, and every Hungarian match has NRMSE <= 2% of the axis "
            "range and x-coverage >= 0.90. Flagged or null points are removed "
            "before scoring."
        ),
        "n_figures": len(accepted),
        "n_dev": sum(1 for item in accepted if item["split"] == "dev"),
        "n_held_out": sum(1 for item in accepted if item["split"] == "held-out"),
        "reject_counts": reasons,
        "figures": sorted(accepted, key=lambda item: item["slug"]),
    }
    (REAL / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"wrote {len(accepted)} figures "
        f"(dev {manifest['n_dev']}, held-out {manifest['n_held_out']}) "
        f"after scanning {cursor} slugs"
    )
    if len(accepted) < args.target:
        raise SystemExit(f"only {len(accepted)} figures passed the inclusion filter")


if __name__ == "__main__":
    main()
