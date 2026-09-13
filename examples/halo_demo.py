"""Three ways to cut artwork off cream paper, shown on a dark garment.

    python examples/halo_demo.py

Writes docs/halo_comparison.png and prints the measurements behind it. The artwork is drawn in
code, so every number here is reproducible on any machine.

  1. colour key      removes every cream pixel - including the eyes and the hairline
  2. blurred mask    keeps them, but the softened edge carries paper colour: a pale halo
  3. printprep       keeps them, and measures coverage so the edge takes the garment's colour
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from printprep import halo, key_ground                     # noqa: E402
from printprep.key import estimate_ground                  # noqa: E402

CREAM, INK, ROSE = (241, 233, 216), (22, 20, 19), (196, 124, 111)
DARK = (58, 58, 60)


def artwork(size=400, scale=4, grain=4.0):
    big = Image.new("RGB", (size * scale, size * scale), CREAM)
    d = ImageDraw.Draw(big)
    s = scale
    d.ellipse([120 * s, 120 * s, 300 * s, 360 * s], fill=INK)
    d.ellipse([160 * s, 170 * s, 195 * s, 205 * s], fill=CREAM)
    d.ellipse([225 * s, 170 * s, 260 * s, 205 * s], fill=CREAM)
    d.line([170 * s, 250 * s, 250 * s, 330 * s], fill=CREAM, width=3 * s)
    d.ellipse([30 * s, 40 * s, 90 * s, 100 * s], fill=ROSE)
    a = np.asarray(big.resize((size, size), Image.BOX)).astype(np.float32)
    a += np.random.default_rng(7).normal(0, grain, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def colour_key(img, tolerance=30):
    a = np.asarray(img).astype(np.float32)
    d = np.abs(a - estimate_ground(a)).max(axis=-1)
    alpha = np.where(d <= tolerance, 0, 255)
    return Image.fromarray(np.dstack([a, alpha]).astype(np.uint8), "RGBA")


def blurred_mask(img, tolerance=30, blur=1.2):
    a = np.asarray(img).astype(np.float32)
    g = estimate_ground(a)
    d = np.abs(a - g).max(axis=-1)
    lbl, _ = ndimage.label(d <= tolerance)
    edge = np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])
    outside = np.isin(lbl, np.unique(edge[edge > 0]))
    alpha = ndimage.gaussian_filter(np.where(outside, 0.0, 255.0), blur)
    rgb = a.copy()
    part = (alpha > 0) & (alpha < 255)
    f = (alpha[part] / 255.0)[:, None]
    rgb[part] = np.clip((rgb[part] - g * (1 - f)) / np.maximum(f, 0.05), 0, 255)
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def on(img, ground):
    bg = Image.new("RGB", img.size, ground)
    bg.paste(img, (0, 0), img)
    return bg


def main():
    src = artwork()
    cuts = [("1  colour key", colour_key(src)),
            ("2  blurred mask", blurred_mask(src)),
            ("3  printprep", key_ground(src).image)]

    rows = []
    print(f"{'method':18s} {'eyes kept':>9s} {'1px ring lum':>13s} {'garment lum':>12s}")
    for name, cut in cuts:
        a = np.asarray(cut)
        eyes = bool(a[187, 177, 3] == 255 and a[187, 242, 3] == 255)
        h = halo(cut, DARK)
        print(f"{name:18s} {str(eyes):>9s} {h['ring_1px_lum']:>13} {h['ground_lum']:>12}")
        whole = on(cut, DARK)
        zoom = whole.crop((140, 150, 280, 230)).resize((420, 240), Image.NEAREST)
        rows.append((name, whole, zoom, eyes, h))

    pad, lab = 16, 30
    w = sum(max(r[1].width, r[2].width) for r in rows) + pad * (len(rows) + 1)
    h = lab + rows[0][1].height + pad + rows[0][2].height + lab + pad
    sheet = Image.new("RGB", (w, h), (250, 249, 246))
    d = ImageDraw.Draw(sheet)
    x = pad
    for name, whole, zoom, eyes, hv in rows:
        col = max(whole.width, zoom.width)
        d.text((x, 8), name, fill=(30, 30, 30))
        sheet.paste(whole, (x + (col - whole.width) // 2, lab))
        y = lab + whole.height + pad
        sheet.paste(zoom, (x + (col - zoom.width) // 2, y))
        d.text((x, y + zoom.height + 6),
               f"eyes kept: {'yes' if eyes else 'NO'}   edge ring L{hv['ring_1px_lum']} "
               f"on garment L{hv['ground_lum']}", fill=(90, 90, 90))
        x += col + pad
    out = ROOT / "docs" / "halo_comparison.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
