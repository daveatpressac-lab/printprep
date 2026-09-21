"""What printprep refuses.

Every case here used to return a plausible-looking image that was wrong: a fully transparent
master, artwork scaled off the edge of the canvas, a threshold measured on paint that was never
printed. A loud refusal is worth more than a quiet bad print file.
"""
import unittest

import numpy as np
from PIL import Image

import synth
from printprep import fidelity, fit_to_canvas, key_ground, region_luminance


class TestKeyGroundRefusals(unittest.TestCase):
    def test_artwork_that_is_already_cut_out_is_refused(self):
        """The RGB under a transparent pixel is undefined, so keying it again measures nothing."""
        cut = key_ground(synth.cat_on_paper()).image
        with self.assertRaises(ValueError) as e:
            key_ground(cut)
        self.assertIn("already cut out", str(e.exception))

    def test_an_rgba_image_that_is_merely_opaque_is_still_accepted(self):
        """Having an alpha channel is not the same as being cut out."""
        opaque = synth.cat_on_paper().convert("RGBA")
        self.assertGreater(key_ground(opaque).stats["transparent_pct"], 50)

    def test_a_few_stray_transparent_pixels_do_not_trip_the_refusal(self):
        a = np.dstack([np.asarray(synth.cat_on_paper()),
                       np.full((400, 400), 255, np.uint8)])
        a[:10, :10, 3] = 0                       # 0.06% of the image
        key_ground(Image.fromarray(a, "RGBA"))   # must not raise

    def test_a_tolerance_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            key_ground(synth.cat_on_paper(), tolerance=0, grain=0)

    def test_negative_grain_is_refused(self):
        with self.assertRaises(ValueError):
            key_ground(synth.cat_on_paper(), grain=-5)

    def test_a_window_of_zero_pixels_is_refused(self):
        with self.assertRaises(ValueError):
            key_ground(synth.cat_on_paper(), window=0)


class TestFitRefusals(unittest.TestCase):
    def _art(self):
        a = np.zeros((80, 60, 4), np.uint8)
        a[10:70, 10:50] = (200, 40, 40, 255)
        return Image.fromarray(a, "RGBA")

    def test_a_margin_above_one_is_refused_instead_of_cropping_the_artwork(self):
        """It used to scale the artwork past the canvas and silently shear off the overhang."""
        with self.assertRaises(ValueError) as e:
            fit_to_canvas(self._art(), canvas=(100, 100), margin=1.5)
        self.assertIn("margin", str(e.exception))

    def test_a_margin_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            fit_to_canvas(self._art(), canvas=(100, 100), margin=0)

    def test_an_empty_canvas_is_refused_instead_of_returning_a_0x0_master(self):
        with self.assertRaises(ValueError) as e:
            fit_to_canvas(self._art(), canvas=(0, 0))
        self.assertIn("1x1", str(e.exception))

    def test_a_margin_of_exactly_one_is_allowed(self):
        r = fit_to_canvas(self._art(), canvas=(120, 120), margin=1.0)
        self.assertEqual(max(r.placed), 120)


class TestMessagesNameTheProblem(unittest.TestCase):
    def test_a_reversed_region_says_so(self):
        with self.assertRaises(ValueError) as e:
            region_luminance(synth.cat_on_paper(), (300, 300, 100, 100))
        self.assertIn("no area", str(e.exception))

    def test_a_region_off_the_image_says_so(self):
        with self.assertRaises(ValueError) as e:
            region_luminance(synth.cat_on_paper(), (0, 0, 9000, 9000))
        self.assertIn("outside", str(e.exception))

    def test_fidelity_names_which_of_the_two_images_was_blank(self):
        blank = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        cut = key_ground(synth.cat_on_paper()).image
        with self.assertRaises(ValueError) as e:
            fidelity(blank, cut)
        self.assertIn("result", str(e.exception))
        with self.assertRaises(ValueError) as e:
            fidelity(cut, blank)
        self.assertIn("source", str(e.exception))


if __name__ == "__main__":
    unittest.main()
