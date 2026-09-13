"""Command line: python -m printprep <command> ...

    key    in.png out.png      cut a plain ground away, keeping enclosed ground colour
    plate  in.png out.png      cut a straight-sided subject by fitting its outline
    fit    in.png out.png      place on the print canvas at one scale, 300 dpi
    qc     master.png          gate a print master
    halo   cutout.png          measure edge fringing on a dark garment colour
    route  art.png             advise vector trace or raster enlargement
    grain  in.png              measure the ground's own texture, to choose --grain
"""
from __future__ import annotations

import argparse
import json
import sys

from PIL import Image

from . import (check_master, choose_enlargement, cut_plate, fit_to_canvas, halo, key_ground,
               measure_grain, save_master)


def _size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="printprep", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("key", help="cut a plain ground away")
    k.add_argument("src"); k.add_argument("dest")
    k.add_argument("--tolerance", type=float, default=30)
    k.add_argument("--grain", type=float, default=24)
    k.add_argument("--window", type=int, default=15)
    k.add_argument("--edge-width", type=int, default=4)

    p = sub.add_parser("plate", help="cut a straight-sided subject")
    p.add_argument("src"); p.add_argument("dest")
    p.add_argument("--tolerance", type=float, default=45)
    p.add_argument("--close", type=int, default=25)

    f = sub.add_parser("fit", help="place on the print canvas")
    f.add_argument("src"); f.add_argument("dest")
    f.add_argument("--canvas", type=_size, default=(4500, 5400))
    f.add_argument("--margin", type=float, default=0.94)
    f.add_argument("--dpi", type=int, default=300)

    q = sub.add_parser("qc", help="gate a print master")
    q.add_argument("src")
    q.add_argument("--canvas", type=_size, default=(4500, 5400))

    h = sub.add_parser("halo", help="measure edge fringing")
    h.add_argument("src")

    r = sub.add_parser("route", help="vector or raster enlargement")
    r.add_argument("src")
    r.add_argument("--texture-dependent", action="store_true")

    g = sub.add_parser("grain", help="measure the ground's texture")
    g.add_argument("src")

    a = ap.parse_args(argv)
    im = Image.open(a.src)

    if a.cmd == "key":
        res = key_ground(im, tolerance=a.tolerance, grain=a.grain, window=a.window,
                         edge_width=a.edge_width)
        res.image.save(a.dest)
        out = res.stats
    elif a.cmd == "plate":
        cut_plate(im, tolerance=a.tolerance, close=a.close).save(a.dest)
        out = {"written": a.dest}
    elif a.cmd == "fit":
        res = fit_to_canvas(im, canvas=a.canvas, margin=a.margin)
        save_master(res.image, a.dest, dpi=a.dpi)
        out = {"scale": round(res.scale, 4), "placed": res.placed, "aspect_drift": res.aspect_drift}
    elif a.cmd == "qc":
        out = check_master(im, canvas=a.canvas)
    elif a.cmd == "halo":
        out = halo(im)
    elif a.cmd == "route":
        out = choose_enlargement(im, texture_dependent=a.texture_dependent)
    else:
        out = measure_grain(im)

    print(json.dumps(out, indent=1))
    return 1 if (a.cmd == "qc" and not out["passed"]) else 0


if __name__ == "__main__":
    sys.exit(main())
