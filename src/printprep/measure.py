"""Pick a threshold by measuring the two things it separates, never by guessing.

Sample a few regions of the subject and a few of the background, take their luminance, and put the
threshold between them. If the darkest part of the subject is darker than the lightest part of the
background, no single luminance threshold can separate them, and you should know that before
spending an hour tuning one - use connectivity (key.py) or shape fitting (plate.py) instead.
"""
from __future__ import annotations

import numpy as np

from ._img import luminance, to_rgb_array


def region_luminance(image, box) -> float:
    """Median luminance of the (x0, y0, x1, y1) box."""
    a = to_rgb_array(image)
    x0, y0, x1, y1 = box
    region = a[y0:y1, x0:x1]
    if not region.size:
        raise ValueError(f"empty region {box}")
    return float(np.median(luminance(region)))


def midpoint_threshold(image, subject_boxes, background_boxes) -> dict:
    """A luminance threshold midway between subject and background, or a clear refusal.

    Assumes the subject is the LIGHTER of the two; for a dark subject on a light ground, swap the
    arguments. Raises ValueError when the ranges overlap, naming the offending measurements.
    """
    subj = {tuple(b): region_luminance(image, b) for b in subject_boxes}
    back = {tuple(b): region_luminance(image, b) for b in background_boxes}
    darkest_subject = min(subj.values())
    lightest_background = max(back.values())
    if darkest_subject <= lightest_background:
        raise ValueError(
            f"subject and background overlap: darkest subject region L{darkest_subject:.0f} is not "
            f"lighter than the lightest background region L{lightest_background:.0f}. No luminance "
            f"threshold separates them.")
    return {"threshold": round((darkest_subject + lightest_background) / 2, 1),
            "darkest_subject": round(darkest_subject, 1),
            "lightest_background": round(lightest_background, 1),
            "gap": round(darkest_subject - lightest_background, 1)}
