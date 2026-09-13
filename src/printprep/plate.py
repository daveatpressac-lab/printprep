"""Cut a straight-sided subject - a poster, a framed panel, a slab - by fitting its shape.

When the subject is a rectangle, testing pixels one at a time is the wrong question. A ragged
printed edge, a strip of cast shadow, or a shaded bevel that is darker than the ground on one side
will each defeat a threshold somewhere along the edge. The shape is known, so fit it: find the
subject's outline and reduce it to a four-point polygon. The quadrilateral straightens a ragged
strip away and carries a shaded edge back, because a straight edge is what the subject really has.

`cv2.approxPolyDP` is used rather than a convex hull. A hull can only add area, so if a corner is
missing from the input mask it bridges straight across and shears the corner off.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from ._img import to_image, to_rgb_array
from .key import estimate_ground


def fit_quadrilateral(image, ground=None, tolerance: float = 45, close: int = 25,
                      epsilon: float = 0.02, mask=None) -> np.ndarray:
    """The subject's outline as a polygon, N x 2 int (x, y). Four points for a clean rectangle.

    By default the subject is everything further than `tolerance` from the ground colour. For a
    subject on a busy or shadowed ground, build your own boolean `mask` and pass it instead.
    `close` bridges small gaps in the outline (ornament, lettering) before fitting.
    """
    if mask is None:
        a = to_rgb_array(image)
        g = estimate_ground(a) if ground is None else np.asarray(ground, np.float32)
        mask = np.abs(a - g).max(axis=-1) > tolerance
    m = np.asarray(mask).astype(np.uint8)
    if close and close > 1:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("no subject found - lower the tolerance or pass a mask")
    c = max(contours, key=cv2.contourArea)
    poly = cv2.approxPolyDP(c, epsilon * cv2.arcLength(c, True), True)
    return poly.reshape(-1, 2).astype(int)


def cut_plate(image, polygon=None, **fit_kwargs) -> Image.Image:
    """The image with everything outside `polygon` transparent, and an anti-aliased edge."""
    if polygon is None:
        polygon = fit_quadrilateral(image, **fit_kwargs)
    a = to_rgb_array(image)
    h, w = a.shape[:2]
    # Draw at 4x and downsample, so the cut edge is anti-aliased rather than stair-stepped.
    s = 4
    big = np.zeros((h * s, w * s), np.uint8)
    cv2.fillPoly(big, [np.asarray(polygon, np.int32) * s + s // 2], 255)
    alpha = np.asarray(Image.fromarray(big).resize((w, h), Image.BOX)).astype(np.float32)
    return to_image(np.dstack([a, alpha]))
