"""Image loading: EXIF orientation, alpha composited on white, original-resolution RGB."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageOps

from curve2csv.errors import InputError
from curve2csv.types import LoadedImage


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _to_rgb_array(image: Image.Image) -> NDArray[np.uint8]:
    image = ImageOps.exif_transpose(image)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    else:
        image = image.convert("RGB")
    array = np.asarray(image, dtype=np.uint8)
    if array.ndim != 3 or array.shape[2] != 3:
        raise InputError("expected an RGB image")
    return np.ascontiguousarray(array)


def _load_pdf_page(path: Path, page: int) -> tuple[NDArray[np.uint8], int]:
    if page < 1:
        raise InputError("PDF page numbers start at 1")
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise InputError("reading a PDF needs the gui extra: pip install curve2csv[gui]") from exc
    document = pdfium.PdfDocument(str(path))
    try:
        count = len(document)
        if page > count:
            raise InputError(f"PDF has {count} page(s); asked for page {page}")
        rendered = document[page - 1].render(scale=2.0)
        pil = rendered.to_pil().convert("RGB")
        return _to_rgb_array(pil), page
    finally:
        document.close()


def load_image(src: str | Path | NDArray[np.uint8], *, page: int = 1) -> LoadedImage:
    if isinstance(src, np.ndarray):
        array = np.asarray(src)
        if array.ndim == 2:
            array = np.stack([array, array, array], axis=-1)
        if array.ndim != 3 or array.shape[2] not in {3, 4}:
            raise InputError("ndarray must have shape HxWx3 or HxWx4")
        if array.shape[2] == 4:
            channels = array[:, :, :3].astype(np.float32)
            alpha = array[:, :, 3:4].astype(np.float32) / 255.0
            array = (channels * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)
        else:
            array = np.ascontiguousarray(array.astype(np.uint8, copy=False))
        digest = _hash_bytes(array.tobytes())
        return LoadedImage(rgb=array, source="memory", sha256=digest)
    path = Path(src)
    if not path.is_file():
        raise InputError(f"image not found: {path}")
    page_index: int | None = None
    try:
        if path.suffix.lower() == ".pdf":
            loaded, page_index = _load_pdf_page(path, page)
        else:
            with Image.open(path) as handle:
                loaded = _to_rgb_array(handle)
    except InputError:
        raise
    except Exception as exc:  # Pillow raises several image-specific errors.
        raise InputError(f"could not read image: {path}") from exc
    return LoadedImage(
        rgb=loaded,
        source=str(path),
        sha256=_hash_bytes(path.read_bytes()),
        page=page_index,
    )
