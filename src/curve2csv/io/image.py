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


def load_image(src: str | Path | NDArray[np.uint8]) -> LoadedImage:
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
    try:
        with Image.open(path) as handle:
            loaded = _to_rgb_array(handle)
    except InputError:
        raise
    except Exception as exc:  # Pillow raises several image-specific errors.
        raise InputError(f"could not read image: {path}") from exc
    return LoadedImage(rgb=loaded, source=str(path), sha256=_hash_bytes(path.read_bytes()))
