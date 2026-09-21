"""Cut artwork off a plain ground without eating the parts that share the ground's colour.

WHY CONNECTIVITY, NOT COLOUR
----------------------------
A drawing on cream paper usually has cream INSIDE it too: the whites of an eye, whiskers, a
highlight, a hairline gap between two shapes. A colour key makes all of those transparent, which is
correct physics and a useless garment. Here only ground that is REACHABLE FROM THE IMAGE BORDER is
background. Ground colour enclosed by the artwork stays, as the deliberate ink it is.

WHY ALPHA IS MEASURED COVERAGE, NOT A BLURRED MASK
--------------------------------------------------
The two obvious ways to soften the cut both print a pale halo on dark garments:

* Blurring a hard 0/255 mask puts partial alpha on pixels whose colour is pure ground. Composited
  on a dark shirt, that is a faint ring of paper colour around every shape.
* A single global ramp (alpha rises from 0 to 1 as distance from the ground colour rises across a
  fixed range) overstates coverage for dark ink. An edge pixel that is one-fifth black ink is
  already a long way from cream, so a fixed ramp calls it mostly opaque - and the fringe comes back.

An anti-aliased edge pixel's ink coverage is its distance from the ground AS A FRACTION OF ITS OWN
INK'S distance, and one design can hold inks at very different distances (a black outline and a
pink fill). So the reference is taken locally: the strongest ink within a small window. Then the
partial pixels are UNMULTIPLIED - the ground colour they still carry is divided out - so the edge
takes the colour of the garment it is printed on.

Coverage is only estimated in a narrow band along the outside edge. Everywhere else inside the
artwork is fully opaque, so seams between two inks (a black body meeting a cream eye) never become
semi-transparent.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np
from scipy import ndimage

from ._img import has_alpha, to_image, to_rgb_array, to_rgba_array


class KeyResult(NamedTuple):
    image: "object"          # PIL.Image.Image, RGBA
    stats: dict


def estimate_ground(image, border: int = 6) -> np.ndarray:
    """The ground colour: the median of a thin ring round the image edge."""
    a = to_rgb_array(image)
    b = max(1, min(border, a.shape[0] // 2, a.shape[1] // 2))
    ring = np.concatenate([a[:b].reshape(-1, 3), a[-b:].reshape(-1, 3),
                           a[:, :b].reshape(-1, 3), a[:, -b:].reshape(-1, 3)])
    return np.median(ring, axis=0)


def ground_distance(image, ground=None) -> np.ndarray:
    """Per-pixel distance from the ground colour: the largest channel difference, 0..255."""
    a = to_rgb_array(image)
    g = estimate_ground(a) if ground is None else np.asarray(ground, np.float32)
    return np.abs(a - g).max(axis=-1)


def _outside(d, tolerance):
    near = d <= tolerance
    lbl, _ = ndimage.label(near)
    edge = np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])
    border = np.unique(edge[edge > 0])
    return near, np.isin(lbl, border)


def _refuse_artwork_that_is_already_cut_out(image) -> None:
    """key_ground reads colour only. Under a transparent pixel there is no colour to read - it is
    whatever happened to be left in the RGB channels, usually black or stale ground - so keying an
    already-cut image measures paint that was never there. Refuse it rather than return rubbish."""
    if not has_alpha(image):
        return
    clear_pct = float((to_rgba_array(image)[..., 3] < 128).mean() * 100)
    if clear_pct > 1.0:
        raise ValueError(
            f"this artwork is already cut out ({clear_pct:.1f}% of it is transparent). key_ground "
            f"reads colour, and the colour under a transparent pixel is undefined, so the result "
            f"would be meaningless. Composite it onto its ground first, or cut it with "
            f"plate.cut_plate(mask=...).")


def measure_grain(image, ground=None, tolerance: float = 30) -> dict:
    """How far the ground itself strays from its own colour. Use it to choose `grain`.

    Measured on the ground well away from any artwork (the border-connected ground, eroded), so
    anti-aliased edges do not inflate it. Set `grain` a little above `p99_9`, and keep `tolerance`
    above `max` but below the palest ink you need to keep.
    """
    a = to_rgb_array(image)
    g = estimate_ground(a) if ground is None else np.asarray(ground, np.float32)
    d = np.abs(a - g).max(axis=-1)
    _, outside = _outside(d, tolerance)
    core = ndimage.binary_erosion(outside, np.ones((9, 9)))
    vals = d[core] if core.any() else d[outside]
    out = {"ground": [round(float(v), 1) for v in g], "pixels": int(vals.size),
           "p50": None, "p99": None, "p99_9": None, "max": None}
    if not vals.size:
        # No ground reached the border, which nearly always means the `ground` colour passed in is
        # not this image's. The keys stay, empty, so a caller reading p99_9 gets None here rather
        # than a KeyError three steps later.
        return out
    out.update(p50=float(np.percentile(vals, 50)), p99=float(np.percentile(vals, 99)),
               p99_9=float(np.percentile(vals, 99.9)), max=float(vals.max()))
    return out


def key_ground(image, ground=None, tolerance: float = 30, grain: float = 24,
               window: int = 15, edge_width: int = 4, min_coverage: float = 0.15) -> KeyResult:
    """Return the artwork with its outside ground made transparent.

    image         PIL image or H x W x 3 array on a plain, roughly uniform ground
    ground        the ground colour; estimated from the image border when omitted
    tolerance     distance from ground that still counts as ground for connectivity
    grain         below this distance a pixel is the ground's own texture (alpha 0)
    window        px neighbourhood the local ink reference is taken from
    edge_width    px band along the outside edge where partial coverage is estimated
    min_coverage  smallest coverage the unmultiply divides by, so faint pixels stay stable
    """
    if tolerance <= 0:
        raise ValueError(f"tolerance ({tolerance}) must be above zero")
    if grain < 0:
        raise ValueError(f"grain ({grain}) cannot be negative")
    if not grain < tolerance:
        raise ValueError(f"grain ({grain}) must be below tolerance ({tolerance})")
    if window < 1 or edge_width < 1:
        raise ValueError(f"window ({window}) and edge_width ({edge_width}) are pixel counts and "
                         f"must be at least 1")
    _refuse_artwork_that_is_already_cut_out(image)
    a = to_rgb_array(image)
    g = estimate_ground(a) if ground is None else np.asarray(ground, np.float32)
    d = np.abs(a - g).max(axis=-1)

    near, outside = _outside(d, tolerance)
    enclosed = near & ~outside

    # The local reference must be REAL ink. In open ground the strongest nearby pixel is just a
    # grain speck, and measuring a speck against itself would call it fully covered - dotting the
    # transparent area with opaque flecks.
    ink_ref = ndimage.maximum_filter(d, size=window)
    real_ink = ink_ref > tolerance
    ref = np.maximum(ink_ref, grain + 1)
    coverage = np.where(real_ink, np.clip((d - grain) / (ref - grain), 0.0, 1.0), 0.0)
    coverage[real_ink & (d >= 0.85 * ref)] = 1.0

    band = ndimage.binary_dilation(outside, np.ones((3, 3)), iterations=max(1, edge_width))
    alpha = np.ones(d.shape, np.float32)
    alpha[band] = coverage[band]
    alpha[enclosed] = 1.0

    rgb = a.copy()
    part = (alpha > 0) & (alpha < 1)
    f = alpha[part][:, None]
    rgb[part] = np.clip((rgb[part] - g * (1 - f)) / np.maximum(f, min_coverage), 0, 255)

    out = np.dstack([rgb, alpha * 255.0])
    stats = {
        "ground": [round(float(v), 1) for v in g],
        "transparent_pct": round(float((alpha < 8 / 255).mean() * 100), 2),
        "enclosed_ground_kept_px": int(enclosed.sum()),
        "partial_alpha_px": int(part.sum()),
    }
    return KeyResult(to_image(out), stats)
