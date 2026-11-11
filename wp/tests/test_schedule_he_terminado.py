"""Tests for wp/mu-plugins/rosmarops-schedule-he-terminado.php: post 2 of the agents series scheduled for 12-11 06:00 Madrid.

Run from the repository root:  python3 -m unittest wp/tests/test_schedule_he_terminado.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": ("https://rosmarops.com", "ai-agent-says-done"),
         "es": ("https://rosmarops.com/es", "agente-de-ia-he-terminado"),
         "ca": ("https://rosmarops.com/ca", "agent-dia-he-acabat")}
BEFORE = 1794416400  # 2026-11-11 17:00 UTC
AT = 1794459600      # 2026-11-12 05:00 UTC
AFTER = AT + 120


class Sched2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def state(self, posts):
        self.db.write_text(json.dumps({"options": {}, "posts": posts}))

    def run_at(self, home, now):
        env = dict(os.environ, SCHED2_DB=str(self.db), SCHED2_CONTENT=str(Path(self.tmp.name) / "content"))
        out = subprocess.run(["php", str(TESTS / "sched2-stub.php"), home, str(now)], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def post(self, slug, status="draft", pid=10, other=None):
        p = {"ID": pid, "post_name": slug, "post_type": "post", "post_status": status, "post_title": "T", "post_content": "C",
             "post_date": "2026-11-09 19:36:00", "post_date_gmt": "2026-11-09 18:36:00"}
        p.update(other or {})
        return p

    def test_schedules_each_site_at_six_madrid(self):
        for lang, (home, slug) in SITES.items():
            with self.subTest(lang=lang):
                self.state([self.post(slug), self.post("other-post", pid=11)])
                log, db = self.run_at(home, BEFORE)
                p = db["posts"][0]
                self.assertEqual(p["post_status"], "future")
                self.assertEqual(p["post_date_gmt"], "2026-11-12 05:00:00")
                self.assertEqual(p["post_date"], "2026-11-12 06:00:00")
                self.assertEqual((p["post_title"], p["post_content"]), ("T", "C"))
                self.assertEqual(db["posts"][1]["post_status"], "draft")
                self.assertTrue(log[-1].startswith("done: post 10"))
                self.assertIn("rosmarops_sched2_done", db["options"])
                self.assertNotIn("rosmarops_sched2_lock", db["options"])
                self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / f"sched2-{lang}.log").exists())

    def test_runs_once(self):
        home, slug = SITES["es"]
        self.state([self.post(slug)])
        self.run_at(home, BEFORE)
        db = json.loads(self.db.read_text())
        db["posts"][0]["post_status"] = "draft"  # changed back by hand: must not be scheduled again
        self.db.write_text(json.dumps(db))
        _, db = self.run_at(home, BEFORE)
        self.assertEqual(db["posts"][0]["post_status"], "draft")

    def test_leaves_published_post_alone(self):
        home, slug = SITES["en"]
        self.state([self.post(slug, status="publish")])
        log, db = self.run_at(home, BEFORE)
        self.assertEqual(db["posts"][0]["post_status"], "publish")
        self.assertTrue(log[-1].startswith("skipped:"))

    def test_missing_or_duplicate_slug(self):
        home, slug = SITES["ca"]
        for posts in ([], [self.post(slug), self.post(slug, pid=12)]):
            with self.subTest(n=len(posts)):
                self.state(posts)
                log, db = self.run_at(home, BEFORE)
                self.assertTrue(log[-1].startswith("skipped:"))
                self.assertTrue(all(p["post_status"] == "draft" for p in db["posts"]))

    def test_too_late_stays_draft(self):
        home, slug = SITES["es"]
        self.state([self.post(slug)])
        log, db = self.run_at(home, AFTER)
        self.assertEqual(db["posts"][0]["post_status"], "draft")
        self.assertTrue(any("has passed" in l for l in log))

    def test_other_site_does_nothing(self):
        self.state([self.post("agente-de-ia-he-terminado")])
        log, db = self.run_at("https://example.com", BEFORE)
        self.assertEqual(log, [])
        self.assertFalse(db["options"])

    def test_fallback_publishes_after_time_only(self):
        home, slug = SITES["es"]
        self.state([self.post(slug)])
        self.run_at(home, BEFORE)
        _, db = self.run_at(home, AT - 60)
        self.assertEqual(db["posts"][0]["post_status"], "future")
        log, db = self.run_at(home, AFTER)
        self.assertEqual(db["posts"][0]["post_status"], "publish")
        self.assertTrue(log[-1].startswith("fallback: post 10 published"))
        self.assertIn("rosmarops_sched2_live", db["options"])

    def test_fallback_stops_when_cron_published(self):
        home, slug = SITES["en"]
        self.state([self.post(slug)])
        self.run_at(home, BEFORE)
        db = json.loads(self.db.read_text())
        db["posts"][0]["post_status"] = "publish"  # WP-Cron did it
        self.db.write_text(json.dumps(db))
        log, db = self.run_at(home, AFTER)
        self.assertIn("rosmarops_sched2_live", db["options"])
        self.assertIn("is publish", log[-1])


if __name__ == "__main__":
    unittest.main()
