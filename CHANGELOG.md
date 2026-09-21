# Changelog

All notable changes to printprep are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-09-21

First release, extracted from a working print-on-demand design pipeline and re-implemented as a
standalone package. Not published to PyPI.

### Added

- `key_ground`: remove a plain background by connectivity, keeping enclosed ground colour, with
  alpha measured as ink coverage against the local ink and unmultiplied edges.
- `fit_quadrilateral`, `cut_plate`: cut straight-sided subjects by fitting a four-point outline.
- `fit_to_canvas`, `save_master`: one scale factor, centred, with aspect drift reported; 300 dpi.
- `check_master`, `alpha_report`, `halo`, `fidelity`: print-master QC measured on the alpha
  channel, with `PlateException` for deliberate rectangles bound to a pixel hash.
- `choose_enlargement`, `analyse`: advise vector trace or raster enlargement, raster by default.
- `sample_ink`: take lettering colour from the artwork, branching for light-ink designs.
- `midpoint_threshold`, `region_luminance`: choose thresholds by measurement, refuse overlaps.
- Command line: `printprep key | plate | fit | qc | halo | route | grain`, with `--version`,
  measurements as JSON on stdout, warnings on stderr, and exit codes 0 done / 1 `qc` failed /
  2 could not be carried out.
- Refusals for inputs that cannot be handled correctly: artwork that is already cut out handed
  back to `key_ground`, a `margin` above 1, a canvas smaller than 1x1, a destination that cannot
  hold transparency, and an integer array whose range printprep cannot know.
- Two command-line diagnostics for the commonest mistake: a key that kept almost nothing, or
  removed almost nothing, now says which, and what to do about it.
- 88 unit tests on artwork drawn in code, run on Linux, Windows and macOS against Python 3.9,
  3.12 and 3.13. CI also builds the wheel and sdist, checks them with `twine check --strict`,
  installs the wheel into a clean environment and runs the sdist's own test suite against it.
- `CONTRIBUTING.md`, `SECURITY.md`, `ROADMAP.md`, issue and pull request templates.

### Fixed

Everything below was found and fixed while preparing this first release, so no published version
ever carried these:

- High-bit-depth greyscale sources (16-bit PNG and TIFF, Pillow modes `I` and `I;16`) were
  saturated to a blank white page by Pillow's own `convert("RGB")`. The ground was then measured
  as pure white and the whole image keyed away, silently. They are now rescaled on the way in.
- `aspect_drift` was one aspect ratio subtracted from another, which no single threshold can
  read: a 4000 x 20 strip distorted by 0.7% scored 1.43, and a 20 x 4000 strip distorted by 1.5%
  scored 0.000075. It is now the fractional change in the aspect ratio.
- `measure_grain` returned a dict without `p50`/`p99`/`p99_9`/`max` when no ground reached the
  image border, which is what happens when a `ground` colour from another image is passed in.
  The keys are now always present, empty when nothing was measured.
- The sdist shipped `tests/test_*.py` but not `tests/synth.py`, which they all import, so the
  published test suite could not be run.
- The command line raised Python tracebacks for a missing file, a missing destination folder, or
  a destination that cannot hold alpha - the last only after the whole key had been computed.

[Unreleased]: https://github.com/daveatpressac-lab/printprep/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/daveatpressac-lab/printprep/releases/tag/v0.1.0
