"""Tests for wp/mu-plugins/rosmarops-slug7-sandbox.php: the ES and CA sandbox posts back to their address without «-2»
(GTM-175 slug7, signed by Albert 17-11 17:43).

Run from the repository root:  python3 -m unittest wp/tests/test_slug7_sandbox.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"es": ("https://rosmarops.com/es", "sandbox-agentes-de-ia", 1238, 1240),
         "ca": ("https://rosmarops.com/ca", "sandbox-agents-dia", 90, 91)}


def post(pid, slug, status, ptype="post"):
    return {"ID": pid, "post_name": slug, "post_type": ptype, "post_status": status,
            "post_title": f"title {pid}", "post_content": f"content {pid}"}


class Slug7(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "content"
        os.mkdir(self.content)

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, home):
        env = dict(os.environ, SLUG7_DB=str(self.db), SLUG7_CONTENT=str(self.content))
        out = subprocess.run(["php", str(TESTS / "slug7-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def run_with(self, home, posts):
        self.db.write_text(json.dumps({"options": {}, "posts": posts}))
        return self.request(home)

    def site(self, lang, extra=()):
        home, slug, d, p = SITES[lang]
        return home, slug, d, p, [post(d, slug, "draft"), post(p, slug + "-2", "publish"), post(7, "other", "publish"), *extra]

    def by_id(self, db, pid):
        return next(x for x in db["posts"] if x["ID"] == pid)

    def test_happy_path_es_and_ca(self):
        for lang in SITES:
            with self.subTest(lang=lang):
                home, slug, d, p, posts = self.site(lang)
                log, db = self.run_with(home, posts)
                self.assertEqual(self.by_id(db, p)["post_name"], slug)
                self.assertEqual(self.by_id(db, p)["post_status"], "publish")
                self.assertEqual(self.by_id(db, d)["post_status"], "trash")
                self.assertEqual(self.by_id(db, d)["post_name"], slug + "__trashed")
                self.assertEqual(self.by_id(db, 7), post(7, "other", "publish"))
                self.assertEqual(log[-1], f"done: post {p} now at {slug} (was {slug}-2)")
                self.assertIn(f"draft {d}: post draft at {slug}", log)
                self.assertIn(f"post {p}: post publish at {slug}-2", log)
                self.assertIn(f"trash: post {d} is trash at {slug}__trashed", log)
                self.assertEqual(db["calls"], ["wp_trash_post", "wp_update_post"])
                self.assertIn("rosmarops_slug7_done", db["options"])
                self.assertTrue((self.content / "rosmarops-private" / f"slug7-{lang}.log").exists())

    def test_draft_not_a_draft_or_at_another_slug(self):
        home, slug, d, p, _ = self.site("es")
        for draft in (post(d, slug, "publish"), post(d, slug, "pending"), post(d, slug + "-3", "draft"), post(d, slug, "draft", "page")):
            with self.subTest(draft=draft):
                posts = [draft, post(p, slug + "-2", "publish")]
                log, db = self.run_with(home, posts)
                self.assertTrue(log[-1].startswith(f"skipped: post {d} is not a draft"))
                self.assertEqual(db["posts"], posts)
                self.assertEqual(db["calls"], [])

    def test_missing_draft(self):
        home, slug, d, p, _ = self.site("ca")
        log, db = self.run_with(home, [post(p, slug + "-2", "publish")])
        self.assertIn(f"draft {d}: not found", log)
        self.assertTrue(log[-1].startswith("skipped:"))
        self.assertEqual(db["calls"], [])

    def test_published_without_dash_two(self):
        home, slug, d, p, _ = self.site("ca")
        for pub in (post(p, slug + "-3", "publish"), post(p, slug + "-2", "draft")):
            with self.subTest(pub=pub):
                posts = [post(d, slug, "draft"), pub]
                log, db = self.run_with(home, posts)
                self.assertTrue(log[-1].startswith(f"skipped: post {p} is not published at {slug}-2"))
                self.assertEqual(db["posts"], posts)
                self.assertEqual(db["calls"], [])

    def test_another_post_with_the_clean_slug_after_the_bin(self):
        for other in (post(50, "sandbox-agentes-de-ia", "trash"), post(51, "sandbox-agentes-de-ia", "inherit", "attachment"),
                      post(52, "sandbox-agentes-de-ia", "private", "page")):
            with self.subTest(other=other):
                home, slug, d, p, posts = self.site("es", [other])
                log, db = self.run_with(home, posts)
                self.assertEqual(log[-1].split(" (")[0], f"skipped: {other['ID']} usa el slug")
                self.assertEqual(self.by_id(db, p), post(p, slug + "-2", "publish"))
                self.assertEqual(db["calls"], ["wp_trash_post"])

    def test_en_does_nothing(self):
        posts = [post(1247, "sandbox-ai-agents", "publish"), post(1245, "sandbox-ai-agents-2", "draft")]
        log, db = self.run_with("https://rosmarops.com", posts)
        self.assertEqual(log, [])
        self.assertEqual(db["posts"], posts)
        self.assertEqual(db["calls"], [])
        self.assertNotIn("rosmarops_slug7_done", db["options"])

    def test_second_time_does_nothing(self):
        home, slug, d, p, posts = self.site("es")
        self.run_with(home, posts)
        db = json.loads(self.db.read_text())
        self.by_id(db, p)["post_name"] = slug + "-2"  # changed back by hand: must not run again
        db["calls"] = []
        self.db.write_text(json.dumps(db))
        _, db = self.request(home)
        self.assertEqual(self.by_id(db, p)["post_name"], slug + "-2")
        self.assertEqual(db["calls"], [])

    def test_never_deletes(self):
        src = (TESTS.parent / "mu-plugins" / "rosmarops-slug7-sandbox.php").read_text()
        code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith(("*", "//", "/**")))
        self.assertNotIn("wp_delete_post", code)
        self.assertNotIn("wp_trash_post(" + "$p", code)
        for lang in SITES:
            home, slug, d, p, posts = self.site(lang)
            _, db = self.run_with(home, posts)
            self.assertNotIn("wp_delete_post", db["calls"])


if __name__ == "__main__":
    unittest.main()
