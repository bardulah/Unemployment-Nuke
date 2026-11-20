import json
import tempfile
import unittest

from careerforge.db import Tracker, today


class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tr = Tracker(self.tmp.name)

    def tearDown(self):
        self.tr.close()
        self.tmp.cleanup()

    def test_profile_roundtrip(self):
        self.assertEqual(self.tr.get_profile(), {})
        self.tr.set_profile({"name": "Ada", "skills": [{"name": "Python", "level": "basic"}]})
        self.assertEqual(self.tr.get_profile()["name"], "Ada")
        self.tr.set_profile({"name": "Ada2"})
        self.assertEqual(self.tr.get_profile()["name"], "Ada2")

    def test_targets_and_results(self):
        tid = self.tr.add_target(title="Data Analyst", company="Acme", jd_text="python sql dashboards")
        targets = self.tr.list_targets()
        self.assertEqual(len(targets), 1)
        self.assertEqual(self.tr.get_target(tid)["company"], "Acme")
        self.tr.save_result(tid, "gap", {"match_score": 40}, mode="offline", model="offline-heuristic")
        self.tr.save_result(tid, "gap", {"match_score": 55}, mode="llm", model="mistral-large-latest")
        latest = self.tr.get_latest_result(tid, "gap")
        self.assertEqual(latest["payload"]["match_score"], 55)
        self.assertEqual(latest["mode"], "llm")
        self.assertIsNone(self.tr.get_latest_result(tid, "project"))
        with self.assertRaises(ValueError):
            self.tr.save_result(tid, "bogus", {}, mode="llm")

    def test_applications_and_status_validation(self):
        tid = self.tr.add_target(title="IT Support", company="TatraTech", jd_text="AD DNS DHCP")
        app_id = self.tr.add_application(status="applied", target_id=tid, contact="recruiter@acme.com")
        self.tr.update_application(app_id, status="interview", next_followup="2026-12-01")
        app = self.tr.get_application(app_id)
        self.assertEqual(app["status"], "interview")
        self.assertEqual(app["target_title"], "IT Support")
        with self.assertRaises(ValueError):
            self.tr.add_application(status="hired")
        with self.assertRaises(ValueError):
            self.tr.update_application(app_id, status="hired")

    def test_reminders_due(self):
        self.tr.add_reminder("follow up", "2000-01-01")
        rid = self.tr.add_reminder("future", "2999-01-01")
        due = self.tr.due_reminders()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["message"], "follow up")
        self.tr.complete_reminder(rid)
        self.assertEqual(len(self.tr.due_reminders(on_date="2999-01-01")), 1)
        self.assertEqual(len(self.tr.list_reminders()), 1)
        self.assertEqual(len(self.tr.list_reminders(include_done=True)), 2)

    def test_stats(self):
        tid = self.tr.add_target(title="X", company="Y", jd_text="python")
        self.tr.save_result(tid, "gap", {"match_score": 33}, mode="offline")
        self.tr.add_application(status="applied")
        self.tr.add_reminder("r", today())
        stats = self.tr.stats()
        self.assertEqual(stats["targets"], 1)
        self.assertEqual(stats["applications_by_status"], {"applied": 1})
        self.assertEqual(stats["overdue_reminders"], 1)
        self.assertEqual(stats["match_scores"], {tid: 33})
        json.dumps(stats)  # must be JSON-serializable


if __name__ == "__main__":
    unittest.main()
