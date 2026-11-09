"""Web Canvas interactive UI: local HTTP server with original-pixel canvas editing."""

from __future__ import annotations

import argparse
import json
import tempfile
import urllib.parse
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import cv2

from curve2csv.api import (
    clear_range,
    confirm_plot_box,
    extract,
    extract_with_limits,
    pick_series,
    trace_stroke,
)
from curve2csv.errors import InputError
from curve2csv.io.export import export_all
from curve2csv.io.image import load_image
from curve2csv.types import (
    Abstain,
    AxisCalibration,
    AxisScale,
    ExtractionResult,
    PlotArea,
)


class WebSession:
    """State manager for interactive web sessions."""

    def __init__(self, work_dir: Path | None = None) -> None:
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="curve2csv_web_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.image_path: Path | None = None
        self.current_result: ExtractionResult | None = None
        self.history: list[ExtractionResult] = []

    def _push_history(self) -> None:
        if self.current_result is not None:
            self.history.append(self.current_result)
            if len(self.history) > 30:
                self.history.pop(0)

    def undo(self) -> dict[str, Any]:
        if not self.history:
            raise InputError("Nothing to undo")
        self.current_result = self.history.pop()
        if self.image_path is not None:
            export_all(self.current_result, self.work_dir / "export", stem="current")
        return self.summary()

    def load(self, data: bytes, filename: str, page: int = 1) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower() or ".png"
        raw_path = self.work_dir / f"uploaded{suffix}"
        raw_path.write_bytes(data)
        loaded = load_image(raw_path, page=page)
        self.image_path = self.work_dir / "figure.png"
        ok = cv2.imwrite(str(self.image_path), cv2.cvtColor(loaded.rgb, cv2.COLOR_RGB2BGR))
        if not ok:
            raise InputError("Could not cache image")

        # Initial automatic extraction
        export_dir = self.work_dir / "export"
        try:
            res = extract(self.image_path, out=export_dir)
        except InputError:
            res = ExtractionResult(
                schema_version="1.0",
                source=loaded,
                plot_area=Abstain("plot_area", "not_detected"),
                calibration={
                    "x": Abstain("calibrate", "not_calibrated"),
                    "y": Abstain("calibrate", "not_calibrated"),
                },
                series=[],
                image_confidence=0.0,
                abstentions=[],
            )
        self.history.clear()
        self.current_result = res
        export_all(self.current_result, export_dir, stem="current")
        return self.summary()

    def extract_with_limits_cmd(
        self,
        *,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        x_log: bool = False,
        y_log: bool = False,
        plot_box: tuple[int, int, int, int] | None = None,
    ) -> dict[str, Any]:
        if self.image_path is None:
            raise InputError("No image loaded")
        self._push_history()
        export_dir = self.work_dir / "export"
        res = extract_with_limits(
            self.image_path,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            x_scale=AxisScale.LOG10 if x_log else AxisScale.LINEAR,
            y_scale=AxisScale.LOG10 if y_log else AxisScale.LINEAR,
            plot_box=plot_box,
            out=export_dir,
        )
        self.current_result = res
        return self.summary()

    def confirm_box(self, bbox: tuple[int, int, int, int]) -> dict[str, Any]:
        if self.current_result is None:
            raise InputError("No extraction result")
        self._push_history()
        export_dir = self.work_dir / "export"
        res = confirm_plot_box(self.current_result, bbox, out=export_dir)
        self.current_result = res
        return self.summary()

    def pick(self, stroke: list[tuple[float, float]], radius: float = 8.0) -> dict[str, Any]:
        if self.current_result is None:
            raise InputError("No extraction result")
        self._push_history()
        export_dir = self.work_dir / "export"
        res = pick_series(self.current_result, stroke, radius=radius, out=export_dir)
        self.current_result = res
        return self.summary()

    def trace(
        self,
        stroke: list[tuple[float, float]],
        series_id: str | None = None,
        radius: float = 10.0,
        bridge: bool = False,
    ) -> dict[str, Any]:
        if self.current_result is None:
            raise InputError("No extraction result")
        self._push_history()
        export_dir = self.work_dir / "export"
        res = trace_stroke(
            self.current_result,
            stroke,
            series_id=series_id,
            radius=radius,
            bridge=bridge,
            out=export_dir,
        )
        self.current_result = res
        return self.summary()

    def clear(self, x_min: float, x_max: float, series_id: str | None = None) -> dict[str, Any]:
        if self.current_result is None:
            raise InputError("No extraction result")
        self._push_history()
        export_dir = self.work_dir / "export"
        res = clear_range(self.current_result, x_min, x_max, series_id=series_id, out=export_dir)
        self.current_result = res
        return self.summary()

    def rename_series(self, series_id: str, label: str) -> dict[str, Any]:
        if self.current_result is None:
            raise InputError("No extraction result")
        self._push_history()
        new_series = []
        found = False
        for s in self.current_result.series:
            if s.series_id == series_id:
                new_series.append(replace(s, label=label))
                found = True
            else:
                new_series.append(s)
        if not found:
            raise InputError(f"No series with id {series_id}")
        export_dir = self.work_dir / "export"
        res = replace(self.current_result, series=new_series)
        export_all(res, export_dir, stem="current")
        self.current_result = res
        return self.summary()

    def summary(self) -> dict[str, Any]:
        if self.current_result is None:
            return {"loaded": False}
        res = self.current_result
        area = res.plot_area if isinstance(res.plot_area, PlotArea) else None
        x_cal = res.calibration.get("x")
        y_cal = res.calibration.get("y")
        series_summary = []
        for s in res.series:
            pts_count = sum(1 for p in s.points if p.x is not None and p.y is not None)
            series_summary.append(
                {
                    "series_id": s.series_id,
                    "label": s.label or "",
                    "kind": s.kind,
                    "color_hex": s.color_hex or "#1f77b4",
                    "coverage": float(s.coverage),
                    "confidence": float(s.confidence),
                    "points_count": pts_count,
                    "gaps": [[float(lo), float(hi)] for lo, hi in s.gaps],
                }
            )

        limits: dict[str, Any] = {}
        if area is not None and res.mapper is not None:
            x0, y0, x1, y1 = area.bbox
            p_bl = res.pixel_to_data(float(x0), float(y1))
            p_br = res.pixel_to_data(float(x1), float(y1))
            p_tl = res.pixel_to_data(float(x0), float(y0))
            if p_bl is not None and p_br is not None and p_tl is not None:
                limits = {
                    "xmin": p_bl[0],
                    "xmax": p_br[0],
                    "ymin": p_bl[1],
                    "ymax": p_tl[1],
                    "x_log": getattr(x_cal, "scale", None) == AxisScale.LOG10,
                    "y_log": getattr(y_cal, "scale", None) == AxisScale.LOG10,
                }

        return {
            "loaded": True,
            "width": res.source.width,
            "height": res.source.height,
            "plot_box": list(area.bbox) if area else None,
            "calibrated": all(
                isinstance(res.calibration.get(k), AxisCalibration) for k in ("x", "y")
            ),
            "limits": limits,
            "series": series_summary,
            "can_undo": len(self.history) > 0,
            "confidence": float(res.image_confidence),
        }


_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Curve2csv Web Interactive</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; height: 100vh; overflow: hidden; background: #1a1a1a; color: #eee; }
  #sidebar { width: 340px; background: #242424; border-right: 1px solid #333; display: flex; flex-direction: column; padding: 12px; gap: 10px; overflow-y: auto; }
  #main { flex: 1; display: flex; flex-direction: column; }
  #toolbar { height: 48px; background: #2a2a2a; border-bottom: 1px solid #333; display: flex; align-items: center; padding: 0 12px; gap: 8px; }
  #canvas-container { flex: 1; position: relative; overflow: hidden; background: #111; cursor: crosshair; }
  canvas { position: absolute; left: 0; top: 0; }
  button { background: #383838; color: #fff; border: 1px solid #555; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; }
  button:hover { background: #4a4a4a; }
  button.active { background: #1976d2; border-color: #2196f3; font-weight: bold; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  input[type="text"], input[type="number"] { background: #333; border: 1px solid #555; color: #fff; padding: 4px 6px; border-radius: 3px; font-size: 12px; }
  label { font-size: 12px; color: #aaa; }
  .card { background: #2d2d2d; border-radius: 6px; padding: 10px; border: 1px solid #3d3d3d; }
  .card-title { font-size: 13px; font-weight: bold; margin-bottom: 8px; color: #90caf9; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 4px; text-align: left; border-bottom: 1px solid #3d3d3d; }
  th { color: #888; }
  #status-bar { height: 26px; background: #202020; border-top: 1px solid #333; display: flex; align-items: center; padding: 0 12px; font-size: 11px; color: #888; }
</style>
</head>
<body>

<div id="sidebar">
  <div class="card">
    <div class="card-title">1. Load Figure</div>
    <input type="file" id="file-input" style="font-size:12px; width:100%;">
  </div>

  <div class="card">
    <div class="card-title">2. Axis Limits</div>
    <div class="grid-2">
      <div><label>xmin</label><input type="text" id="xmin" style="width:100%;"></div>
      <div><label>xmax</label><input type="text" id="xmax" style="width:100%;"></div>
      <div><label>ymin</label><input type="text" id="ymin" style="width:100%;"></div>
      <div><label>ymax</label><input type="text" id="ymax" style="width:100%;"></div>
    </div>
    <div style="margin-top:6px; display:flex; gap:10px; font-size:12px;">
      <label><input type="checkbox" id="x-log"> x log10</label>
      <label><input type="checkbox" id="y-log"> y log10</label>
    </div>
    <button id="btn-apply-limits" style="width:100%; margin-top:8px;">Set Limits</button>
  </div>

  <div class="card">
    <div class="card-title">3. Trace Stroke (Add Ink)</div>
    <div style="font-size:11px; color:#aaa; margin-bottom:6px;">
      Click along missing/occluded curve. Real ink will snap automatically.
    </div>
    <div style="display:flex; gap:6px; align-items:center; margin-bottom:6px;">
      <label>Radius (px):</label>
      <input type="number" id="trace-radius" value="10" style="width:50px;">
      <label><input type="checkbox" id="trace-bridge"> Bridge</label>
    </div>
    <div style="display:flex; gap:6px;">
      <button id="btn-apply-trace" style="flex:1;">Apply Trace</button>
      <button id="btn-clear-trace" style="background:#552;">Clear</button>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Series Summary</div>
    <table id="series-table">
      <thead><tr><th>ID</th><th>Label</th><th>Pts</th><th>Cov</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="card" style="margin-top:auto;">
    <div class="card-title">Export</div>
    <div style="display:flex; gap:6px;">
      <button id="btn-dl-csv" style="flex:1;">CSV</button>
      <button id="btn-dl-json" style="flex:1;">JSON</button>
      <button id="btn-dl-overlay" style="flex:1;">Overlay</button>
    </div>
  </div>
</div>

<div id="main">
  <div id="toolbar">
    <button class="active" id="tool-trace" data-tool="trace">Trace Stroke</button>
    <button id="tool-box" data-tool="box">Confirm Box</button>
    <button id="tool-pick" data-tool="pick">Pick Series</button>
    <button id="tool-clear" data-tool="clear">Clear Range</button>
    <div style="width:1px; height:20px; background:#444; margin:0 4px;"></div>
    <button id="btn-undo" disabled>Undo</button>
    <div style="margin-left:auto; display:flex; gap:8px; align-items:center;">
      <label><input type="checkbox" id="show-overlay" checked> QA Overlay</label>
      <button id="btn-reset-view">Reset View</button>
    </div>
  </div>

  <div id="canvas-container">
    <canvas id="view-canvas"></canvas>
  </div>

  <div id="status-bar">
    <span id="status-text">Ready. Open an image to begin.</span>
    <span id="coords" style="margin-left:auto;"></span>
  </div>
</div>

<script>
let state = {
  tool: 'trace',
  loaded: false,
  width: 0,
  height: 0,
  scale: 1.0,
  panX: 0,
  panY: 0,
  isPanning: false,
  lastMouse: { x: 0, y: 0 },
  strokePoints: [],
  boxStart: null,
  clearStart: null,
  sourceImg: new Image(),
  overlayImg: new Image(),
};

const canvas = document.getElementById('view-canvas');
const ctx = canvas.getContext('2d');
const container = document.getElementById('canvas-container');

function resizeCanvas() {
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
  render();
}
window.addEventListener('resize', resizeCanvas);

function setStatus(text) {
  document.getElementById('status-text').textContent = text;
}

function screenToImage(sx, sy) {
  return {
    x: (sx - state.panX) / state.scale,
    y: (sy - state.panY) / state.scale
  };
}

function imageToScreen(ix, iy) {
  return {
    x: ix * state.scale + state.panX,
    y: iy * state.scale + state.panY
  };
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!state.loaded) return;

  ctx.save();
  ctx.translate(state.panX, state.panY);
  ctx.scale(state.scale, state.scale);

  const showOverlay = document.getElementById('show-overlay').checked;
  const img = showOverlay && state.overlayImg.complete && state.overlayImg.naturalWidth ? state.overlayImg : state.sourceImg;
  if (img.complete && img.naturalWidth) {
    ctx.drawImage(img, 0, 0);
  }

  // Draw in-progress stroke
  if (state.strokePoints.length > 0) {
    const radius = parseFloat(document.getElementById('trace-radius').value) || 10;
    ctx.strokeStyle = 'rgba(0, 255, 255, 0.8)';
    ctx.lineWidth = 2 / state.scale;
    ctx.beginPath();
    state.strokePoints.forEach((p, idx) => {
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    state.strokePoints.forEach(p => {
      ctx.fillStyle = 'cyan';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4 / state.scale, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = 'rgba(0, 255, 255, 0.25)';
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.stroke();
    });
  }

  // Draw in-progress box
  if (state.boxStart) {
    ctx.strokeStyle = '#ff9800';
    ctx.lineWidth = 1.5 / state.scale;
    ctx.strokeRect(state.boxStart.x, state.boxStart.y, state.lastImgX - state.boxStart.x, state.lastImgY - state.boxStart.y);
  }

  // Draw in-progress clear range
  if (state.clearStart) {
    ctx.fillStyle = 'rgba(255, 0, 0, 0.25)';
    ctx.fillRect(Math.min(state.clearStart.x, state.lastImgX), 0, Math.abs(state.lastImgX - state.clearStart.x), state.height);
  }

  ctx.restore();
}

container.addEventListener('wheel', e => {
  e.preventDefault();
  if (!state.loaded) return;
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
  const newScale = Math.max(0.05, Math.min(25, state.scale * zoomFactor));

  state.panX = mx - (mx - state.panX) * (newScale / state.scale);
  state.panY = my - (my - state.panY) * (newScale / state.scale);
  state.scale = newScale;
  render();
});

container.addEventListener('mousedown', e => {
  if (!state.loaded) return;
  if (e.button === 1 || e.button === 2 || e.shiftKey) {
    state.isPanning = true;
    state.lastMouse = { x: e.clientX, y: e.clientY };
    return;
  }
  const rect = canvas.getBoundingClientRect();
  const imgCoord = screenToImage(e.clientX - rect.left, e.clientY - rect.top);

  if (state.tool === 'trace') {
    state.strokePoints.push(imgCoord);
    render();
  } else if (state.tool === 'box') {
    if (!state.boxStart) {
      state.boxStart = imgCoord;
      setStatus('First corner set. Drag/click opposite corner.');
    } else {
      const x0 = Math.round(Math.min(state.boxStart.x, imgCoord.x));
      const x1 = Math.round(Math.max(state.boxStart.x, imgCoord.x));
      const y0 = Math.round(Math.min(state.boxStart.y, imgCoord.y));
      const y1 = Math.round(Math.max(state.boxStart.y, imgCoord.y));
      state.boxStart = null;
      apiPost('/api/confirm_box', { bbox: [x0, y0, x1, y1] });
    }
  } else if (state.tool === 'pick') {
    apiPost('/api/pick_series', { stroke: [[imgCoord.x, imgCoord.y]], radius: 8.0 });
  } else if (state.tool === 'clear') {
    if (!state.clearStart) {
      state.clearStart = imgCoord;
      setStatus('Click opposite x-boundary to clear.');
    } else {
      const lo = Math.min(state.clearStart.x, imgCoord.x);
      const hi = Math.max(state.clearStart.x, imgCoord.x);
      state.clearStart = null;
      apiPost('/api/clear_range_pixel', { x_min_px: lo, x_max_px: hi });
    }
  }
});

container.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const imgCoord = screenToImage(e.clientX - rect.left, e.clientY - rect.top);
  state.lastImgX = imgCoord.x;
  state.lastImgY = imgCoord.y;
  document.getElementById('coords').textContent = `${Math.round(imgCoord.x)}, ${Math.round(imgCoord.y)} px`;

  if (state.isPanning) {
    state.panX += e.clientX - state.lastMouse.x;
    state.panY += e.clientY - state.lastMouse.y;
    state.lastMouse = { x: e.clientX, y: e.clientY };
    render();
  } else if (state.boxStart || state.clearStart) {
    render();
  }
});

window.addEventListener('mouseup', e => {
  if (state.isPanning) state.isPanning = false;
});
container.addEventListener('contextmenu', e => e.preventDefault());

// Tool selection
document.querySelectorAll('#toolbar button[data-tool]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#toolbar button[data-tool]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.tool = btn.dataset.tool;
    state.boxStart = null;
    state.clearStart = null;
    render();
  });
});

document.getElementById('btn-reset-view').addEventListener('click', () => {
  if (!state.loaded) return;
  const padding = 20;
  const sX = (canvas.width - padding * 2) / state.width;
  const sY = (canvas.height - padding * 2) / state.height;
  state.scale = Math.min(sX, sY);
  state.panX = (canvas.width - state.width * state.scale) / 2;
  state.panY = (canvas.height - state.height * state.scale) / 2;
  render();
});

document.getElementById('show-overlay').addEventListener('change', render);

document.getElementById('btn-apply-trace').addEventListener('click', () => {
  if (state.strokePoints.length < 2) {
    alert('Click at least 2 points along the curve before applying.');
    return;
  }
  const radius = parseFloat(document.getElementById('trace-radius').value) || 10;
  const bridge = document.getElementById('trace-bridge').checked;
  apiPost('/api/trace_stroke', {
    stroke: state.strokePoints.map(p => [p.x, p.y]),
    radius: radius,
    bridge: bridge
  }).then(() => {
    state.strokePoints = [];
    render();
  });
});

document.getElementById('btn-clear-trace').addEventListener('click', () => {
  state.strokePoints = [];
  render();
});

document.getElementById('btn-apply-limits').addEventListener('click', () => {
  const xmin = parseFloat(document.getElementById('xmin').value);
  const xmax = parseFloat(document.getElementById('xmax').value);
  const ymin = parseFloat(document.getElementById('ymin').value);
  const ymax = parseFloat(document.getElementById('ymax').value);
  if ([xmin, xmax, ymin, ymax].some(isNaN)) {
    alert('Please enter valid numeric limits');
    return;
  }
  apiPost('/api/extract_limits', {
    xmin: xmin,
    xmax: xmax,
    ymin: ymin,
    ymax: ymax,
    x_log: document.getElementById('x-log').checked,
    y_log: document.getElementById('y-log').checked
  });
});

document.getElementById('btn-undo').addEventListener('click', () => {
  apiPost('/api/undo', {});
});

document.getElementById('btn-dl-csv').addEventListener('click', () => window.open('/api/export/csv'));
document.getElementById('btn-dl-json').addEventListener('click', () => window.open('/api/export/json'));
document.getElementById('btn-dl-overlay').addEventListener('click', () => window.open('/api/image/overlay.png'));

document.getElementById('file-input').addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  setStatus('Uploading & extracting...');
  fetch('/api/upload', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => handleSummary(data))
    .catch(err => setStatus('Upload failed: ' + err));
});

function apiPost(endpoint, body) {
  setStatus('Processing...');
  return fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      alert(data.error);
      setStatus('Error: ' + data.error);
    } else {
      handleSummary(data);
    }
  })
  .catch(err => setStatus('Network error: ' + err));
}

function handleSummary(data) {
  if (!data.loaded) return;
  state.loaded = true;
  state.width = data.width;
  state.height = data.height;
  document.getElementById('btn-undo').disabled = !data.can_undo;

  if (data.limits && data.limits.xmin !== undefined) {
    document.getElementById('xmin').value = data.limits.xmin.toFixed(4);
    document.getElementById('xmax').value = data.limits.xmax.toFixed(4);
    document.getElementById('ymin').value = data.limits.ymin.toFixed(4);
    document.getElementById('ymax').value = data.limits.ymax.toFixed(4);
    document.getElementById('x-log').checked = data.limits.x_log;
    document.getElementById('y-log').checked = data.limits.y_log;
  }

  // Update series table
  const tbody = document.querySelector('#series-table tbody');
  tbody.innerHTML = '';
  data.series.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td style="color:${s.color_hex}; font-weight:bold;">${s.series_id}</td>
                    <td>${s.label || '-'}</td>
                    <td>${s.points_count}</td>
                    <td>${(s.coverage * 100).toFixed(1)}%</td>`;
    tbody.appendChild(tr);
  });

  // Reload images
  const ts = Date.now();
  state.sourceImg.src = '/api/image/source.png?' + ts;
  state.overlayImg.src = '/api/image/overlay.png?' + ts;
  state.overlayImg.onload = () => {
    if (!state.panX && !state.panY && state.scale === 1.0) {
      document.getElementById('btn-reset-view').click();
    } else {
      render();
    }
    setStatus(`Updated. ${data.series.length} series extracted.`);
  };
}

resizeCanvas();
</script>
</body>
</html>
"""


class WebHandler(BaseHTTPRequestHandler):
    """HTTP request handler for curve2csv web UI."""

    session: WebSession

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_bytes(self, content: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_bytes(_HTML_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/api/summary":
            self._send_json(self.session.summary())
            return

        if path == "/api/image/source.png":
            if self.session.image_path and self.session.image_path.is_file():
                self._send_bytes(self.session.image_path.read_bytes(), "image/png")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        if path == "/api/image/overlay.png":
            overlay_file = self.session.work_dir / "export" / "current.overlay.png"
            if overlay_file.is_file():
                self._send_bytes(overlay_file.read_bytes(), "image/png")
            elif self.session.image_path and self.session.image_path.is_file():
                self._send_bytes(self.session.image_path.read_bytes(), "image/png")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        if path == "/api/export/csv":
            csv_file = self.session.work_dir / "export" / "current.csv"
            if csv_file.is_file():
                self._send_bytes(csv_file.read_bytes(), "text/csv; charset=utf-8")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        if path == "/api/export/json":
            json_file = self.session.work_dir / "export" / "current.json"
            if json_file.is_file():
                self._send_bytes(json_file.read_bytes(), "application/json; charset=utf-8")
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))

        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self._send_json({"error": "Expected multipart/form-data"}, status=400)
                return

            # Simple multipart parser
            body = self.rfile.read(length)
            boundary = content_type.split("boundary=")[-1].strip()
            parts = body.split(f"--{boundary}".encode())
            file_bytes = b""
            filename = "uploaded.png"
            for part in parts:
                if b'filename="' in part:
                    header, file_bytes = part.split(b"\r\n\r\n", 1)
                    file_bytes = file_bytes.rstrip(b"\r\n--")
                    header_str = header.decode("latin1")
                    if 'filename="' in header_str:
                        filename = header_str.split('filename="')[1].split('"')[0]
                    break

            if not file_bytes:
                self._send_json({"error": "No file received"}, status=400)
                return

            try:
                summary = self.session.load(file_bytes, filename)
                self._send_json(summary)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        body = self.rfile.read(length)
        payload: dict[str, Any] = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                self._send_json({"error": "Invalid JSON"}, status=400)
                return

        try:
            if path == "/api/extract_limits":
                res = self.session.extract_with_limits_cmd(
                    xmin=float(payload["xmin"]),
                    xmax=float(payload["xmax"]),
                    ymin=float(payload["ymin"]),
                    ymax=float(payload["ymax"]),
                    x_log=bool(payload.get("x_log", False)),
                    y_log=bool(payload.get("y_log", False)),
                )
                self._send_json(res)
                return

            if path == "/api/confirm_box":
                bbox = tuple(int(x) for x in payload["bbox"])
                if len(bbox) != 4:
                    raise InputError("bbox must have 4 integers")
                res = self.session.confirm_box(cast(tuple[int, int, int, int], bbox))
                self._send_json(res)
                return

            if path == "/api/pick_series":
                stroke = [(float(p[0]), float(p[1])) for p in payload["stroke"]]
                radius = float(payload.get("radius", 8.0))
                res = self.session.pick(stroke, radius=radius)
                self._send_json(res)
                return

            if path == "/api/trace_stroke":
                stroke = [(float(p[0]), float(p[1])) for p in payload["stroke"]]
                radius = float(payload.get("radius", 10.0))
                bridge = bool(payload.get("bridge", False))
                series_id = payload.get("series_id")
                res = self.session.trace(stroke, series_id=series_id, radius=radius, bridge=bridge)
                self._send_json(res)
                return

            if path == "/api/clear_range":
                lo = float(payload["x_min"])
                hi = float(payload["x_max"])
                series_id = payload.get("series_id")
                res = self.session.clear(lo, hi, series_id=series_id)
                self._send_json(res)
                return

            if path == "/api/clear_range_pixel":
                # Convert pixel bounds to data bounds using current mapper
                cur = self.session.current_result
                if cur is None or not cur.mapper:
                    raise InputError("Not calibrated")
                x0_px = float(payload["x_min_px"])
                x1_px = float(payload["x_max_px"])
                area = cur.plot_area if isinstance(cur.plot_area, PlotArea) else None
                y_mid = (area.bbox[1] + area.bbox[3]) / 2.0 if area else 0.0
                d0 = cur.pixel_to_data(x0_px, y_mid)
                d1 = cur.pixel_to_data(x1_px, y_mid)
                if d0 is None or d1 is None:
                    raise InputError("Coordinate mapping failed")
                res = self.session.clear(d0[0], d1[0])
                self._send_json(res)
                return

            if path == "/api/undo":
                res = self.session.undo()
                self._send_json(res)
                return

            self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=400)


def run_web(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="curve2csv web", description="Run interactive web interface"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Port to listen on (default 7860)")
    args = parser.parse_args(argv)

    session = WebSession()
    handler_class = type("BoundWebHandler", (WebHandler,), {"session": session})
    server = ThreadingHTTPServer((args.host, args.port), handler_class)
    print(f"Running curve2csv web UI on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server.")
        server.server_close()
    return 0
