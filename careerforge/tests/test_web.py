import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from careerforge.cli import main
from careerforge.db import Tracker
from careerforge.web import make_server

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


class TestWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        data_dir = cls.tmp.name
        main(["--data-dir", data_dir, "--offline", "profile", "init",
              "--from-cv", str(EXAMPLES / "cv-matus-altaner.md"), "--name", "Matúš Altaner"])
        main(["--data-dir", data_dir, "--offline", "target", "add", "--title", "Junior Data Analyst",
              "--company", "ACME", "--jd-file", str(EXAMPLES / "jd-junior-data-analyst.txt")])
        main(["--data-dir", data_dir, "--offline", "run", "1"])
        main(["--data-dir", data_dir, "--offline", "track", "add", "--target", "1", "--status", "applied"])
        cls.server = make_server(data_dir, "127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")

    def post(self, path, data):
        req = urllib.request.Request(self.base + path, data=urlencode(data).encode(),
                                     method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")

    def test_overview(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("careerforge", body)
        self.assertIn("Matúš Altaner", body)
        self.assertIn("Junior Data Analyst", body)
        self.assertIn("/100", body)  # match score rendered

    def test_target_detail(self):
        status, body = self.get("/targets/1")
        self.assertEqual(status, 200)
        self.assertIn("Gap analysis", body)
        self.assertIn("14-day micro-project", body)
        self.assertIn("Day 14", body)
        self.assertIn("Tailored CV", body)

    def test_targets_and_tracker_pages(self):
        self.assertEqual(self.get("/targets")[0], 200)
        status, body = self.get("/tracker")
        self.assertEqual(status, 200)
        self.assertIn("applied", body)

    def test_api(self):
        status, body = self.get("/api/stats")
        self.assertEqual(json.loads(body)["targets"], 1)
        status, body = self.get("/api/targets")
        targets = json.loads(body)
        self.assertEqual(targets[0]["latest"]["gap"]["payload"]["mode"], "offline")
        self.assertEqual(len(targets[0]["latest"]["project"]["payload"]["days"]), 14)

    def test_post_reminder_and_status(self):
        status, body = self.post("/api/reminders/add", {"message": "ping recruiter", "due": "2999-12-31"})
        self.assertEqual(status, 200)
        status, body = self.get("/api/reminders")
        rems = json.loads(body)
        self.assertTrue(any(r["message"] == "ping recruiter" for r in rems))
        rid = next(r["id"] for r in rems if r["message"] == "ping recruiter")
        self.post(f"/api/reminders/{rid}/done", {})
        status, body = self.get("/api/reminders")
        self.assertTrue(next(r for r in json.loads(body) if r["id"] == rid)["done"])
        self.post("/api/applications/1/set", {"status": "interview", "followup": "2999-12-30", "note": "HR call"})
        status, body = self.get("/api/applications")
        app = json.loads(body)[0]
        self.assertEqual(app["status"], "interview")

    def test_loopback_only(self):
        with self.assertRaises(ValueError):
            make_server(self.tmp.name, "0.0.0.0", 0)

    def test_404(self):
        try:
            self.get("/nope")
            self.fail("expected 404")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)


if __name__ == "__main__":
    unittest.main()
