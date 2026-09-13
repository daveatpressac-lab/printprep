"""Small conversions shared by every module."""
from __future__ import annotations

import numpy as np
from PIL import Image


def to_rgb_array(image) -> np.ndarray:
    """H x W x 3 float32 in 0..255, from a PIL image or an array (alpha is dropped)."""
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB")).astype(np.float32)
    a = np.asarray(image)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return a[..., :3].astype(np.float32)


def to_rgba_array(image) -> np.ndarray:
    """H x W x 4 float32 in 0..255. An image with no alpha is treated as fully opaque."""
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGBA")).astype(np.float32)
    a = np.asarray(image).astype(np.float32)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    if a.shape[-1] == 3:
        a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255.0, np.float32)], axis=-1)
    return a


def has_alpha(image) -> bool:
    """Does the image carry a real alpha channel, as opposed to none at all?"""
    if isinstance(image, Image.Image):
        return image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
    a = np.asarray(image)
    return a.ndim == 3 and a.shape[-1] == 4


def to_image(rgba: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA")


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., :3].mean(axis=-1)


def alpha_bbox(alpha: np.ndarray, threshold: float = 8):
    """(x0, y0, x1, y1) of pixels above `threshold`, or None if there are none."""
    ys, xs = np.where(alpha > threshold)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
