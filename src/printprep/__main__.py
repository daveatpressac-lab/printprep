"""Command line: printprep <command> ...  (or python -m printprep <command> ...)

    key    in.png out.png      cut a plain ground away, keeping enclosed ground colour
    plate  in.png out.png      cut a straight-sided subject by fitting its outline
    fit    in.png out.png      place on the print canvas at one scale, 300 dpi
    qc     master.png          gate a print master
    halo   cutout.png          measure edge fringing on a dark garment colour
    route  art.png             advise vector trace or raster enlargement
    grain  in.png              measure the ground's own texture, to choose --grain

Every command prints its measurements as JSON on stdout, so it can be piped into jq or read back
with json.loads. Anything the operator needs to notice goes to stderr, where it will not corrupt
that JSON.

Exit codes:

    0   done
    1   `qc` ran and the master failed its gates
    2   the command could not be carried out - the reason is on stderr
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from . import (__version__, check_master, choose_enlargement, cut_plate, fit_to_canvas, halo,
               key_ground, measure_grain, save_master)

#: Formats that can carry an alpha channel. Cut-out artwork saved anywhere else loses its cut.
ALPHA_FORMATS = (".png", ".tga", ".tif", ".tiff", ".webp")


def _size(s):
    try:
        w, h = (int(part) for part in s.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected WIDTHxHEIGHT, such as 4500x5400, not {s!r}")
    if w < 1 or h < 1:
        raise argparse.ArgumentTypeError(f"both sides must be at least 1 pixel, not {w}x{h}")
    return w, h


def _warn(message: str) -> None:
    print(f"printprep: {message}", file=sys.stderr)


def _check_destination(dest) -> None:
    """Refuse a destination that cannot hold the result, before doing the work rather than after."""
    p = Path(dest)
    if p.suffix.lower() not in ALPHA_FORMATS:
        raise ValueError(
            f"{p.name or dest} cannot hold transparency, so the cut would be thrown away on "
            f"save. Use one of {', '.join(ALPHA_FORMATS)} - PNG is the usual choice for a print "
            f"master.")
    if p.parent and not p.parent.exists():
        raise ValueError(f"the folder {p.parent} does not exist")


def _open(src):
    p = Path(src)
    if not p.exists():
        raise ValueError(f"no such file: {src}")
    if p.is_dir():
        raise ValueError(f"{src} is a folder, not an image")
    try:
        return Image.open(p)
    except OSError as e:
        raise ValueError(f"{src} could not be read as an image ({e})")


def _comment_on_the_key(stats: dict) -> None:
    """A key that removed everything, or nothing, is nearly always a wrong ground colour."""
    clear = stats["transparent_pct"]
    if clear > 99.0:
        _warn("almost nothing was kept. The ground colour is estimated from the image border, so "
              "this usually means the artwork runs to the edge. Crop a margin of plain ground "
              "around it, or pass the ground colour yourself with the Python API.")
    elif clear < 1.0:
        _warn("almost nothing was removed. The ground may not be plain, or --tolerance may be too "
              "low for it. Run `printprep grain` on the same file to measure it.")


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="printprep", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"printprep {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="command")

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
    f.add_argument("--canvas", type=_size, default=(4500, 5400), metavar="WxH")
    f.add_argument("--margin", type=float, default=0.94)
    f.add_argument("--dpi", type=int, default=300)

    q = sub.add_parser("qc", help="gate a print master")
    q.add_argument("src")
    q.add_argument("--canvas", type=_size, default=(4500, 5400), metavar="WxH")

    h = sub.add_parser("halo", help="measure edge fringing")
    h.add_argument("src")

    r = sub.add_parser("route", help="vector or raster enlargement")
    r.add_argument("src")
    r.add_argument("--texture-dependent", action="store_true")

    g = sub.add_parser("grain", help="measure the ground's texture")
    g.add_argument("src")
    return ap


def _run(argv) -> int:
    a = _build_parser().parse_args(argv)
    if a.cmd in ("key", "plate", "fit"):
        _check_destination(a.dest)
    im = _open(a.src)

    if a.cmd == "key":
        res = key_ground(im, tolerance=a.tolerance, grain=a.grain, window=a.window,
                         edge_width=a.edge_width)
        res.image.save(a.dest)
        out = res.stats
        _comment_on_the_key(out)
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


def main(argv=None) -> int:
    """Run one command. Returns the exit code rather than raising at the operator."""
    try:
        return _run(argv)
    except (ValueError, OSError) as e:
        _warn(str(e))
        return 2
    except KeyboardInterrupt:
        _warn("interrupted")
        return 2


if __name__ == "__main__":
    sys.exit(main())
