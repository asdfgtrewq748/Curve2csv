"""Unit and integration tests for the Web Canvas interactive session and HTTP server."""

from __future__ import annotations

import json
import socket
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np
from tests.helpers import line_figure

from curve2csv.web import WebHandler, WebSession


def _sample_png() -> bytes:
    x = np.linspace(0.0, 10.0, 240)
    image, _ = line_figure(x, [(0.4 * x, "#1f77b4")])
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".png", bgr)
    assert ok
    return bytes(buf)


def test_web_session_lifecycle(tmp_path: Path) -> None:
    session = WebSession(work_dir=tmp_path)
    assert not session.summary()["loaded"]

    png_bytes = _sample_png()
    summary = session.load(png_bytes, "test_fig.png")
    assert summary["loaded"]
    assert summary["width"] > 0
    assert summary["height"] > 0

    # Extract with limits
    box = summary["plot_box"] or [10, 10, summary["width"] - 10, summary["height"] - 10]
    lim_summary = session.extract_with_limits_cmd(
        xmin=0.0,
        xmax=10.0,
        ymin=0.0,
        ymax=10.0,
        plot_box=(box[0], box[1], box[2], box[3]),
    )
    assert lim_summary["calibrated"]
    assert len(lim_summary["series"]) >= 1
    s0_id = lim_summary["series"][0]["series_id"]

    # Clear range
    cov_before = lim_summary["series"][0]["coverage"]
    cleared = session.clear(4.0, 6.0, series_id=s0_id)
    assert cleared["series"][0]["coverage"] < cov_before

    # Undo
    undone = session.undo()
    assert undone["series"][0]["coverage"] == cov_before

    # Trace stroke
    # Find pixel coordinates of curve
    pts = session.current_result.series[0].points  # type: ignore[union-attr]
    valid_pts = [p for p in pts if p.x is not None]
    p_start = valid_pts[10]
    p_end = valid_pts[-10]
    traced = session.trace(
        [(p_start.px, p_start.py), (p_end.px, p_end.py)],
        series_id=s0_id,
        radius=8.0,
    )
    assert len(traced["series"]) >= 1

    # Rename series
    renamed = session.rename_series(s0_id, "my_custom_label")
    assert renamed["series"][0]["label"] == "my_custom_label"


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_web_http_endpoints(tmp_path: Path) -> None:
    session = WebSession(work_dir=tmp_path)
    png_bytes = _sample_png()
    session.load(png_bytes, "fig.png")

    handler_class = type("TestBoundWebHandler", (WebHandler,), {"session": session})
    port = _get_free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_class)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    try:
        # GET /
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Curve2csv Web Interactive" in content

        # GET /api/summary
        with urllib.request.urlopen(f"{base_url}/api/summary") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["loaded"]

        # GET /api/image/source.png
        with urllib.request.urlopen(f"{base_url}/api/image/source.png") as resp:
            assert resp.status == 200
            img_data = resp.read()
            assert len(img_data) > 100

        # GET /api/image/overlay.png
        with urllib.request.urlopen(f"{base_url}/api/image/overlay.png") as resp:
            assert resp.status == 200
            overlay_data = resp.read()
            assert len(overlay_data) > 100

        # POST /api/extract_limits
        req = urllib.request.Request(
            f"{base_url}/api/extract_limits",
            data=json.dumps({"xmin": 0, "xmax": 10, "ymin": 0, "ymax": 10}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["calibrated"]

        # GET /api/export/csv
        with urllib.request.urlopen(f"{base_url}/api/export/csv") as resp:
            assert resp.status == 200
            csv_text = resp.read().decode("utf-8")
            assert "series_id" in csv_text

        # GET /api/export/json
        with urllib.request.urlopen(f"{base_url}/api/export/json") as resp:
            assert resp.status == 200
            json_text = resp.read().decode("utf-8")
            assert "schema_version" in json_text

    finally:
        server.shutdown()
        server.server_close()
