"""Tests for wp/mu-plugins/rosmarops-papelera-0-16.php: the three drafts of the earlier 0.16 post to the bin
(plan for the week of 23-29 November, point 7, signed by Albert 21-11 10:48).

Run from the repository root:  python3 -m unittest wp/tests/test_papelera_0_16.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": ("https://rosmarops.com", 1255, "from-a-long-list-of-findings-to-a-short-list-of-problems"),
         "es": ("https://rosmarops.com/es", 1245, "de-una-lista-larga-de-avisos-a-una-lista-corta-de-problemas"),
         "ca": ("https://rosmarops.com/ca", 99, "duna-llista-llarga-davisos-a-una-llista-curta-de-problemes")}


def post(pid, slug, status, ptype="post"):
    return {"ID": pid, "post_name": slug, "post_type": ptype, "post_status": status,
            "post_title": f"title {pid}", "post_content": f"content {pid}"}


class Bin016(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "content"
        os.mkdir(self.content)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, home):
        env = dict(os.environ, BIN016_DB=str(self.db), BIN016_CONTENT=str(self.content))
        out = subprocess.run(["php", str(TESTS / "bin016-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def run_with(self, home, posts):
        self.db.write_text(json.dumps({"options": {}, "posts": posts}))
        return self.request(home)

    def by_id(self, db, pid):
        return next(x for x in db["posts"] if x["ID"] == pid)

    def test_each_site_sends_its_draft_to_the_bin_and_nothing_else(self):
        for lang, (home, pid, slug) in SITES.items():
            with self.subTest(lang=lang):
                new = post(2000, "whats-new-0-17", "publish")
                posts = [post(pid, slug, "draft"), new, post(7, "other", "draft")]
                log, db = self.run_with(home, posts)
                self.assertEqual(self.by_id(db, pid)["post_status"], "trash")
                self.assertEqual(self.by_id(db, 2000), new)
                self.assertEqual(self.by_id(db, 7), post(7, "other", "draft"))
                self.assertIn(f"post {pid}: post draft at {slug}", log)
                self.assertEqual(log[-1], f"done: post {pid} in the bin (was a draft at {slug})")
                self.assertEqual(db["calls"], ["wp_trash_post"])
                self.assertIn("rosmarops_bin016_done", db["options"])
                self.assertTrue((self.content / "rosmarops-private" / f"bin016-{lang}.log").exists())

    def test_leaves_alone_anything_that_is_not_that_draft(self):
        home, pid, slug = SITES["es"]
        for p in (post(pid, slug, "publish"), post(pid, slug, "future"), post(pid, slug + "-2", "draft"),
                  post(pid, slug, "draft", "page"), post(pid, slug, "trash")):
            with self.subTest(p=p):
                log, db = self.run_with(home, [p])
                self.assertEqual(log[-1], f"skipped: post {pid} is not a draft at {slug}")
                self.assertEqual(db["posts"], [p])
                self.assertEqual(db["calls"], [])

    def test_missing_post(self):
        home, pid, slug = SITES["ca"]
        log, db = self.run_with(home, [post(100, slug, "draft")])
        self.assertIn(f"post {pid}: not found", log)
        self.assertTrue(log[-1].startswith("skipped:"))
        self.assertEqual(db["calls"], [])

    def test_other_sites_do_nothing(self):
        posts = [post(1255, SITES["en"][2], "draft")]
        log, db = self.run_with("https://rosmarops.com/fr", posts)
        self.assertEqual(log, [])
        self.assertEqual(db["posts"], posts)
        self.assertNotIn("rosmarops_bin016_done", db["options"])

    def test_second_time_does_nothing(self):
        home, pid, slug = SITES["en"]
        self.run_with(home, [post(pid, slug, "draft")])
        db = json.loads(self.db.read_text())
        db["posts"] = [post(pid, slug, "draft")]  # restored by hand: must not run again
        db["calls"] = []
        self.db.write_text(json.dumps(db))
        _, db = self.request(home)
        self.assertEqual(db["posts"], [post(pid, slug, "draft")])
        self.assertEqual(db["calls"], [])

    def test_never_deletes_or_updates(self):
        src = (TESTS.parent / "mu-plugins" / "rosmarops-papelera-0-16.php").read_text()
        code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith(("*", "//", "/**")))
        for word in ("wp_delete_post", "wp_update_post", "wp_publish_post", "$wpdb"):
            self.assertNotIn(word, code)


if __name__ == "__main__":
    unittest.main()
