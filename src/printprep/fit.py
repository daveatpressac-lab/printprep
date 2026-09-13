"""Place artwork on a print canvas at one scale, centred, never stretched.

Stretching is the quiet failure. A helper that resizes to a target width AND height will force a
tall design into a square canvas, and if every design you test happens to be square it can go
unnoticed for a long time. Here there is exactly one scale factor, chosen by whichever axis runs
out of room first, and the aspect drift is reported so a test can pin it at zero.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np
from PIL import Image

from ._img import alpha_bbox, to_image, to_rgba_array

#: A common direct-to-garment print area: 15 x 18 inches at 300 dpi.
DEFAULT_CANVAS = (4500, 5400)


class FitResult(NamedTuple):
    image: Image.Image
    scale: float
    placed: tuple
    offset: tuple
    aspect_drift: float


def fit_to_canvas(image, canvas=DEFAULT_CANVAS, margin: float = 0.94,
                  crop_to_art: bool = True, alpha_threshold: float = 8) -> FitResult:
    """Crop to the visible artwork, scale once to fit `margin` of the canvas, centre it.

    `margin` keeps the artwork off the very edge of the print area.
    """
    rgba = to_rgba_array(image)
    if crop_to_art:
        box = alpha_bbox(rgba[..., 3], alpha_threshold)
        if box is None:
            raise ValueError("the image has no visible artwork to fit")
        x0, y0, x1, y1 = box
        rgba = rgba[y0:y1, x0:x1]
    art = to_image(rgba)
    cw, ch = canvas
    s = min(cw * margin / art.width, ch * margin / art.height)
    w, h = max(1, round(art.width * s)), max(1, round(art.height * s))
    placed = art.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    off = ((cw - w) // 2, (ch - h) // 2)
    out.alpha_composite(placed, off)
    drift = abs(art.width / art.height - w / h)
    return FitResult(out, s, (w, h), off, drift)


def save_master(image: Image.Image, path, dpi: int = 300) -> None:
    """Save as PNG with real alpha and a dpi tag."""
    image.convert("RGBA").save(path, dpi=(dpi, dpi))
