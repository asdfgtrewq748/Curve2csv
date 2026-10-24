"""Pipeline thresholds. Every field has a default and participates in ``config_hash``."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PipelineConfig:
    max_calib_residual: float = 0.02
    min_point_confidence: float = 0.3
    ink_threshold: int = 185
    min_line_frac: float = 0.22
    chroma_min: float = 12.0
    ambiguous_delta_e: float = 5.0
    min_series_delta_e: float = 8.0
    max_series: int = 6
    min_cluster_pixels: int = 40
    assign_delta_e: float = 28.0
    thick_factor: float = 8.0
    inset_px: int = 1
    legend_max_area_frac: float = 0.4
    scatter_min_distance: float = 4.0
    scatter_min_pixels: int = 4
    edge_band_px: int = 3
    kmeans_seed: int = 0

    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
