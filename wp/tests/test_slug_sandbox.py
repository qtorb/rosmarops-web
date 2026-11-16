"""Tests for wp/mu-plugins/rosmarops-slug-sandbox.php: the sandbox post back to its address without «-2».

Run from the repository root:  python3 -m unittest wp/tests/test_slug_sandbox.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": ("https://rosmarops.com", "sandbox-ai-agents"),
         "es": ("https://rosmarops.com/es", "sandbox-agentes-de-ia"),
         "ca": ("https://rosmarops.com/ca", "sandbox-agents-dia")}


class Slug6(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, posts):
        self.db.write_text(json.dumps({"options": {}, "posts": posts}))
        env = dict(os.environ, SLUG6_DB=str(self.db), SLUG6_CONTENT=str(Path(self.tmp.name) / "content"))
        out = subprocess.run(["php", str(TESTS / "slug6-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def post(self, slug, status="publish", pid=10):
        return {"ID": pid, "post_name": slug, "post_type": "post", "post_status": status}

    def test_renames_on_each_site(self):
        for lang, (home, slug) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, [self.post(slug + "-2"), self.post("other", pid=11)])
                self.assertEqual(db["posts"][0]["post_name"], slug)
                self.assertEqual(db["posts"][1]["post_name"], "other")
                self.assertTrue(log[-1].startswith("done: post 10"))
                self.assertIn("rosmarops_slug6_done", db["options"])
                self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / f"slug6-{lang}.log").exists())

    def test_leaves_it_when_the_slug_is_still_taken(self):
        home, slug = SITES["es"]
        for status in ("draft", "trash", "publish"):
            with self.subTest(status=status):
                log, db = self.run_with(home, [self.post(slug + "-2"), self.post(slug, status=status, pid=12)])
                self.assertEqual(db["posts"][0]["post_name"], slug + "-2")
                self.assertTrue(log[-1].startswith("skipped:"))

    def test_an_attachment_with_the_slug_also_blocks(self):
        home, slug = SITES["es"]
        a = self.post(slug, status="inherit", pid=13)
        a["post_type"] = "attachment"
        log, db = self.run_with(home, [self.post(slug + "-2"), a])
        self.assertEqual(db["posts"][0]["post_name"], slug + "-2")
        self.assertIn("attachment", log[-1])

    def test_nothing_to_do_without_a_published_dash_two(self):
        home, slug = SITES["ca"]
        log, db = self.run_with(home, [self.post(slug + "-2", status="draft")])
        self.assertEqual(db["posts"][0]["post_name"], slug + "-2")
        self.assertTrue(log[-1].startswith("skipped:"))

    def test_runs_once(self):
        home, slug = SITES["en"]
        self.run_with(home, [self.post(slug + "-2")])
        db = json.loads(self.db.read_text())
        db["posts"][0]["post_name"] = slug + "-2"  # changed back by hand: must not run again
        self.db.write_text(json.dumps(db))
        env = dict(os.environ, SLUG6_DB=str(self.db), SLUG6_CONTENT=str(Path(self.tmp.name) / "content"))
        subprocess.run(["php", str(TESTS / "slug6-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(self.db.read_text())["posts"][0]["post_name"], slug + "-2")

    def test_other_sites_do_nothing(self):
        log, _ = self.run_with("https://example.com", [self.post("sandbox-ai-agents-2")])
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
