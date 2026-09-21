"""Place artwork on a print canvas at one scale, centred, never stretched.

Stretching is the quiet failure. A helper that resizes to a target width AND height will force a
tall design into a square canvas, and if every design you test happens to be square it can go
unnoticed for a long time. Here there is exactly one scale factor, chosen by whichever axis runs
out of room first, and the aspect drift is reported so a test can pin it near zero.

`aspect_drift` IS A FRACTION, NOT A DIFFERENCE OF RATIOS
--------------------------------------------------------
Rounding the placed size to whole pixels distorts the artwork a little, and how much is only
meaningful relative to the shape. Subtracting one aspect ratio from another reports the same
distortion very differently depending on which way up the artwork is, and it reports it wrongly in
both directions: a 4000 x 20 strip rounded to 0.7% distortion scored 1.43 and looked catastrophic,
while a 20 x 4000 strip rounded to 1.5% distortion scored 0.000075 and looked perfect. So the
drift is the fractional change in the aspect ratio, and a single threshold means the same thing
for every shape.
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
    #: Fractional change in the aspect ratio: 0.01 means one per cent distorted.
    aspect_drift: float


def fit_to_canvas(image, canvas=DEFAULT_CANVAS, margin: float = 0.94,
                  crop_to_art: bool = True, alpha_threshold: float = 8) -> FitResult:
    """Crop to the visible artwork, scale once to fit `margin` of the canvas, centre it.

    `margin` keeps the artwork off the very edge of the print area. The returned `aspect_drift` is
    the fraction by which the aspect ratio changed, so `< 0.005` means under half a per cent
    whatever shape the artwork is.
    """
    cw, ch = canvas
    if cw < 1 or ch < 1:
        raise ValueError(f"the canvas must be at least 1x1 pixels, not {cw}x{ch}")
    if not 0 < margin <= 1:
        raise ValueError(f"margin must be above 0 and at most 1, not {margin}. Above 1 scales the "
                         f"artwork past the canvas, and the overhang is silently cut off.")
    rgba = to_rgba_array(image)
    if crop_to_art:
        box = alpha_bbox(rgba[..., 3], alpha_threshold)
        if box is None:
            raise ValueError("the image has no visible artwork to fit")
        x0, y0, x1, y1 = box
        rgba = rgba[y0:y1, x0:x1]
    art = to_image(rgba)
    s = min(cw * margin / art.width, ch * margin / art.height)
    w, h = max(1, round(art.width * s)), max(1, round(art.height * s))
    placed = art.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    off = ((cw - w) // 2, (ch - h) // 2)
    out.alpha_composite(placed, off)
    drift = abs((w / h) / (art.width / art.height) - 1.0)
    return FitResult(out, s, (w, h), off, drift)


def save_master(image: Image.Image, path, dpi: int = 300) -> None:
    """Save as PNG with real alpha and a dpi tag."""
    image.convert("RGBA").save(path, dpi=(dpi, dpi))
