## What this changes, and why

<!-- What went wrong, or what was missing. For this library the "why" is usually a specific way
     artwork prints badly - say which. -->

## How it was measured

<!-- printprep is built on measurements rather than eyeballing, so where possible: the numbers
     before, the numbers after. halo(), alpha_report() and fidelity() all print something. -->

## Checklist

- [ ] `python -m unittest discover -s tests -v` passes
- [ ] There is a test that fails without this change
- [ ] Any new test artwork is drawn in code in `tests/synth.py`, not committed as an image
- [ ] The reasoning is in the code, not only in this description
- [ ] `CHANGELOG.md` updated under `## [Unreleased]` if the behaviour changed
