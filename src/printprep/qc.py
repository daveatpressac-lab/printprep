"""Measure a print master instead of eyeballing it.

TRANSPARENCY IS A PROPERTY OF THE ALPHA CHANNEL, NEVER OF A PREVIEW
-------------------------------------------------------------------
Many viewers draw transparent pixels as black. A black design keyed onto transparency then looks
exactly like a black design on a black rectangle, and a whole batch can be misjudged either way.
Everything here reads alpha directly.

A FRINGE IS INVISIBLE ON THE GROUND THE ARTWORK WAS DRAWN ON
------------------------------------------------------------
`halo()` composites onto a dark garment colour and measures the ring just outside the artwork.
Artwork drawn on cream will always look clean on cream.

A DELIBERATE RECTANGLE IS AN EXCEPTION, NOT A LOWER THRESHOLD
-------------------------------------------------------------
`check_master` refuses artwork that is almost entirely opaque inside its own bounding box, because
that is what a design that was never cut out looks like. Some designs are rectangles on purpose -
a poster, a framed panel. Lowering the threshold for them blinds the check for everything else.
Instead grant a `PlateException` to that one image, with a stated reason, bound to a hash of its
pixels. Change the picture and the exception stops applying. The measurement still runs and is
still reported; the finding moves from a problem to a warning.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage

from ._img import alpha_bbox, has_alpha, luminance, to_rgba_array

#: A dark garment colour. Fringes show here.
DARK_GROUND = (58, 58, 60)


def pixel_sha256(image) -> str:
    """A hash of the RGBA pixels and size - stable across re-saves that do not change pixels."""
    a = np.ascontiguousarray(to_rgba_array(image).astype(np.uint8))
    h = hashlib.sha256()
    h.update(f"{a.shape[1]}x{a.shape[0]}".encode())
    h.update(a.tobytes())
    return h.hexdigest()


@dataclass(frozen=True)
class PlateException:
    """Permission for ONE image to be a solid rectangle. Needs a reason; bound to its pixels."""
    reason: str
    sha256: str

    def __post_init__(self):
        if not (self.reason or "").strip():
            raise ValueError("a plate exception needs a stated reason")
        if not self.sha256:
            raise ValueError("a plate exception must be bound to the image it was granted for")

    @classmethod
    def for_image(cls, image, reason: str) -> "PlateException":
        return cls(reason=reason, sha256=pixel_sha256(image))

    def applies_to(self, image) -> bool:
        return self.sha256 == pixel_sha256(image)


def alpha_report(image, threshold: float = 8) -> dict:
    """Transparency facts, measured on the alpha channel."""
    a = to_rgba_array(image)
    al = a[..., 3]
    box = alpha_bbox(al, threshold)
    out = {"size": [int(al.shape[1]), int(al.shape[0])], "has_alpha": has_alpha(image),
           "transparent_pct": round(float((al < threshold).mean() * 100), 2),
           "corners_clear": bool(max(al[0, 0], al[0, -1], al[-1, 0], al[-1, -1]) <= threshold),
           "bbox": list(box) if box else None}
    if box:
        x0, y0, x1, y1 = box
        inner = al[y0:y1, x0:x1]
        out["transparent_in_bbox_pct"] = round(float((inner < threshold).mean() * 100), 2)
        out["touches_canvas_edge"] = bool(x0 == 0 or y0 == 0 or x1 == al.shape[1] or y1 == al.shape[0])
    return out


def halo(image, ground=DARK_GROUND, ring: int = 3) -> dict:
    """Composite onto `ground` and measure how much lighter the edge is than the ground.

    ring_1px_lum close to ground_lum means a clean edge. A pale fringe shows up as a 1px ring far
    brighter than the ground.
    """
    a = to_rgba_array(image)
    rgb, al = a[..., :3], a[..., 3:4] / 255.0
    g = np.asarray(ground, np.float32)
    comp = rgb * al + g * (1 - al)
    solid = a[..., 3] > 200
    r1 = ndimage.binary_dilation(solid, np.ones((3, 3))) & ~solid
    band = ndimage.binary_dilation(solid, np.ones((2 * ring + 1, 2 * ring + 1))) & ~solid
    if not r1.any():
        return {"ground_lum": float(g.mean()), "ring_1px_lum": None, "band_p95_lum": None}
    lum = luminance(comp)
    return {"ground_lum": round(float(g.mean()), 1),
            "ring_1px_lum": round(float(lum[r1].mean()), 1),
            "band_p95_lum": round(float(np.percentile(lum[band], 95)), 1)}


def _prepare(im, long_edge):
    a = to_rgba_array(im)
    box = alpha_bbox(a[..., 3])
    if box is None:
        raise ValueError("image has no visible artwork")
    x0, y0, x1, y1 = box
    crop = Image.fromarray(a[y0:y1, x0:x1].astype(np.uint8), "RGBA")
    s = long_edge / max(crop.size)
    crop = crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))),
                       Image.LANCZOS)
    return to_rgba_array(crop)


def _detail(rgba, opaque):
    g = luminance(rgba)
    if opaque.any():
        lo, hi = np.percentile(g[opaque], 1), np.percentile(g[opaque], 99)
        g = np.clip((g - lo) / max(1e-6, hi - lo), 0, 1) * 255
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    interior = ndimage.binary_erosion(opaque, np.ones((5, 5)))
    return float((gx + gy)[interior].mean()) if interior.any() else 0.0


def fidelity(result, source, long_edge: int = 1024) -> dict:
    """How faithfully `result` (an enlargement, a trace, a re-export) reproduces `source`.

    Both are cropped to their artwork and compared at the same size.

    alpha_iou          overlap of the cut-outs
    colour_similarity  1 - mean colour difference where both are opaque
    detail_ratio       interior edge energy of result / source. A trace that has smoothed texture
                       away scores well under 1 while alpha and colour still look excellent - look
                       at the artwork before accepting a low one.
    score              0.4 * alpha_iou + 0.3 * colour_similarity + 0.3 * min(detail_ratio, 1)
    """
    s = _prepare(source, long_edge)
    r = _prepare(result, long_edge)
    h, w = min(s.shape[0], r.shape[0]), min(s.shape[1], r.shape[1])
    s, r = s[:h, :w], r[:h, :w]
    sa, ra = s[..., 3] > 128, r[..., 3] > 128
    union = (sa | ra).sum()
    iou = float((sa & ra).sum() / union) if union else 1.0
    both = sa & ra
    colour = (1.0 - float(np.abs(s[..., :3] - r[..., :3])[both].mean()) / 255.0) if both.any() else 0.0
    ds = _detail(s, sa)
    detail = (_detail(r, ra) / ds) if ds > 0 else 1.0
    score = 0.4 * iou + 0.3 * colour + 0.3 * min(detail, 1.0)
    return {"alpha_iou": round(iou, 3), "colour_similarity": round(colour, 3),
            "detail_ratio": round(detail, 3), "score": round(score, 3)}


def check_master(image, canvas=(4500, 5400), min_transparent_in_bbox: float = 2.0,
                 plate_exception: PlateException | None = None) -> dict:
    """Gate a print master. Returns {passed, problems, warnings, measurements}.

    has_alpha        no alpha at all prints as a solid rectangle
    canvas           the agreed print canvas size
    corners_clear    a background rectangle survived the cut
    not_clipped      artwork running into the canvas edge has been cut off
    cut_out          at least `min_transparent_in_bbox` % clear inside the artwork's own box;
                     canvas padding around an uncut rectangle says nothing about the cut
    """
    m = alpha_report(image)
    problems, warnings = [], []

    if not m["has_alpha"]:
        problems.append("no alpha channel - this prints as a solid rectangle")
    if tuple(m["size"]) != tuple(canvas):
        problems.append(f"canvas is {m['size'][0]}x{m['size'][1]}, expected {canvas[0]}x{canvas[1]}")
    if m["bbox"] is None:
        problems.append("nothing visible on the canvas")
        return {"passed": False, "problems": problems, "warnings": warnings, "measurements": m}
    if not m["corners_clear"]:
        problems.append("corners are not transparent - a background rectangle survived")
    if m.get("touches_canvas_edge"):
        problems.append("artwork touches the canvas edge - part of it has been clipped")

    clear = m.get("transparent_in_bbox_pct", 0.0)
    if clear < min_transparent_in_bbox:
        finding = (f"only {clear}% of the artwork's own box is transparent - it is effectively a "
                   f"solid plate")
        if plate_exception is not None and plate_exception.applies_to(image):
            warnings.append(f"{finding}; allowed by plate exception: {plate_exception.reason}")
        else:
            if plate_exception is not None:
                warnings.append("a plate exception was supplied but it was granted for different "
                                "pixels, so it does not apply")
            problems.append(finding)

    return {"passed": not problems, "problems": problems, "warnings": warnings, "measurements": m}
