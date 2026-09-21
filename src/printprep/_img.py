"""Small conversions shared by every module.

EVERYTHING INSIDE printprep IS 8-BIT-RANGED FLOAT
-------------------------------------------------
Distances, tolerances and grain are all in 0..255 units, so every source has to arrive in that
range. Most do. High-bit-depth GREYSCALE does not: Pillow loads a 16-bit grey PNG or TIFF as mode
"I;16" or "I", and its own `convert("RGB")` saturates every value above 255 to white. A 16-bit scan
run through that becomes a blank page, and the failure is silent - the ground is measured as pure
white and the whole image keys away. Those modes are rescaled here instead. High-bit-depth RGB and
RGBA files are handled by Pillow correctly on load, so they need nothing.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

#: Pillow modes that carry more than 8 bits in a single channel. `convert()` saturates these.
HIGH_DEPTH_MODES = frozenset({"I", "I;16", "I;16B", "I;16L", "I;16N"})

#: 16-bit full scale to 8-bit full scale: 65535 / 255.
_SIXTEEN_BIT = 257.0


def _high_depth_to_8bit(image: Image.Image) -> np.ndarray:
    """H x W float32 in 0..255 from a high-bit-depth greyscale image.

    The data is taken as 16-bit full scale, which is what every such image file this reads
    actually is. That is a fixed conversion on purpose: scaling by the image's own maximum
    instead would make a dark scan and a bright one land on different tolerances.
    """
    return np.asarray(image).astype(np.float32) / _SIXTEEN_BIT


def _array_to_float(array) -> np.ndarray:
    """float32 in 0..255 from a numpy array, refusing values that are plainly not 8-bit.

    uint16 is rescaled. Any other integer type holding values above 255 is refused rather than
    guessed at, because reading it as 8-bit would put every threshold in the wrong place.
    float is taken as already 0..255, which is what this module hands back.
    """
    a = np.asarray(array)
    if a.dtype == np.uint16:
        return a.astype(np.float32) / _SIXTEEN_BIT
    if np.issubdtype(a.dtype, np.integer) and a.dtype != np.uint8 and a.size:
        top = int(a.max())
        if top > 255:
            raise ValueError(
                f"array of dtype {a.dtype} runs to {top}, which is not 8-bit. Pass uint16, or "
                f"scale it to 0..255 yourself - printprep will not guess the range.")
    return a.astype(np.float32)


def to_rgb_array(image) -> np.ndarray:
    """H x W x 3 float32 in 0..255, from a PIL image or an array (alpha is dropped)."""
    if isinstance(image, Image.Image):
        if image.mode in HIGH_DEPTH_MODES:
            return np.repeat(_high_depth_to_8bit(image)[..., None], 3, axis=-1)
        return np.asarray(image.convert("RGB")).astype(np.float32)
    a = _array_to_float(image)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return a[..., :3]


def to_rgba_array(image) -> np.ndarray:
    """H x W x 4 float32 in 0..255. An image with no alpha is treated as fully opaque."""
    if isinstance(image, Image.Image):
        if image.mode in HIGH_DEPTH_MODES:
            rgb = np.repeat(_high_depth_to_8bit(image)[..., None], 3, axis=-1)
            return np.concatenate(
                [rgb, np.full(rgb.shape[:2] + (1,), 255.0, np.float32)], axis=-1)
        return np.asarray(image.convert("RGBA")).astype(np.float32)
    a = _array_to_float(image)
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
