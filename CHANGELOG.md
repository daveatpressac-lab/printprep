# Changelog

## 0.1.0 (unreleased)

First standalone release, extracted from a working print-on-demand design pipeline.

- `key_ground`: remove a plain background by connectivity, keeping enclosed ground colour, with
  alpha measured as ink coverage against the local ink and unmultiplied edges.
- `fit_quadrilateral`, `cut_plate`: cut straight-sided subjects by fitting a four-point outline.
- `fit_to_canvas`, `save_master`: one scale factor, centred, with aspect drift reported; 300 dpi.
- `check_master`, `alpha_report`, `halo`, `fidelity`: print-master QC measured on the alpha
  channel, with `PlateException` for deliberate rectangles bound to a pixel hash.
- `choose_enlargement`, `analyse`: advise vector trace or raster enlargement, raster by default.
- `sample_ink`: take lettering colour from the artwork, branching for light-ink designs.
- `midpoint_threshold`, `region_luminance`: choose thresholds by measurement, refuse overlaps.
- Command line: `printprep key | plate | fit | qc | halo | route | grain`.
