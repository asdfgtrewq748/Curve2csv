"""Run the digitizing stages and always return an :class:`ExtractionResult`."""

from __future__ import annotations

import time
from typing import cast

import numpy as np

from curve2csv.calibrate.manual import calibrate_manual
from curve2csv.config import PipelineConfig
from curve2csv.detect.axes import detect_ticks
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.extract.bar import extract_bar
from curve2csv.extract.curve import classify_mask, extract_curve
from curve2csv.extract.scatter import extract_scatter
from curve2csv.quality.confidence import calibration_residual, plot_score_of, score_series
from curve2csv.quality.flags import strip_interpolation
from curve2csv.separate.color import lab_to_hex, separate_series
from curve2csv.separate.foreground import build_masks
from curve2csv.types import (
    SCHEMA_VERSION,
    Abstain,
    AxesOverride,
    AxisCalibration,
    ExtractionResult,
    LoadedImage,
    PlotArea,
    Series,
    SeriesMask,
)


def _empty(
    loaded: LoadedImage,
    *,
    area: PlotArea | Abstain,
    calibration: dict[str, AxisCalibration | Abstain],
    abstentions: list[Abstain],
    config: PipelineConfig,
    timings: dict[str, float],
) -> ExtractionResult:
    return ExtractionResult(
        schema_version=SCHEMA_VERSION,
        source=loaded,
        plot_area=area,
        calibration=calibration,
        series=[],
        image_confidence=0.0,
        abstentions=abstentions,
        diagnostics={"timings_ms": timings},
        config_hash=config.config_hash(),
    )


def run_pipeline(
    loaded: LoadedImage,
    *,
    axes: AxesOverride | None = None,
    config: PipelineConfig | None = None,
) -> ExtractionResult:
    cfg = config or PipelineConfig()
    timings: dict[str, float] = {}
    abstentions: list[Abstain] = []

    t0 = time.perf_counter()
    area = detect_plot_area(loaded.rgb, cfg)
    timings["plot_area"] = (time.perf_counter() - t0) * 1000.0
    # Spine detection is unchanged when it succeeds. Charts whose axes are
    # lighter than the ink threshold (Our World in Data grapher exports, for
    # example) fall through to tick-label positions. That path needs RapidOCR;
    # without it the result stays an abstain and typed endpoints still work.
    framed_axes: AxesOverride | None = None
    if isinstance(area, Abstain) and axes is None:
        from curve2csv.ocr.read import read_frame

        t0 = time.perf_counter()
        framed = read_frame(loaded.rgb, cfg)
        timings["ocr"] = (time.perf_counter() - t0) * 1000.0
        if framed is not None:
            area, framed_axes = framed
    if isinstance(area, Abstain):
        abstentions.append(area)
        calibration: dict[str, AxisCalibration | Abstain] = {
            "x": Abstain("calibrate", "no_plot_area"),
            "y": Abstain("calibrate", "no_plot_area"),
        }
        return _empty(
            loaded,
            area=area,
            calibration=calibration,
            abstentions=abstentions,
            config=cfg,
            timings=timings,
        )

    t0 = time.perf_counter()
    detected = detect_ticks(loaded.rgb, area, cfg)
    timings["ticks"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    plane = None
    if axes is None and framed_axes is not None:
        axes = framed_axes
    elif axes is None:
        from curve2csv.ocr.read import read_axes, read_frame

        axes = read_axes(loaded.rgb, area, cfg)
        # A detected box that does not line up with the labels (a footer rule
        # or a short interior line) is replaced by the label frame. Callers
        # that pass axes, including the synthetic benchmark, never reach this.
        if axes is None:
            framed = read_frame(loaded.rgb, cfg)
            if framed is not None:
                area, axes = framed
        timings["ocr"] = (time.perf_counter() - t0) * 1000.0
        t0 = time.perf_counter()
    if axes is None:
        calibration = {
            "x": Abstain("calibrate", "no_ticks"),
            "y": Abstain("calibrate", "no_ticks"),
        }
        abstentions.extend([cast(Abstain, calibration["x"]), cast(Abstain, calibration["y"])])
    else:
        calibration, plane = calibrate_manual(axes, cfg)
        for value in calibration.values():
            if isinstance(value, Abstain):
                abstentions.append(value)
    timings["calibrate"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    masks = build_masks(loaded.rgb, area, cfg)
    timings["masks"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    learned_masks: list[SeriesMask] | None = None
    if cfg.extractor == "learned":
        from curve2csv.separate.learned import segment_series

        learned_masks = segment_series(loaded.rgb, area.bbox, cfg)
    if learned_masks is None:
        separated = separate_series(loaded.rgb, masks, cfg)
        extractor_name = "rules"
    else:
        separated = learned_masks
        extractor_name = "learned"
    timings["separate"] = (time.perf_counter() - t0) * 1000.0

    if plane is None:
        abstentions.append(Abstain("extract", "no_calibration"))
        return _empty(
            loaded,
            area=area,
            calibration=calibration,
            abstentions=abstentions,
            config=cfg,
            timings=timings,
        )

    t0 = time.perf_counter()
    series: list[Series] = []
    separated_masks = [item.mask for item in separated]
    for index, mask in enumerate(separated):
        kind = classify_mask(mask.mask, area.bbox)
        color = lab_to_hex(mask.color_lab) if mask.color_lab is not None else None
        gray = loaded.rgb.mean(axis=2)
        if kind == "bar":
            extracted = extract_bar(mask, area, plane, cfg, color_hex=color, gray=gray)
        elif kind == "scatter":
            extracted = extract_scatter(mask, area, plane, cfg, color_hex=color, gray=gray)
        else:
            other: np.ndarray | None = None
            for other_index, other_mask in enumerate(separated_masks):
                if other_index == index:
                    continue
                other = (
                    np.array(other_mask, copy=True)
                    if other is None
                    else np.logical_or(other, other_mask)
                )
            extracted = extract_curve(
                mask,
                area,
                plane,
                masks,
                cfg,
                color_hex=color,
                other_mask=other,
                gray=gray,
                clean_components=extractor_name == "rules",
                allow_single_ridge_overlap=extractor_name == "learned",
            )
        if extracted.points:
            series.append(extracted)
    series = strip_interpolation(series)

    # Stable order: top-to-bottom, then left-to-right, using the median pixel.
    def _sort_key(item: Series) -> tuple[float, float]:
        pys = [p.py for p in item.points]
        pxs = [p.px for p in item.points]
        return (float(np_median(pys)), float(np_median(pxs)))

    series.sort(key=_sort_key)
    for index, found in enumerate(series):
        found.series_id = f"s{index}"
    timings["extract"] = (time.perf_counter() - t0) * 1000.0

    image_confidence = score_series(
        series, plot_score_of(area), calibration_residual(cast(dict[str, object], calibration))
    )
    diagnostics: dict[str, object] = {
        "timings_ms": {key: round(value, 3) for key, value in timings.items()},
        "n_detected_ticks": len(detected),
        "n_series_masks": len(separated),
        "aligned": plane.is_axis_aligned(),
        "extractor": extractor_name,
        "extractor_requested": cfg.extractor,
    }
    return ExtractionResult(
        schema_version=SCHEMA_VERSION,
        source=loaded,
        plot_area=area,
        calibration=calibration,
        series=series,
        image_confidence=image_confidence,
        abstentions=abstentions,
        diagnostics=diagnostics,
        mapper=plane,
        config_hash=cfg.config_hash(),
    )


def np_median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])
