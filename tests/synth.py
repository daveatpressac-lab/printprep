"""Synthetic artwork for the tests. Drawn in code so the repository ships no real designs.

Shapes are drawn at 4x and box-downsampled, so edges are genuinely anti-aliased the way scanned or
generated artwork is - which is exactly where keying goes wrong.
"""
import numpy as np
from PIL import Image, ImageDraw

CREAM = (241, 233, 216)
INK = (22, 20, 19)
ROSE = (196, 124, 111)


def _aa(draw_fn, size, ground, scale=4):
    w, h = size
    big = Image.new("RGB", (w * scale, h * scale), ground)
    draw_fn(ImageDraw.Draw(big), scale)
    return big.resize((w, h), Image.BOX)


def with_grain(image, sd=4.0, seed=7):
    a = np.asarray(image).astype(np.float32)
    rng = np.random.default_rng(seed)
    a += rng.normal(0, sd, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def cat_on_paper(size=(400, 400), grain=4.0):
    """A dark body with two enclosed cream eyes and a cream hairline, plus a rose heart.

    The eyes and the hairline are the ground colour, enclosed - a colour key would delete them.
    The heart is an ink at a very different distance from the ground than the body is.
    """
    def draw(d, s):
        d.ellipse([120 * s, 120 * s, 300 * s, 360 * s], fill=INK)                 # body
        d.ellipse([160 * s, 170 * s, 195 * s, 205 * s], fill=CREAM)               # left eye
        d.ellipse([225 * s, 170 * s, 260 * s, 205 * s], fill=CREAM)               # right eye
        d.line([170 * s, 250 * s, 250 * s, 330 * s], fill=CREAM, width=3 * s)     # hairline
        d.ellipse([30 * s, 40 * s, 90 * s, 100 * s], fill=ROSE)                   # heart-ish
    img = _aa(draw, size, CREAM)
    return with_grain(img, grain) if grain else img


def naive_blurred_key(image, tolerance=30, blur=1.2):
    """The approach printprep replaces: hard connectivity mask, gaussian-blurred, unmultiplied."""
    from scipy import ndimage
    from printprep.key import estimate_ground
    a = np.asarray(image.convert("RGB")).astype(np.float32)
    g = estimate_ground(a)
    d = np.abs(a - g).max(axis=-1)
    near = d <= tolerance
    lbl, _ = ndimage.label(near)
    edge = np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])
    outside = np.isin(lbl, np.unique(edge[edge > 0]))
    alpha = ndimage.gaussian_filter(np.where(outside, 0.0, 255.0), blur)
    rgb = a.copy()
    part = (alpha > 0) & (alpha < 255)
    f = (alpha[part] / 255.0)[:, None]
    rgb[part] = np.clip((rgb[part] - g * (1 - f)) / np.maximum(f, 0.05), 0, 255)
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def tilted_plate(size=(500, 640), angle=1.5, ground=(40, 38, 36)):
    """A light rectangular panel, slightly rotated, with ragged edges, on a dark textured wall."""
    w, h = size
    panel = Image.new("RGB", (360, 480), (205, 196, 180))
    pd = ImageDraw.Draw(panel)
    pd.rectangle([40, 40, 320, 300], fill=(30, 50, 120))                 # dark window inside
    pd.rectangle([60, 360, 300, 420], fill=(160, 150, 138))              # a carved-looking band
    rng = np.random.default_rng(3)
    pa = np.asarray(panel).astype(np.float32)
    for side in range(4):                                                # nibble the edges
        n = rng.integers(0, 3, size=pa.shape[0] if side < 2 else pa.shape[1])
        for i, k in enumerate(n):
            if side == 0: pa[i, :k] = ground
            if side == 1: pa[i, pa.shape[1] - k:] = ground
            if side == 2: pa[:k, i] = ground
            if side == 3: pa[pa.shape[0] - k:, i] = ground
    panel = Image.fromarray(pa.astype(np.uint8), "RGB").convert("RGBA").rotate(
        angle, expand=True, resample=Image.BICUBIC)
    wall = with_grain(Image.new("RGB", size, ground), sd=3.0, seed=11).convert("RGBA")
    ox, oy = (w - panel.width) // 2, (h - panel.height) // 2
    wall.alpha_composite(panel, (ox, oy))
    return wall.convert("RGB"), (ox, oy, panel.width, panel.height)


def flat_graphic(size=(300, 300)):
    def draw(d, s):
        d.rectangle([0, 0, 300 * s, 300 * s], fill=(250, 250, 250))
        d.ellipse([40 * s, 40 * s, 260 * s, 260 * s], fill=(20, 20, 20))
        d.rectangle([120 * s, 20 * s, 180 * s, 280 * s], fill=(210, 60, 60))
    return _aa(draw, size, (250, 250, 250))


def tonal_photo(size=(300, 300), seed=5):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size[1], 0:size[0]].astype(np.float32)
    base = 127 + 90 * np.sin(x / 23.0) * np.cos(y / 31.0)
    base += rng.normal(0, 22, base.shape)
    a = np.clip(np.stack([base, base * 0.95, base * 0.9], -1), 0, 255).astype(np.uint8)
    return Image.fromarray(a, "RGB")


def as_16bit_grey(image):
    """The same artwork as a 16-bit greyscale PIL image (mode I;16), as a scan or TIFF arrives.

    Pillow's own `convert("RGB")` saturates this to a blank white page, which is exactly the
    silent failure `_img` exists to prevent.
    """
    grey = np.asarray(image.convert("L")).astype(np.uint16) * 257
    return Image.fromarray(grey)


def ring(size=(200, 200), gap=False):
    """A filled ring. Its middle is ground colour: enclosed when closed, reachable when gapped.

    The gapped version is the case connectivity is supposed to get RIGHT by removing the middle -
    ground that a hairline opening connects to the outside world really is background.
    """
    def draw(d, s):
        d.ellipse([40 * s, 40 * s, 160 * s, 160 * s], fill=INK)
        d.ellipse([70 * s, 70 * s, 130 * s, 130 * s], fill=CREAM)
        if gap:
            d.rectangle([95 * s, 30 * s, 105 * s, 100 * s], fill=CREAM)
    return _aa(draw, size, CREAM)


def pale_on_cream(size=(300, 300), grain=3.0):
    """A pale ink barely distinguishable from the paper - the hardest case for any keyer."""
    def draw(d, s):
        d.ellipse([40 * s, 40 * s, 260 * s, 260 * s], fill=(228, 214, 188))
    return with_grain(_aa(draw, size, CREAM), grain)


def strip(size, grain=0.0):
    """A block of ink on ground, at whatever extreme aspect ratio is asked for."""
    w, h = size

    def draw(d, s):
        d.rectangle([w * s // 4, h * s // 4, w * s * 3 // 4, h * s * 3 // 4], fill=INK)
    img = _aa(draw, size, CREAM)
    return with_grain(img, grain) if grain else img
