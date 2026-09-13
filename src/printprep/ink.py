"""Take a colour from the artwork itself, for lettering or marks added beside it.

Pure typeset black next to a printed, textured line looks pasted on; the drawing's own darkest ink
rarely is pure black. But "the darkest ink" is only right for a dark design. A pale design meant
for a dark garment has its darkest pixels in a mid grey that belongs to neither the artwork nor
the shirt. So the sampling branches on which way the design's ink actually sits.
"""
from __future__ import annotations

import numpy as np

from ._img import luminance, to_rgba_array


def sample_ink(image, light_threshold: float = 140, quantile: float = 0.07) -> tuple:
    """(r, g, b) of the artwork's own ink: its darkest solid ink, or its lightest if it is a light
    design. Falls back to a warm near-black when there is too little solid artwork to judge."""
    a = to_rgba_array(image)
    rgb, alpha = a[..., :3], a[..., 3]
    solid = alpha > 200
    if solid.sum() < 50:
        return (31, 23, 19)
    lum = luminance(rgb)
    light = float(lum[solid].mean()) > light_threshold
    q = np.quantile(lum[solid], 1 - quantile if light else quantile)
    pick = solid & ((lum >= q) if light else (lum <= max(q, 1.0)))
    if pick.sum() < 20:
        pick = solid
    return tuple(int(round(v)) for v in rgb[pick].mean(axis=0))
