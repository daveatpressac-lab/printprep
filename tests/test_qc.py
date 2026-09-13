import unittest

import numpy as np
from PIL import Image

import synth
from printprep import (PlateException, alpha_report, check_master, fidelity, fit_to_canvas,
                       key_ground)

CANVAS = (900, 1080)


def cutout_master():
    return fit_to_canvas(key_ground(synth.cat_on_paper()).image, canvas=CANVAS).image


def plate_master():
    a = np.zeros((300, 240, 4), np.uint8)
    a[..., :3] = (210, 190, 160)
    a[..., 3] = 255
    return fit_to_canvas(Image.fromarray(a, "RGBA"), canvas=CANVAS).image


class TestAlphaReport(unittest.TestCase):
    def test_it_measures_the_artwork_not_the_canvas_padding(self):
        m = alpha_report(plate_master())
        self.assertGreater(m["transparent_pct"], 10)          # plenty of canvas padding
        self.assertLess(m["transparent_in_bbox_pct"], 1)      # but the art itself is solid
        self.assertTrue(m["corners_clear"])


class TestCheckMaster(unittest.TestCase):
    def test_a_clean_cutout_passes(self):
        r = check_master(cutout_master(), canvas=CANVAS)
        self.assertTrue(r["passed"], r)

    def test_an_image_with_no_alpha_fails(self):
        """A JPEG that reaches a garment prints as a rectangle."""
        rgb = Image.new("RGB", CANVAS, (255, 255, 255))
        r = check_master(rgb, canvas=CANVAS)
        self.assertFalse(r["passed"])
        self.assertTrue(any("no alpha" in p for p in r["problems"]))

    def test_the_wrong_canvas_fails(self):
        self.assertFalse(check_master(cutout_master(), canvas=(4500, 5400))["passed"])

    def test_clipped_artwork_fails(self):
        a = np.zeros(CANVAS[::-1] + (4,), np.uint8)
        a[0:200, 300:600] = (0, 0, 0, 255)        # runs off the top edge
        r = check_master(Image.fromarray(a, "RGBA"), canvas=CANVAS)
        self.assertTrue(any("clipped" in p for p in r["problems"]), r)

    def test_a_solid_plate_fails_without_an_exception(self):
        r = check_master(plate_master(), canvas=CANVAS)
        self.assertFalse(r["passed"])
        self.assertTrue(any("solid plate" in p for p in r["problems"]))

    def test_a_named_exception_lets_that_plate_through_as_a_warning(self):
        m = plate_master()
        exc = PlateException.for_image(m, "a poster design with a printed border")
        r = check_master(m, canvas=CANVAS, plate_exception=exc)
        self.assertTrue(r["passed"], r)
        self.assertTrue(any("poster design" in w for w in r["warnings"]))
        self.assertLess(r["measurements"]["transparent_in_bbox_pct"], 1, "the measurement still runs")

    def test_the_exception_does_not_follow_the_design_to_new_pixels(self):
        m = plate_master()
        exc = PlateException.for_image(m, "a poster design")
        changed = np.asarray(m).copy()
        changed[540, 450, :3] = (0, 0, 0)
        r = check_master(Image.fromarray(changed, "RGBA"), canvas=CANVAS, plate_exception=exc)
        self.assertFalse(r["passed"])
        self.assertTrue(any("different pixels" in w for w in r["warnings"]))

    def test_an_exception_needs_a_reason(self):
        with self.assertRaises(ValueError):
            PlateException.for_image(plate_master(), "   ")


class TestFidelity(unittest.TestCase):
    def test_an_identical_result_scores_one(self):
        cut = key_ground(synth.cat_on_paper()).image
        f = fidelity(cut, cut)
        self.assertEqual(f["alpha_iou"], 1.0)
        self.assertGreaterEqual(f["score"], 0.999)

    def test_smoothing_away_texture_shows_in_the_detail_ratio(self):
        """Alpha and colour barely move, and the blended score still clears a typical 0.65 floor.
        Only the detail ratio says the texture has gone - which is why it is reported separately."""
        from PIL import ImageFilter
        cut = key_ground(synth.cat_on_paper(grain=10)).image
        rgb = cut.convert("RGB").filter(ImageFilter.GaussianBlur(1.5))
        smooth = rgb.convert("RGBA")
        smooth.putalpha(cut.getchannel("A"))
        f = fidelity(smooth, cut)
        self.assertGreater(f["alpha_iou"], 0.99)
        self.assertGreater(f["colour_similarity"], 0.95)
        self.assertGreater(f["score"], 0.65, "a single blended score would have passed this")
        self.assertLess(f["detail_ratio"], 0.5, f)


if __name__ == "__main__":
    unittest.main()
