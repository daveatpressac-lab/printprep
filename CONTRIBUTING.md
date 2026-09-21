# Contributing to printprep

Thanks for looking. This is a small, early project, so the bar for a useful contribution is low:
a failing case is worth as much as a fix.

## Getting set up

```bash
git clone https://github.com/daveatpressac-lab/printprep
cd printprep
python -m venv .venv
pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

Python 3.9 or newer. The dependencies are numpy, scipy, opencv-python-headless and Pillow;
`[dev]` adds `build` and `twine` for checking the package.

To regenerate the figure in the README:

```bash
python examples/halo_demo.py
```

## Reporting a problem

Open an [issue](https://github.com/daveatpressac-lab/printprep/issues). The most useful report is
one that can be reproduced without your artwork:

- a small image drawn in code, in the style of `tests/synth.py`, that shows the failure, **or**
- a description of the artwork - what the ground colour is, roughly what the design is, whether
  the background colour also appears inside the design - and what came out instead

Please include the printprep version (`printprep --version`), your Python version, and the exact
command or call. If a command failed, the line it printed is usually enough; printprep tries not
to raise tracebacks at people.

You do not need to send artwork you would rather not share. A description of the shape of the
problem is genuinely useful.

## How the tests are laid out

All the test artwork is **drawn in code**, in `tests/synth.py`, so the repository ships no real
designs and every number in the suite is reproducible on any machine. Please keep it that way:
a new test case should add a shape to `synth.py` rather than commit a PNG.

| file | what it covers |
|---|---|
| `tests/test_key.py` | keying by connectivity: holes, halos, seams, grain specks |
| `tests/test_plate_fit.py` | quadrilateral fitting, and placing artwork on the canvas |
| `tests/test_qc.py` | alpha measurement, the master gates, plate exceptions, fidelity |
| `tests/test_route_ink_measure.py` | enlargement advice, ink sampling, thresholds |
| `tests/test_img.py` | the conversion layer: bit depth, channel counts, alpha detection |
| `tests/test_validation.py` | what printprep refuses, and why |
| `tests/test_edges.py` | enclosed detail, pale ink, extreme shapes, indexed sources |
| `tests/test_cli.py` | the command line end to end, including its exit codes |

The suite is plain `unittest`, with no plugins, so it runs anywhere Python does.

## What makes a good pull request

- **A test that fails before your change and passes after it.** For this library that usually
  means a new shape in `synth.py` and an assertion on a measurement, not on a screenshot.
- **Measure, don't assume.** Nearly every rule here exists because something looked fine and
  printed badly. If a change improves an edge, say by how much - `halo()` will tell you.
- **Say why in the code.** The modules carry long docstrings explaining what was tried and why it
  was rejected. That is deliberate: the reasoning is the valuable part. New behaviour should come
  with the same.
- **Keep the refusals loud.** If an input cannot be handled correctly, raising with a message that
  says what to do next is better than returning something plausible.
- One change per pull request, please, with a commit message that says what changed and why.

## Style

No linter is enforced. Match what is there: about 100 columns, standard library imports first,
plain functions over classes, docstrings that explain the reasoning rather than restate the
signature.

## Licence

By contributing you agree that your contribution is licensed under the MIT Licence, the same as
the rest of the project.
