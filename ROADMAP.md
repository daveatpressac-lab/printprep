# Roadmap

Where printprep is likely to go next. These are intentions, not commitments: it is a one-person
project and the order will change as real artwork breaks things. Anything here is open to a pull
request.

## Known limits worth closing

- **Pale ink on pale paper.** Ink close to the ground colour gives the coverage estimate very
  little to work with, and the edge still fringes: on the test case, a 1px ring at L103 against an
  L59 garment. It beats the alternatives and is pinned by a test, but it is not clean. Likely
  direction: estimate coverage from a colour axis chosen per design rather than from a channel-max
  distance.
- **Busy and shadowed backgrounds.** `key_ground` needs a roughly uniform ground, and today the
  answer is "build the mask yourself and use `cut_plate(mask=...)`". A gradient-tolerant ground
  model would cover the common case of a scan with uneven lighting.
- **Memory on full-size plates.** `cut_plate` renders its polygon at 4x to anti-alias the edge, so
  a 4500 x 5400 plate needs roughly 400 MB for that one step. Rasterising in bands would remove
  that ceiling.

## Diagnostics

- A `printprep explain` that runs the measurements a design needs and says, in words, which
  settings suit it — today that is three commands and some judgement.
- Optional side-by-side proof sheets from the library, of the kind `examples/halo_demo.py`
  produces, so a failing case can be attached to an issue without sharing the artwork.

## Workflow

- A batch mode: a folder in, masters and a QC report out, with one non-zero exit if any failed.
- Canvas presets for the common print areas, so `--canvas 4500x5400` need not be remembered.
- A documented way to plug in a mask from another tool at each stage, rather than only in
  `cut_plate`.

## Testing and packaging

- Property-based tests over image shape, bit depth and ground colour, to replace some of the
  hand-picked cases.
- Coverage measured and reported, rather than assumed from the test count.
- A PyPI release, so `pip install printprep` works. See [CHANGELOG.md](CHANGELOG.md) for where
  that stands.

## Once there are outside users

Deliberately empty for now. Real reports about real artwork should set most of the priorities
above, and inventing them in advance is how a small library grows features nobody needs. If
printprep broke on your artwork, that belongs in an
[issue](https://github.com/daveatpressac-lab/printprep/issues) and probably belongs on this list.
