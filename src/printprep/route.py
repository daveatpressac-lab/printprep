"""Should this artwork be enlarged by tracing it to vectors, or by resampling pixels?

RASTER IS THE DEFAULT, AND VECTOR HAS TO EARN ITS PLACE
-------------------------------------------------------
A raster enlargement is at worst a little softer than ideal. A bad trace destroys the artwork:
continuous tone posterises into blobs, dense hatching collapses into mush, and paper grain and
fine hairlines are smoothed away. No later step recovers any of that.

So tracing is only advised when the artwork measurably is the kind that traces well: most of it in
a handful of flat colours, coarse edges, and little mid-tone. The useful distinction is not "flat
versus tonal" - a flat-looking engraving can be full of fine hatching - it is LARGE FLAT SHAPES
versus FINE HIGH-FREQUENCY DETAIL.

The measurements are contrast-normalised first. Measured on raw values, a dark low-contrast design
looks as if it has no detail at all and gets routed to a trace that then smooths its linework away.

Even a "vector" verdict is advice, not proof. Run the trace, then `qc.fidelity()` against the
source, and look at the result - a trace can keep alpha and colour almost perfect while its detail
ratio falls well below 1.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from ._img import to_rgba_array


def analyse(image, work_size: int = 320) -> dict:
    """The properties the route decision uses. Facts only, no judgement."""
    a = to_rgba_array(image).astype(np.uint8)
    im = Image.fromarray(a, "RGBA")
    im.thumbnail((work_size, work_size))
    a = np.asarray(im).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3]
    vis = alpha > 32
    n_vis = int(vis.sum()) or 1

    q = (rgb[vis] // 24).astype(np.int32)
    _, counts = np.unique(q.reshape(-1, 3), axis=0, return_counts=True)
    top8 = float(np.sort(counts)[::-1][:8].sum()) / n_vis

    g = rgb.mean(axis=2)
    gv = g[vis]
    lo, hi = (np.percentile(gv, 1), np.percentile(gv, 99)) if gv.size else (0, 255)
    gs = np.clip((gv - lo) / max(1e-6, hi - lo), 0, 1) * 255
    hist, _ = np.histogram(gs, bins=16, range=(0, 256))
    hist = hist / max(1, hist.sum())
    midtone = float(hist[4:12].sum())

    gn = np.clip((g - lo) / max(1e-6, hi - lo), 0, 1) * 255
    gx = np.abs(np.diff(gn, axis=1, prepend=gn[:, :1]))
    gy = np.abs(np.diff(gn, axis=0, prepend=gn[:1, :]))
    edges = (gx + gy) > 40
    return {"visible_pct": round(n_vis * 100.0 / alpha.size, 1),
            "top8_colour_share": round(top8, 3),
            "midtone_share": round(midtone, 3),
            "edge_density": round(float(edges[vis].mean()) if vis.any() else 0.0, 3)}


def choose_enlargement(image, texture_dependent: bool = False) -> dict:
    """{route: 'vector' | 'raster', confidence, reasons, measured}.

    texture_dependent  set True for artwork whose look depends on grain, stipple, halftone or
                       photographic tone. That alone vetoes tracing, whatever the pixels say.
    """
    m = analyse(image)
    if texture_dependent:
        return {"route": "raster", "confidence": "vetoed",
                "reasons": ["marked texture-dependent - tracing would flatten the texture"],
                "measured": m}
    if m["midtone_share"] >= 0.60:
        return {"route": "raster", "confidence": "measured",
                "reasons": [f"mid-tone share {m['midtone_share']} - continuous tone, which tracing "
                            f"posterises"], "measured": m}
    flat = m["top8_colour_share"] >= 0.90
    coarse = m["edge_density"] < 0.35
    not_tonal = m["midtone_share"] < 0.45
    if flat and coarse and not_tonal:
        return {"route": "vector", "confidence": "measured - verify with qc.fidelity and look",
                "reasons": [f"{int(m['top8_colour_share'] * 100)}% of it is 8 colours, edge density "
                            f"{m['edge_density']}, mid-tone {m['midtone_share']}: large flat shapes"],
                "measured": m}
    why = []
    if not flat:
        why.append(f"only {int(m['top8_colour_share'] * 100)}% of it is 8 colours")
    if not coarse:
        why.append(f"edge density {m['edge_density']} means fine detail")
    if not not_tonal:
        why.append(f"mid-tone share {m['midtone_share']} is too tonal to trace safely")
    return {"route": "raster", "confidence": "default",
            "reasons": ["not clearly large flat shapes: " + "; ".join(why),
                        "raster is the safe default - softer at worst, never destroyed"],
            "measured": m}
