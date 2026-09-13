import os
import tempfile
import unittest

import numpy as np
from PIL import Image

import synth
from printprep import cut_plate, fit_quadrilateral, fit_to_canvas, save_master


class TestPlate(unittest.TestCase):
    def test_a_ragged_tilted_panel_fits_to_four_corners(self):
        img, (ox, oy, pw, ph) = synth.tilted_plate()
        poly = fit_quadrilateral(img, tolerance=45)
        self.assertEqual(len(poly), 4, poly)
        xs, ys = poly[:, 0], poly[:, 1]
        self.assertLess(abs(xs.min() - ox), 8)
        self.assertLess(abs(ys.min() - oy), 8)
        self.assertLess(abs(xs.max() - (ox + pw)), 8)
        self.assertLess(abs(ys.max() - (oy + ph)), 8)

    def test_the_cut_keeps_the_dark_window_inside_the_panel(self):
        """The window is as dark as the wall. Fitting the shape keeps it; a threshold would not."""
        img, _ = synth.tilted_plate()
        a = np.asarray(cut_plate(img, tolerance=45))
        self.assertEqual(a[320, 250, 3], 255)      # inside the dark window
        self.assertEqual(a[5, 5, 3], 0)             # the wall
        edge = a[..., 3]
        self.assertTrue(((edge > 0) & (edge < 255)).any(), "the cut edge is not anti-aliased")

    def test_no_subject_is_a_clear_error(self):
        with self.assertRaises(ValueError):
            fit_quadrilateral(Image.new("RGB", (50, 50), (10, 10, 10)), tolerance=45)


class TestFit(unittest.TestCase):
    def _art(self, w, h):
        a = np.zeros((h + 40, w + 40, 4), np.uint8)
        a[20:20 + h, 20:20 + w] = (200, 40, 40, 255)
        return Image.fromarray(a, "RGBA")

    def test_it_never_stretches(self):
        for w, h in ((300, 900), (900, 300), (500, 500), (613, 431)):
            r = fit_to_canvas(self._art(w, h))
            self.assertEqual(r.image.size, (4500, 5400))
            self.assertLess(r.aspect_drift, 0.005, (w, h, r))

    def test_it_respects_the_margin_and_centres(self):
        r = fit_to_canvas(self._art(1000, 1000), margin=0.9)
        self.assertEqual(r.placed, (4050, 4050))
        self.assertEqual(r.offset, ((4500 - 4050) // 2, (5400 - 4050) // 2))

    def test_empty_artwork_is_refused(self):
        with self.assertRaises(ValueError):
            fit_to_canvas(Image.new("RGBA", (40, 40), (0, 0, 0, 0)))

    def test_the_master_is_saved_with_a_dpi_tag_and_alpha(self):
        r = fit_to_canvas(self._art(100, 120), canvas=(900, 1080))
        path = os.path.join(tempfile.mkdtemp(), "m.png")
        save_master(r.image, path)
        back = Image.open(path)
        self.assertEqual(back.mode, "RGBA")
        self.assertAlmostEqual(back.info["dpi"][0], 300, delta=0.5)


if __name__ == "__main__":
    unittest.main()
