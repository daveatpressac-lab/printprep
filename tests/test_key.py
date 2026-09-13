import unittest

import numpy as np
from scipy import ndimage

import synth
from printprep import halo, key_ground, measure_grain


class TestKeyGround(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = synth.cat_on_paper()
        cls.res = key_ground(cls.src)
        cls.a = np.asarray(cls.res.image).astype(np.float32)

    def test_the_outside_ground_is_transparent(self):
        al = self.a[..., 3]
        for y, x in ((0, 0), (0, -1), (-1, 0), (-1, -1), (390, 10), (200, 380)):
            self.assertEqual(al[y, x], 0, f"ground at ({x},{y}) survived")

    def test_enclosed_ground_colour_is_kept_as_ink(self):
        """The eyes are the ground colour. A colour key would delete them."""
        eye = self.a[187, 177]
        self.assertEqual(eye[3], 255)
        self.assertLess(np.abs(eye[:3] - synth.CREAM).max(), 25)
        hairline = self.a[290, 210]
        self.assertEqual(hairline[3], 255)
        self.assertGreater(self.res.stats["enclosed_ground_kept_px"], 1500)

    def test_seams_inside_the_artwork_never_turn_semi_transparent(self):
        """A black body meeting a cream eye is two inks touching, not an edge to the shirt."""
        al = self.a[..., 3]
        body = np.zeros(al.shape, bool)
        yy, xx = np.mgrid[0:al.shape[0], 0:al.shape[1]]
        body[((xx - 210) / 90.0) ** 2 + ((yy - 240) / 120.0) ** 2 <= 0.8] = True
        self.assertEqual(al[body].min(), 255, "a pixel inside the body went see-through")

    def test_a_second_ink_at_a_different_distance_is_kept_whole(self):
        heart_centre = self.a[70, 60]
        self.assertEqual(heart_centre[3], 255)
        self.assertLess(np.abs(heart_centre[:3] - synth.ROSE).max(), 20)

    def test_grain_specks_in_open_ground_stay_transparent(self):
        """A speck measured against itself would call itself fully covered."""
        al = self.a[..., 3]
        solid = al > 8
        lbl, n = ndimage.label(solid)
        sizes = ndimage.sum(solid, lbl, range(1, n + 1))
        self.assertEqual(int((sizes < 20).sum()), 0, "isolated opaque flecks in the ground")

    def test_no_pale_halo_on_a_dark_garment(self):
        h = halo(self.res.image)
        self.assertLess(h["ring_1px_lum"] - h["ground_lum"], 15, h)

    def test_it_beats_the_blurred_mask_it_replaces(self):
        ours = halo(self.res.image)["ring_1px_lum"]
        naive = halo(synth.naive_blurred_key(self.src))["ring_1px_lum"]
        self.assertGreater(naive - ours, 20, f"naive {naive} vs printprep {ours}")

    def test_grain_must_sit_below_tolerance(self):
        with self.assertRaises(ValueError):
            key_ground(self.src, tolerance=20, grain=24)


class TestMeasureGrain(unittest.TestCase):
    def test_it_reports_the_grounds_own_spread(self):
        m = measure_grain(synth.cat_on_paper(grain=4.0))
        self.assertLess(m["p50"], 8)
        self.assertLess(m["p99_9"], 24, "default grain would read texture as ink")
        self.assertGreater(m["pixels"], 10000)


if __name__ == "__main__":
    unittest.main()
