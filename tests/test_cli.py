"""The command line, driven in process.

The CLI is the part most users meet first, and it had no coverage at all: every wrong argument
came back as a Python traceback, and the exit codes were never checked.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import numpy as np
from PIL import Image

import synth
from printprep.__main__ import main


class CliCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.art = os.path.join(self.dir, "art.png")
        synth.cat_on_paper().save(self.art)

    def path(self, name):
        return os.path.join(self.dir, name)

    def run_cli(self, *argv):
        """(exit code, parsed stdout JSON or raw text, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        text = out.getvalue()
        try:
            payload = json.loads(text)
        except ValueError:
            payload = text
        return code, payload, err.getvalue()


class TestTheWholeChain(CliCase):
    def test_grain_key_fit_and_qc_run_end_to_end(self):
        code, grain, _ = self.run_cli("grain", self.art)
        self.assertEqual(code, 0)
        self.assertLess(grain["p99_9"], 24, "the demo artwork should suit the default --grain")

        cut = self.path("cut.png")
        code, stats, err = self.run_cli("key", self.art, cut)
        self.assertEqual(code, 0, err)
        self.assertGreater(stats["transparent_pct"], 50)
        self.assertEqual(err, "", "a clean key should say nothing on stderr")
        with Image.open(cut) as written:
            self.assertEqual(written.mode, "RGBA")

        master = self.path("master.png")
        code, fit, _ = self.run_cli("fit", cut, master, "--canvas", "900x1080")
        self.assertEqual(code, 0)
        self.assertLess(fit["aspect_drift"], 0.005)

        code, report, _ = self.run_cli("qc", master, "--canvas", "900x1080")
        self.assertEqual(code, 0, report)
        self.assertTrue(report["passed"])

    def test_qc_exits_1_when_the_master_fails(self):
        code, report, _ = self.run_cli("qc", self.art)
        self.assertEqual(code, 1)
        self.assertFalse(report["passed"])

    def test_halo_and_route_report_measurements(self):
        cut = self.path("cut.png")
        self.run_cli("key", self.art, cut)
        code, h, _ = self.run_cli("halo", cut)
        self.assertEqual(code, 0)
        self.assertLess(h["ring_1px_lum"] - h["ground_lum"], 15)
        code, r, _ = self.run_cli("route", self.art)
        self.assertEqual(code, 0)
        self.assertIn(r["route"], ("vector", "raster"))

    def test_measurements_are_machine_readable_on_stdout(self):
        """Warnings must go to stderr, or they corrupt the JSON a caller is piping."""
        out = io.StringIO()
        err = io.StringIO()
        flat = self.path("flat.png")
        Image.new("RGB", (60, 60), (12, 12, 12)).save(flat)
        with redirect_stdout(out), redirect_stderr(err):
            main(["key", flat, self.path("o.png")])
        json.loads(out.getvalue())
        self.assertNotEqual(err.getvalue(), "")


class TestItFailsWithAReasonNotATraceback(CliCase):
    def test_a_missing_source_file(self):
        code, _, err = self.run_cli("key", self.path("nope.png"), self.path("o.png"))
        self.assertEqual(code, 2)
        self.assertIn("no such file", err)

    def test_a_source_that_is_not_an_image(self):
        junk = self.path("junk.png")
        with open(junk, "w") as fh:
            fh.write("not an image")
        code, _, err = self.run_cli("qc", junk)
        self.assertEqual(code, 2)
        self.assertIn("could not be read", err)

    def test_a_destination_that_cannot_hold_transparency(self):
        """It used to do the whole key, then die inside Pillow with 'cannot write mode RGBA'."""
        code, _, err = self.run_cli("key", self.art, self.path("out.jpg"))
        self.assertEqual(code, 2)
        self.assertIn("transparency", err)
        self.assertIn(".png", err, "the message should name a format that works")

    def test_a_destination_folder_that_does_not_exist(self):
        code, _, err = self.run_cli("key", self.art, self.path("nowhere/out.png"))
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_grain_above_tolerance(self):
        code, _, err = self.run_cli("key", self.art, self.path("o.png"), "--grain", "99")
        self.assertEqual(code, 2)
        self.assertIn("must be below tolerance", err)

    def test_the_destination_is_checked_before_the_work_is_done(self):
        dest = self.path("out.jpg")
        self.run_cli("key", self.art, dest)
        self.assertFalse(os.path.exists(dest))


class TestArgumentParsing(CliCase):
    def test_version_reports_the_package_version(self):
        from printprep import __version__
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as e:
            main(["--version"])
        self.assertEqual(e.exception.code, 0)
        self.assertIn(__version__, out.getvalue())

    def test_a_canvas_that_is_not_wxh_is_rejected_by_name(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            main(["fit", self.art, self.path("o.png"), "--canvas", "banana"])
        self.assertIn("WIDTHxHEIGHT", err.getvalue())

    def test_a_zero_sized_canvas_is_rejected(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            main(["fit", self.art, self.path("o.png"), "--canvas", "0x500"])
        self.assertIn("at least 1 pixel", err.getvalue())


class TestOperatorWarnings(CliCase):
    def test_a_key_that_kept_nothing_says_why(self):
        """Artwork running to the edge makes the border ring read as ink."""
        flat = self.path("allart.png")
        Image.new("RGB", (60, 60), (12, 12, 12)).save(flat)
        code, stats, err = self.run_cli("key", flat, self.path("o.png"))
        self.assertEqual(code, 0)
        self.assertGreater(stats["transparent_pct"], 99)
        self.assertIn("almost nothing was kept", err)

    def test_a_key_that_removed_nothing_says_why(self):
        a = np.zeros((60, 60, 3), np.uint8)
        a[:, :] = (240, 232, 214)
        a[2:58, 2:58] = (20, 20, 20)          # ground only in a 2px frame, ink everywhere else
        noisy = self.path("noisy.png")
        Image.fromarray(a, "RGB").save(noisy)
        code, stats, err = self.run_cli("key", noisy, self.path("o.png"),
                                        "--tolerance", "2", "--grain", "1")
        self.assertEqual(code, 0)
        self.assertIn("almost nothing was removed", err)


if __name__ == "__main__":
    unittest.main()
