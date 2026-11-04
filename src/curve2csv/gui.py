"""Desktop window: open an image or PDF page, type axis endpoints, export CSV."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from typing import cast

import numpy as np
from PIL import Image, ImageTk

from curve2csv.api import extract, extract_with_limits
from curve2csv.errors import InputError
from curve2csv.io.image import load_image
from curve2csv.io.labels import rename_series_label
from curve2csv.types import Abstain, AxisCalibration, AxisScale, ExtractionResult

_PREVIEW = 640


def run_gui() -> int:
    root = _make_root()
    App(root)
    root.mainloop()
    return 0


def _make_root() -> tk.Tk:
    try:
        from tkinterdnd2 import TkinterDnD

        widget = cast(tk.Tk, TkinterDnD.Tk())
    except Exception:
        widget = tk.Tk()
    widget.title("Curve2csv")
    return widget


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.rgb: np.ndarray | None = None
        self.image_path: Path | None = None
        self.csv_path: Path | None = None
        self.json_path: Path | None = None
        self._figure_photo: ImageTk.PhotoImage | None = None
        self._overlay_photo: ImageTk.PhotoImage | None = None
        self._scale = 1.0
        self._crop_start: tuple[int, int] | None = None

        self.xmin = tk.StringVar(value="0")
        self.xmax = tk.StringVar(value="1")
        self.ymin = tk.StringVar(value="0")
        self.ymax = tk.StringVar(value="1")
        self.x_log = tk.BooleanVar(value=False)
        self.y_log = tk.BooleanVar(value=False)
        self.read_labels = tk.BooleanVar(value=True)
        self.page = tk.StringVar(value="1")
        self.status = tk.StringVar(value="Open an image or a PDF page. Tick labels are not read.")
        self.series_id = tk.StringVar()
        self.series_label = tk.StringVar()

        bar = ttk.Frame(root, padding=8)
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Open…", command=self.open_dialog).pack(side=tk.LEFT)
        ttk.Label(bar, text="PDF page").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(bar, textvariable=self.page, width=4).pack(side=tk.LEFT)
        ttk.Button(bar, text="Extract", command=self.extract).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Export folder…", command=self.export_folder).pack(side=tk.LEFT)

        axes = ttk.Frame(root, padding=(8, 0))
        axes.pack(fill=tk.X)
        for label, var in (
            ("xmin", self.xmin),
            ("xmax", self.xmax),
            ("ymin", self.ymin),
            ("ymax", self.ymax),
        ):
            ttk.Label(axes, text=label).pack(side=tk.LEFT)
            ttk.Entry(axes, textvariable=var, width=8).pack(side=tk.LEFT, padx=(2, 8))
        ttk.Checkbutton(axes, text="x log10", variable=self.x_log).pack(side=tk.LEFT)
        ttk.Checkbutton(axes, text="y log10", variable=self.y_log).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(axes, text="Read tick labels", variable=self.read_labels).pack(side=tk.LEFT)

        body = ttk.Frame(root, padding=8)
        body.pack(fill=tk.BOTH, expand=True)
        self.figure = ttk.Label(body, text="Drop an image here, or use Open.")
        self.figure.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.figure.bind("<Button-1>", self._on_click)
        self.overlay = ttk.Label(body)
        self.overlay.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        edit = ttk.Frame(root, padding=(8, 0))
        edit.pack(fill=tk.X)
        ttk.Label(edit, text="series id").pack(side=tk.LEFT)
        ttk.Entry(edit, textvariable=self.series_id, width=12).pack(side=tk.LEFT, padx=(2, 8))
        ttk.Label(edit, text="label").pack(side=tk.LEFT)
        ttk.Entry(edit, textvariable=self.series_label, width=24).pack(side=tk.LEFT, padx=(2, 8))
        ttk.Button(edit, text="Rename series", command=self.rename).pack(side=tk.LEFT)

        ttk.Label(root, textvariable=self.status, padding=8, wraplength=720).pack(fill=tk.X)
        self._enable_drop()

    def _enable_drop(self) -> None:
        try:
            from tkinterdnd2 import DND_FILES
        except Exception:
            return
        register = getattr(self.root, "drop_target_register", None)
        bind = getattr(self.root, "dnd_bind", None)
        if register is None or bind is None:
            return
        register(DND_FILES)
        bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event: object) -> None:
        data = str(getattr(event, "data", ""))
        paths = _split_drop(data)
        if paths:
            self._load_path(Path(paths[0]))

    def open_dialog(self) -> None:
        name = filedialog.askopenfilename(
            title="Open a figure",
            filetypes=[
                ("Figures", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp *.pdf"),
                ("All files", "*.*"),
            ],
        )
        if name:
            self._load_path(Path(name))

    def _load_path(self, path: Path) -> None:
        try:
            page = int(self.page.get().strip() or "1")
            loaded = load_image(path, page=page)
        except (InputError, ValueError) as exc:
            self.status.set(str(exc))
            return
        self.rgb = np.array(loaded.rgb, copy=True)
        self._crop_start = None
        cache = _cache_dir()
        self.image_path = cache / ("page.png" if path.suffix.lower() == ".pdf" else path.name)
        _write_png(self.image_path, self.rgb)
        self._show_figure()
        which = f" page {loaded.page}" if loaded.page is not None else ""
        self.status.set(f"Loaded {path.name}{which}. Click two corners to crop, then Extract.")

    def _show_figure(self) -> None:
        if self.image_path is None:
            return
        photo, scale = _preview(self.image_path)
        self._figure_photo = photo
        self._scale = scale
        self.figure.configure(image=photo, text="")

    def _on_click(self, event: tk.Event[tk.Misc]) -> None:
        if self.rgb is None or self._scale <= 0:
            return
        col = int(event.x / self._scale)
        row = int(event.y / self._scale)
        if self._crop_start is None:
            self._crop_start = (col, row)
            self.status.set("First corner set. Click the opposite corner.")
            return
        c0, r0 = self._crop_start
        self._crop_start = None
        x0, x1 = sorted((c0, col))
        y0, y1 = sorted((r0, row))
        if x1 - x0 < 20 or y1 - y0 < 20:
            self.status.set("Crop is smaller than 20 pixels. Click two corners again.")
            return
        height, width = self.rgb.shape[:2]
        x0 = max(0, min(width - 1, x0))
        x1 = max(x0 + 1, min(width, x1))
        y0 = max(0, min(height - 1, y0))
        y1 = max(y0 + 1, min(height, y1))
        self.rgb = np.array(self.rgb[y0:y1, x0:x1], copy=True)
        if self.image_path is not None:
            _write_png(self.image_path, self.rgb)
            self._show_figure()
        self.status.set("Cropped. Set the axis endpoints and extract.")

    def extract(self) -> None:
        if self.image_path is None:
            self.status.set("Open a figure first.")
            return
        out = _cache_dir() / "extract"
        if self.read_labels.get():
            try:
                result = extract(self.image_path, out=out)
            except InputError as exc:
                self.status.set(str(exc))
                return
            if _both_axes(result):
                self._fill_limits(result)
                self.read_labels.set(False)
                self._show_result(
                    result,
                    out,
                    "Tick labels were read. Edit the endpoints and extract again to override them. ",
                )
                return
            self.status.set("Tick labels were not read. Using the typed endpoints.")
        try:
            xmin = float(self.xmin.get())
            xmax = float(self.xmax.get())
            ymin = float(self.ymin.get())
            ymax = float(self.ymax.get())
        except ValueError:
            self.status.set("Axis endpoints must be numbers.")
            return
        try:
            result = extract_with_limits(
                self.image_path,
                xmin=xmin,
                xmax=xmax,
                ymin=ymin,
                ymax=ymax,
                x_scale=AxisScale.LOG10 if self.x_log.get() else AxisScale.LINEAR,
                y_scale=AxisScale.LOG10 if self.y_log.get() else AxisScale.LINEAR,
                out=out,
            )
        except InputError as exc:
            self.status.set(str(exc))
            return
        self._show_result(result, out, "")

    def _fill_limits(self, result: ExtractionResult) -> None:
        area = result.plot_area
        mapper = result.mapper
        if isinstance(area, Abstain) or mapper is None:
            return
        x0, y0, x1, y1 = area.bbox
        bottom_left = mapper.pixel_to_data(float(x0), float(y1))
        bottom_right = mapper.pixel_to_data(float(x1), float(y1))
        top_left = mapper.pixel_to_data(float(x0), float(y0))
        if bottom_left is None or bottom_right is None or top_left is None:
            return
        self.xmin.set(f"{bottom_left[0]:.6g}")
        self.xmax.set(f"{bottom_right[0]:.6g}")
        self.ymin.set(f"{bottom_left[1]:.6g}")
        self.ymax.set(f"{top_left[1]:.6g}")
        x_cal = result.calibration.get("x")
        y_cal = result.calibration.get("y")
        if isinstance(x_cal, AxisCalibration):
            self.x_log.set(x_cal.scale is AxisScale.LOG10)
        if isinstance(y_cal, AxisCalibration):
            self.y_log.set(y_cal.scale is AxisScale.LOG10)

    def _show_result(self, result: ExtractionResult, out: Path, prefix: str) -> None:
        if self.image_path is None:
            return
        stem = self.image_path.stem
        self.csv_path = out / f"{stem}.csv"
        self.json_path = out / f"{stem}.json"
        overlay = out / f"{stem}.overlay.png"
        if overlay.is_file():
            photo, _scale = _preview(overlay)
            self._overlay_photo = photo
            self.overlay.configure(image=photo)
        points = sum(len(series.points) for series in result.series)
        ids = ", ".join(series.series_id for series in result.series) or "none"
        self.status.set(
            f"{prefix}{len(result.series)} series, {points} points. "
            f"Ids: {ids}. Change the endpoints and extract again, or rename a series."
        )

    def rename(self) -> None:
        if self.csv_path is None or self.json_path is None:
            self.status.set("Extract a figure before renaming a series.")
            return
        try:
            rename_series_label(
                self.csv_path,
                self.json_path,
                self.series_id.get().strip(),
                self.series_label.get().strip(),
            )
        except InputError as exc:
            self.status.set(str(exc))
            return
        self.status.set(f"Renamed {self.series_id.get().strip()}. Coordinates are unchanged.")

    def export_folder(self) -> None:
        if self.csv_path is None or not self.csv_path.is_file():
            self.status.set("Extract a figure before exporting.")
            return
        folder = filedialog.askdirectory(title="Export CSV and JSON")
        if not folder:
            return
        dest = Path(folder)
        for path in (self.csv_path, self.json_path):
            if path is not None and path.is_file():
                (dest / path.name).write_bytes(path.read_bytes())
        overlay = self.csv_path.with_name(self.csv_path.stem + ".overlay.png")
        if overlay.is_file():
            (dest / overlay.name).write_bytes(overlay.read_bytes())
        self.status.set(f"Wrote CSV, JSON, and overlay into {dest}.")


def _both_axes(result: ExtractionResult) -> bool:
    return all(isinstance(result.calibration.get(name), AxisCalibration) for name in ("x", "y"))


def _cache_dir() -> Path:
    path = Path.home() / ".cache" / "curve2csv"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_png(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb).save(path)


def _preview(path: Path) -> tuple[ImageTk.PhotoImage, float]:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    scale = min(1.0, _PREVIEW / max(width, height, 1))
    if scale < 1.0:
        image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))))
    return ImageTk.PhotoImage(image), scale


def _split_drop(data: str) -> list[str]:
    paths: list[str] = []
    token: list[str] = []
    brace = False
    for char in data:
        if char == "{":
            brace = True
        elif char == "}":
            brace = False
        elif char == " " and not brace:
            if token:
                paths.append("".join(token))
                token = []
        else:
            token.append(char)
    if token:
        paths.append("".join(token))
    return paths
