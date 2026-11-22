"""Tests for wp/mu-plugins/rosmarops-gtm195-voz.php: the worktree drafts get the text in Albert's voice, drafts only.

Run from the repository root:  python3 -m unittest wp/tests/test_gtm195_voz.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
DRAFTS = TESTS.parent / "drafts"
SITES = {"en": ("https://rosmarops.com", 1262, "a-git-worktree-is-not-a-sandbox"),
         "es": ("https://rosmarops.com/es", 1252, "una-worktree-de-git-no-es-un-sandbox"),
         "ca": ("https://rosmarops.com/ca", 105, "una-worktree-de-git-no-es-un-sandbox")}
OLD = "<!-- wp:paragraph -->\n<p>Old text.</p>\n<!-- /wp:paragraph -->\n"


def post(pid, slug, status="draft", ptype="post"):
    return {"ID": pid, "post_name": slug, "post_type": ptype, "post_status": status, "post_title": "Old title",
            "post_content": OLD, "post_excerpt": "Old excerpt.", "post_date": "2026-11-22 22:29:00"}


class Gtm195(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "content"
        os.mkdir(self.content)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, posts, options=None, drafts=DRAFTS):
        self.db.write_text(json.dumps({"options": options or {}, "posts": posts}))
        env = dict(os.environ, GTM195_DB=str(self.db), GTM195_CONTENT=str(self.content), GTM195_DRAFTS=str(drafts))
        out = subprocess.run(["php", str(TESTS / "gtm195-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def test_draft_gets_the_new_text_and_stays_a_draft(self):
        for lang, (home, pid, slug) in SITES.items():
            with self.subTest(lang=lang):
                d = json.loads((DRAFTS / f"worktree-{lang}.json").read_text(encoding="utf-8"))
                log, db = self.run_with(home, [post(pid, slug), post(7, "other")])
                p = next(x for x in db["posts"] if x["ID"] == pid)
                self.assertEqual(p["post_content"], (DRAFTS / f"worktree-{lang}.html").read_text(encoding="utf-8"))
                self.assertEqual(p["post_title"], d["title"])
                self.assertEqual(p["post_excerpt"], d["excerpt"])
                self.assertEqual(db["post_meta"][str(pid)]["_genesis_description"], d["seo_description"])
                self.assertEqual(p["post_status"], "draft")
                self.assertEqual(p["post_date"], "2026-11-22 22:29:00")
                self.assertEqual(next(x for x in db["posts"] if x["ID"] == 7), post(7, "other"))
                self.assertTrue(log[-1].startswith("done:"))
                self.assertTrue((self.content / "rosmarops-private" / f"gtm195-{lang}.log").exists())

    def test_published_or_unexpected_posts_are_left_alone(self):
        home, pid, slug = SITES["es"]
        for p in (post(pid, slug, "publish"), post(pid, slug + "-2"), post(pid, slug, ptype="page"), post(pid + 1, slug)):
            with self.subTest(p=f'{p["ID"]} {p["post_status"]} {p["post_name"]} {p["post_type"]}'):
                log, db = self.run_with(home, [p])
                self.assertEqual(db["posts"], [p])
                self.assertNotIn("post_meta", db)
                self.assertTrue(log[-1].startswith("skipped:"))

    def test_missing_files_leave_the_draft_alone(self):
        home, pid, slug = SITES["ca"]
        log, db = self.run_with(home, [post(pid, slug)], drafts=Path(self.tmp.name) / "none")
        self.assertEqual(db["posts"], [post(pid, slug)])
        self.assertIn("worktree-ca.json", log[-1])

    def test_once_per_site_and_other_sites_do_nothing(self):
        home, pid, slug = SITES["en"]
        log, db = self.run_with(home, [post(pid, slug)], options={"rosmarops_gtm195_done": "x"})
        self.assertIsNone(log)
        self.assertEqual(db["posts"], [post(pid, slug)])
        log, db = self.run_with("https://rosmarops.com/fr", [post(pid, slug)])
        self.assertIsNone(log)
        self.assertEqual(db["posts"], [post(pid, slug)])


if __name__ == "__main__":
    unittest.main()
