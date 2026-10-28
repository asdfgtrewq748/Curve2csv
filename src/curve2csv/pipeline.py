"""Run the digitizing stages and always return an :class:`ExtractionResult`."""

from __future__ import annotations

import time
from typing import cast

import numpy as np

from curve2csv.calibrate.manual import calibrate_manual
from curve2csv.calibrate.model import PlaneMap
from curve2csv.color_math import rgb2lab
from curve2csv.config import PipelineConfig
from curve2csv.detect.axes import detect_ticks
from curve2csv.detect.plot_area import detect_plot_area
from curve2csv.extract.bar import extract_bar
from curve2csv.extract.curve import classify_mask, extract_curve
from curve2csv.extract.scatter import extract_scatter
from curve2csv.quality.confidence import calibration_residual, plot_score_of, score_series
from curve2csv.quality.flags import assign_segment_ids, strip_interpolation
from curve2csv.separate.achromatic import (
    achromatic_text_exclusion,
    achromatic_width_hint,
    separate_achromatic_series,
)
from curve2csv.separate.color import lab_to_hex, separate_series
from curve2csv.separate.foreground import build_masks
from curve2csv.types import (
    SCHEMA_VERSION,
    Abstain,
    AxesOverride,
    AxisCalibration,
    ExtractionResult,
    LoadedImage,
    Masks,
    PlotArea,
    PointFlag,
    Series,
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


def _plane_from_calibration(
    calibration: dict[str, AxisCalibration | Abstain],
) -> PlaneMap | None:
    x_cal = calibration.get("x")
    y_cal = calibration.get("y")
    if isinstance(x_cal, AxisCalibration) and isinstance(y_cal, AxisCalibration):
        return PlaneMap(x=x_cal, y=y_cal)
    return None


def run_pipeline(
    loaded: LoadedImage,
    *,
    axes: AxesOverride | None = None,
    config: PipelineConfig | None = None,
    plot_area_override: PlotArea | None = None,
    calibration_override: dict[str, AxisCalibration | Abstain] | None = None,
) -> ExtractionResult:
    cfg = config or PipelineConfig()
    timings: dict[str, float] = {}
    abstentions: list[Abstain] = []

    t0 = time.perf_counter()
    # Spine detection is unchanged when it succeeds. Charts whose axes are
    # lighter than the ink threshold (Our World in Data grapher exports, for
    # example) fall through to tick-label positions. That path needs RapidOCR;
    # without it the result stays an abstain and typed endpoints still work.
    framed_axes: AxesOverride | None = None
    area: PlotArea | Abstain
    if plot_area_override is not None:
        area = plot_area_override
    else:
        area = detect_plot_area(loaded.rgb, cfg)
    timings["plot_area"] = (time.perf_counter() - t0) * 1000.0
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
    detected = [] if calibration_override is not None else detect_ticks(loaded.rgb, area, cfg)
    timings["ticks"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    plane = None
    if calibration_override is not None:
        calibration = calibration_override
        plane = _plane_from_calibration(calibration)
        abstentions.extend(value for value in calibration.values() if isinstance(value, Abstain))
    else:
        if axes is None and framed_axes is not None:
            axes = framed_axes
        elif axes is None:
            from curve2csv.ocr.read import read_axes, read_frame

            axes = read_axes(loaded.rgb, area, cfg)
            # A detected box that does not line up with the labels (a footer rule
            # or a short interior line) is replaced by the label frame. Callers
            # that pass axes or a confirmed box never reach this.
            if axes is None and plot_area_override is None:
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
    separated = separate_series(loaded.rgb, masks, cfg)
    achromatic_fallback = False
    if not separated:
        separated = separate_achromatic_series(loaded.rgb, masks, area, cfg)
        achromatic_fallback = bool(separated)
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
    lab_image = rgb2lab(loaded.rgb)
    curve_masks = masks
    if achromatic_fallback:
        curve_masks = Masks(
            foreground=masks.foreground,
            text=achromatic_text_exclusion(masks.text, area.bbox),
            grid=masks.grid,
            legend=masks.legend,
            axes=masks.axes,
        )
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
                curve_masks,
                cfg,
                color_hex=color,
                other_mask=other,
                gray=gray,
                lab_image=lab_image,
                width_hint=(
                    achromatic_width_hint(mask.mask, area.bbox) if achromatic_fallback else None
                ),
            )
        if extracted.points:
            series.append(extracted)
    series = assign_segment_ids(strip_interpolation(series))

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
    bridged = 0
    for found in series:
        for point in found.points:
            if PointFlag.INTERPOLATED in point.flags and point.x is not None:
                bridged += 1
    diagnostics: dict[str, object] = {
        "timings_ms": {key: round(value, 3) for key, value in timings.items()},
        "n_detected_ticks": len(detected),
        "n_series_masks": len(separated),
        "achromatic_fallback": achromatic_fallback,
        "aligned": plane.is_axis_aligned(),
        "bridged_count": bridged,
        "plot_area_source": area.source,
    }
    result = ExtractionResult(
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
    diagnostics["calibration_id"] = result.calibration_id
    return result


def np_median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])
