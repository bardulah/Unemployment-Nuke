import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from careerforge.cli import main
from careerforge.db import Tracker

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class CliTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--data-dir", self.data_dir, "--offline", *argv])
        return code, buf.getvalue()


class TestEngineOffline(CliTestBase):
    def test_full_offline_flow(self):
        code, out = self.run_cli("profile", "init", "--from-cv", str(EXAMPLES / "cv-matus-altaner.md"), "--name", "Matúš Altaner")
        self.assertEqual(code, 0)
        with Tracker(self.data_dir) as tr:
            prof = tr.get_profile()
            self.assertEqual(prof["name"], "Matúš Altaner")
            self.assertIn("matusaltaner@gmail.com", prof["contact"]["email"])

        code, _ = self.run_cli("profile", "set", "work_preferences.roles", '["Junior Data Analyst","IT Support Specialist"]')
        self.assertEqual(code, 0)
        code, _ = self.run_cli("profile", "set", "work_preferences.remote", "hybrid")
        self.assertEqual(code, 0)

        code, out = self.run_cli("target", "add", "--title", "Junior Data Analyst", "--company", "ACME Logistics",
                                 "--jd-file", str(EXAMPLES / "jd-junior-data-analyst.txt"), "--location", "Bratislava")
        self.assertEqual(code, 0)
        self.assertIn("target #1", out)

        code, out = self.run_cli("run", "1")
        self.assertEqual(code, 0)
        self.assertIn("GAP ANALYSIS", out)
        self.assertIn("14-DAY MICRO-PROJECT", out)
        self.assertIn("TAILORED CV + OUTREACH", out)
        self.assertIn("Day 14", out)

        with Tracker(self.data_dir) as tr:
            gap = tr.get_latest_result(1, "gap")
            proj = tr.get_latest_result(1, "project")
            tail = tr.get_latest_result(1, "tailor")
            self.assertEqual(gap["mode"], "offline")
            self.assertEqual(len(proj["payload"]["days"]), 14)
            self.assertTrue(tail["payload"]["cv_bullets"])
            self.assertIn("outreach", tail["payload"])
            self.assertGreaterEqual(gap["payload"]["match_score"], 0)
            self.assertLessEqual(gap["payload"]["match_score"], 100)

        code, out = self.run_cli("track", "add", "--target", "1", "--status", "applied", "--contact", "recruiter@acme.eu", "--followup", "2999-01-01")
        self.assertEqual(code, 0)
        code, out = self.run_cli("track", "list")
        self.assertIn("applied", out)
        code, out = self.run_cli("track", "set", "1", "--status", "interview")
        self.assertEqual(code, 0)

        code, out = self.run_cli("remind", "add", "--message", "follow up with ACME recruiter", "--due", "2999-01-01", "--app", "1")
        self.assertEqual(code, 0)
        code, out = self.run_cli("remind", "list")
        self.assertIn("follow up with ACME recruiter", out)
        code, out = self.run_cli("remind", "done", "1")
        self.assertEqual(code, 0)
        code, out = self.run_cli("remind", "list", "--all")
        self.assertIn("[x]", out)

        out_dir = Path(self.data_dir) / "export"
        code, out = self.run_cli("export", "1", "--out", str(out_dir))
        self.assertEqual(code, 0)
        names = {p.name for p in out_dir.iterdir()}
        self.assertIn("acme-logistics-gap-analysis.md", names)
        self.assertIn("acme-logistics-14day-project.md", names)
        self.assertIn("acme-logistics-tailored-cv-outreach.md", names)

        code, out = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("Matúš Altaner", out)
        self.assertIn("interview", out)

    def test_errors(self):
        code, _ = self.run_cli("analyze", "99")
        self.assertEqual(code, 2)
        code, _ = self.run_cli("target", "add", "--title", "X")
        self.assertEqual(code, 2)

    def test_profile_show_export_import(self):
        self.run_cli("profile", "init", "--from-cv", str(EXAMPLES / "cv-matus-altaner.md"))
        code, out = self.run_cli("profile", "show", "--json")
        self.assertEqual(code, 0)
        prof = json.loads(out)
        self.assertIn("raw_cv", prof)
        export_path = Path(self.data_dir) / "p.json"
        self.run_cli("profile", "export", str(export_path))
        self.run_cli("profile", "set", "summary", "ops-to-data")
        self.run_cli("profile", "import", str(export_path))
        code, out = self.run_cli("profile", "show", "--json")
        self.assertNotIn("ops-to-data", out)


if __name__ == "__main__":
    unittest.main()
