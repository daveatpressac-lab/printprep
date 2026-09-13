import unittest

import numpy as np
from PIL import Image

import synth
from printprep import choose_enlargement, midpoint_threshold, region_luminance, sample_ink


class TestRoute(unittest.TestCase):
    def test_large_flat_shapes_may_be_traced(self):
        r = choose_enlargement(synth.flat_graphic())
        self.assertEqual(r["route"], "vector", r)
        self.assertIn("verify", r["confidence"])

    def test_continuous_tone_is_resampled(self):
        self.assertEqual(choose_enlargement(synth.tonal_photo())["route"], "raster")

    def test_marking_it_texture_dependent_vetoes_tracing(self):
        r = choose_enlargement(synth.flat_graphic(), texture_dependent=True)
        self.assertEqual(r["route"], "raster")
        self.assertEqual(r["confidence"], "vetoed")


class TestInk(unittest.TestCase):
    def _rgba(self, colour):
        a = np.zeros((100, 100, 4), np.uint8)
        a[20:80, 20:80] = colour + (255,)
        a[45:55, 45:55] = (128, 128, 128, 255)     # a mid grey that belongs to neither
        return Image.fromarray(a, "RGBA")

    def test_a_dark_design_gives_its_dark_ink(self):
        self.assertLess(max(sample_ink(self._rgba((25, 20, 18)))), 40)

    def test_a_light_design_gives_its_light_ink_not_its_darkest_grey(self):
        self.assertGreater(min(sample_ink(self._rgba((246, 235, 217)))), 200)


class TestMeasure(unittest.TestCase):
    def setUp(self):
        a = np.zeros((100, 200, 3), np.uint8)
        a[:, :100] = 40          # background
        a[:, 100:] = 80          # subject
        self.img = Image.fromarray(a, "RGB")

    def test_the_threshold_sits_between_the_two(self):
        r = midpoint_threshold(self.img, [(120, 10, 180, 90)], [(10, 10, 80, 90)])
        self.assertEqual(r["threshold"], 60.0)
        self.assertEqual(region_luminance(self.img, (120, 10, 180, 90)), 80.0)

    def test_overlapping_regions_are_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            midpoint_threshold(self.img, [(10, 10, 80, 90)], [(120, 10, 180, 90)])


if __name__ == "__main__":
    unittest.main()
