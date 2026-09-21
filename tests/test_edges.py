"""Edge cases that come from real artwork rather than from the happy path.

Enclosed detail that is and is not really enclosed, ink that barely differs from the paper,
shapes far from square, and indexed PNGs - each of these has a specific way of going wrong.
"""
import unittest

import numpy as np
from PIL import Image

import synth
from printprep import (alpha_report, check_master, fit_to_canvas, halo, key_ground, measure_grain,
                       save_master)


class TestEnclosedDetail(unittest.TestCase):
    """Connectivity has to get this right in both directions, not just the flattering one."""

    def test_a_closed_ring_keeps_its_middle(self):
        r = key_ground(synth.ring(gap=False))
        self.assertEqual(np.asarray(r.image)[100, 100, 3], 255, "the enclosed middle went clear")
        self.assertGreater(r.stats["enclosed_ground_kept_px"], 2000)

    def test_a_hairline_gap_lets_the_middle_go(self):
        """Ground the outside can reach is background, however small the opening."""
        r = key_ground(synth.ring(gap=True))
        self.assertEqual(np.asarray(r.image)[100, 100, 3], 0, "the middle should drain out")
        self.assertEqual(r.stats["enclosed_ground_kept_px"], 0)


class TestPaleInkIsAKnownLimit(unittest.TestCase):
    """Ink close to the paper colour still fringes. Pinned so the limit is measured, not assumed."""

    def setUp(self):
        self.src = synth.pale_on_cream()
        self.cut = key_ground(self.src, tolerance=8, grain=5).image

    def test_it_still_beats_the_blurred_mask(self):
        ours = halo(self.cut)["ring_1px_lum"]
        naive = halo(synth.naive_blurred_key(self.src, tolerance=8))["ring_1px_lum"]
        self.assertGreater(naive - ours, 20, f"naive {naive} vs printprep {ours}")

    def test_but_the_fringe_is_real_and_is_not_claimed_away(self):
        """Documented in the README as a limit. If this starts passing, the README is out of date."""
        h = halo(self.cut)
        self.assertGreater(h["ring_1px_lum"] - h["ground_lum"], 15,
                           "pale ink now keys cleanly - update the README's known limits")


class TestUnusualDimensions(unittest.TestCase):
    def test_extreme_strips_key_without_falling_over(self):
        """A 15px local-ink window is wider than some of these images."""
        for size in ((2000, 20), (20, 2000), (400, 3), (3, 400), (17, 17), (1, 1)):
            with self.subTest(size=size):
                r = key_ground(synth.strip(size))
                self.assertEqual(r.image.size, size)

    def test_fitting_a_strip_reports_its_real_distortion(self):
        """Rounding a 20px side to whole pixels is a real 1.5% stretch, and must be reported."""
        art = np.zeros((4000, 20, 4), np.uint8)
        art[:, :] = (200, 40, 40, 255)
        r = fit_to_canvas(Image.fromarray(art, "RGBA"))
        self.assertGreater(r.aspect_drift, 0.005, "a whole-pixel stretch went unreported")
        self.assertLess(r.aspect_drift, 0.05)

    def test_drift_means_the_same_thing_whichever_way_up_the_artwork_is(self):
        """The old difference-of-ratios read 1.43 one way round and 0.000075 the other."""
        def art(w, h):
            a = np.zeros((h, w, 4), np.uint8)
            a[:, :] = (200, 40, 40, 255)
            return Image.fromarray(a, "RGBA")
        wide = fit_to_canvas(art(4000, 20)).aspect_drift
        tall = fit_to_canvas(art(20, 4000)).aspect_drift
        self.assertLess(abs(wide - tall), 0.02, (wide, tall))

    def test_ordinary_shapes_are_still_pinned_at_no_distortion(self):
        for w, h in ((300, 900), (900, 300), (500, 500), (613, 431), (9000, 11000)):
            with self.subTest(size=(w, h)):
                a = np.zeros((h, w, 4), np.uint8)
                a[:, :] = (200, 40, 40, 255)
                self.assertLess(fit_to_canvas(Image.fromarray(a, "RGBA")).aspect_drift, 0.005)


class TestIndexedAndGreyscaleSources(unittest.TestCase):
    def test_an_indexed_png_with_transparency_is_read_as_cut_out(self):
        """Some exporters write indexed PNGs; its alpha lives in the palette, not a channel."""
        p = Image.new("P", (60, 60))
        p.putpalette([0, 0, 0] + [255, 255, 255] * 255)
        px = p.load()
        for y in range(60):
            for x in range(60):
                px[x, y] = 0 if 20 <= x < 40 and 20 <= y < 40 else 1
        p.info["transparency"] = 1
        m = alpha_report(p)
        self.assertTrue(m["has_alpha"])
        self.assertTrue(m["corners_clear"])
        self.assertEqual(m["bbox"], [20, 20, 40, 40])

    def test_a_flat_rgb_scan_fails_qc_for_the_right_reason(self):
        r = check_master(synth.cat_on_paper(), canvas=(400, 400))
        self.assertFalse(r["passed"])
        self.assertTrue(any("no alpha" in p for p in r["problems"]), r)

    def test_save_master_adds_the_alpha_channel_a_master_needs(self):
        import os
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "m.png")
        save_master(Image.new("RGB", (40, 40), (10, 10, 10)), path)
        with Image.open(path) as back:
            self.assertEqual(back.mode, "RGBA")


class TestMeasureGrainReportsTheSameShape(unittest.TestCase):
    def test_a_ground_colour_from_another_image_reports_nothing_measured(self):
        """Passing the wrong ground used to return a dict missing p99_9 entirely."""
        m = measure_grain(synth.cat_on_paper(), ground=(0, 0, 0))
        self.assertEqual(m["pixels"], 0)
        self.assertIsNone(m["p99_9"])

    def test_the_keys_do_not_depend_on_the_answer(self):
        good = measure_grain(synth.cat_on_paper())
        bad = measure_grain(synth.cat_on_paper(), ground=(0, 0, 0))
        self.assertEqual(sorted(good), sorted(bad))
        self.assertIsNotNone(good["p99_9"])


if __name__ == "__main__":
    unittest.main()
