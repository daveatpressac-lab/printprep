"""The conversion layer: every source has to arrive as 8-bit-ranged float, or nothing downstream
measures what it thinks it is measuring."""
import unittest

import numpy as np
from PIL import Image

import synth
from printprep import key_ground, measure_grain
from printprep._img import has_alpha, to_rgb_array, to_rgba_array


class TestHighBitDepth(unittest.TestCase):
    """Pillow loads 16-bit grey as mode I;16 and saturates it to white on convert()."""

    def test_pillow_alone_would_lose_the_artwork(self):
        """The bug this guards against, asserted on Pillow itself so it cannot drift silently."""
        src = synth.as_16bit_grey(synth.cat_on_paper())
        self.assertEqual(src.mode, "I;16")
        naive = np.asarray(src.convert("RGB"))
        self.assertEqual(naive.min(), 255, "Pillow no longer saturates - revisit _img")

    def test_16bit_grey_is_rescaled_not_saturated(self):
        a = to_rgb_array(synth.as_16bit_grey(synth.cat_on_paper()))
        self.assertEqual(a.shape[-1], 3)
        self.assertLess(a.min(), 40, "the dark ink survived the conversion")
        self.assertGreater(a.max(), 200, "the cream ground survived the conversion")

    def test_16bit_grey_keys_like_its_8bit_twin(self):
        src = synth.cat_on_paper()
        eight = key_ground(src.convert("L").convert("RGB"))
        sixteen = key_ground(synth.as_16bit_grey(src))
        self.assertAlmostEqual(sixteen.stats["transparent_pct"],
                               eight.stats["transparent_pct"], delta=1.0)
        self.assertGreater(sixteen.stats["enclosed_ground_kept_px"], 1500,
                           "the eyes were lost on the way in")

    def test_grain_is_measured_on_real_values_not_a_blank_page(self):
        m = measure_grain(synth.as_16bit_grey(synth.cat_on_paper()))
        self.assertLess(max(m["ground"]), 250, "the ground read as pure white")
        self.assertGreater(m["p99_9"], 0.0, "a blank page has no grain to measure")

    def test_16bit_grey_gets_an_opaque_alpha_channel(self):
        a = to_rgba_array(synth.as_16bit_grey(synth.cat_on_paper()))
        self.assertEqual(a.shape[-1], 4)
        self.assertEqual(a[..., 3].min(), 255)


class TestArrayInputs(unittest.TestCase):
    def test_uint16_arrays_are_rescaled(self):
        a = to_rgb_array(np.full((4, 4, 3), 65535, np.uint16))
        self.assertAlmostEqual(float(a.max()), 255.0, delta=0.01)

    def test_a_wide_integer_array_is_refused_rather_than_misread(self):
        """int32 holding 16-bit values has no declared range. Guessing puts every threshold wrong."""
        with self.assertRaises(ValueError) as e:
            to_rgb_array(np.full((4, 4, 3), 4000, np.int32))
        self.assertIn("not 8-bit", str(e.exception))

    def test_an_8bit_ranged_integer_array_still_works(self):
        self.assertEqual(float(to_rgb_array(np.full((4, 4, 3), 200, np.int32)).max()), 200.0)

    def test_float_arrays_round_trip_unchanged(self):
        """to_rgb_array hands back 0..255 float, so feeding that straight back must be identity."""
        once = to_rgb_array(synth.cat_on_paper())
        np.testing.assert_array_equal(to_rgb_array(once), once)

    def test_a_greyscale_array_becomes_three_channels(self):
        self.assertEqual(to_rgb_array(np.zeros((5, 6), np.uint8)).shape, (5, 6, 3))


class TestHasAlpha(unittest.TestCase):
    def test_rgb_has_none_and_rgba_has_one(self):
        self.assertFalse(has_alpha(Image.new("RGB", (4, 4))))
        self.assertTrue(has_alpha(Image.new("RGBA", (4, 4))))

    def test_a_palette_images_transparency_counts(self):
        p = Image.new("P", (4, 4))
        self.assertFalse(has_alpha(p))
        p.info["transparency"] = 0
        self.assertTrue(has_alpha(p))

    def test_arrays_are_judged_by_their_channel_count(self):
        self.assertFalse(has_alpha(np.zeros((4, 4, 3), np.uint8)))
        self.assertTrue(has_alpha(np.zeros((4, 4, 4), np.uint8)))


if __name__ == "__main__":
    unittest.main()
