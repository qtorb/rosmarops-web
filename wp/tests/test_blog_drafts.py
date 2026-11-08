"""Tests for wp/mu-plugins/rosmarops-blog-drafts.php: blog posts from wp/drafts/ created as drafts, once per site.

Run from the repository root:  python3 -m unittest wp/tests/test_blog_drafts.py   (needs php on PATH)
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
DRAFTS = TESTS.parent / "drafts"
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
ALBERT = {"ID": 3, "display_name": "Albert Garcia Pujadas", "roles": ["administrator"]}
ADMIN = {"ID": 1, "display_name": "admin6244", "roles": ["administrator"]}


def descriptions():
    return {d["lang"]: d for d in (json.loads(f.read_text(encoding="utf-8")) for f in sorted(DRAFTS.glob("*.json")))}


class Drafts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dbf = root / "db.json"
        self.content = root / "wp-content"
        self.content.mkdir()
        self.dir = root / "rosmarops-drafts"
        shutil.copytree(DRAFTS, self.dir)

    def run_once(self, home, data=None, fail=False):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, DRAFTS_DB=str(self.dbf), DRAFTS_CONTENT=str(self.content), DRAFTS_DIR=str(self.dir))
        if fail:
            env["DRAFTS_FAIL"] = "1"
        p = subprocess.run(["php", str(TESTS / "drafts-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    @staticmethod
    def db(posts=(), users=(ADMIN, ALBERT)):
        return {"options": {}, "posts": list(posts), "users": list(users), "meta": {}}

    def test_descriptions_are_complete_and_link_each_other(self):
        d = descriptions()
        self.assertEqual(set(d), {"en", "es", "ca"})
        urls = {l: f"{SITES[l]}/blog/{d[l]['slug']}/" for l in d}
        for l, x in d.items():
            self.assertEqual(x["id"], "loop-engineering")
            self.assertTrue((DRAFTS / x["content"]).is_file())
            self.assertLessEqual(len(x["seo_title"]), 60, l)
            self.assertLessEqual(len(x["seo_description"]), 160, l)
            self.assertEqual(x["translations"], {o: urls[o] for o in urls if o != l})
            html = (DRAFTS / x["content"]).read_text(encoding="utf-8")
            self.assertIn("arxiv.org/abs/2608.21884v3", html)
            self.assertNotIn("<h1", html)
            self.assertNotIn("<script", html.lower())

    def test_each_site_gets_its_own_draft_and_only_a_draft(self):
        d = descriptions()
        for lang, home in SITES.items():
            log, out = self.run_once(home, self.db())
            posts = [p for p in out["posts"]]
            self.assertEqual(len(posts), 1, lang)
            p = posts[0]
            self.assertEqual(p["post_status"], "draft")
            self.assertEqual(p["post_type"], "post")
            self.assertEqual((p["post_name"], p["post_title"], p["post_excerpt"]), (d[lang]["slug"], d[lang]["title"], d[lang]["excerpt"]))
            self.assertEqual(p["post_content"], (DRAFTS / d[lang]["content"]).read_text(encoding="utf-8"))
            self.assertEqual(p["post_author"], 3)
            meta = out["meta"][str(p["ID"])]
            self.assertEqual(meta["_genesis_title"], d[lang]["seo_title"])
            self.assertEqual(meta["_genesis_description"], d[lang]["seo_description"])
            self.assertEqual({k: v for k, v in meta.items() if k.startswith("rosmarops_url_")},
                             {f"rosmarops_url_{o}": u for o, u in d[lang]["translations"].items()})
            self.assertTrue(log[0].startswith(f"Blog drafts, site {lang}, "))
            self.assertTrue(log[1].startswith(f"done: {d[lang]['slug']} created as draft"))
            self.assertTrue((self.content / "rosmarops-private" / f"drafts-{lang}.log").is_file())
            self.assertEqual((self.content / "rosmarops-private" / ".htaccess").read_text(), "Require all denied\n")

    def test_runs_once(self):
        _, out = self.run_once(SITES["es"], self.db())
        log, again = self.run_once(SITES["es"])
        self.assertIsNone(log)
        self.assertEqual(len(again["posts"]), 1)

    def test_a_used_slug_is_left_alone(self):
        slug = descriptions()["ca"]["slug"]
        for status in ("publish", "draft", "trash"):
            name = slug + "__trashed" if status == "trash" else slug
            mine = {"ID": 9, "post_name": name, "post_type": "post", "post_status": status, "post_title": "theirs"}
            log, out = self.run_once(SITES["ca"], self.db([mine]))
            self.assertEqual(out["posts"], [mine], status)
            self.assertIn(f"skipped: {slug} already used by post 9 ({status}); nothing changed", log)

    def test_other_hosts_do_nothing(self):
        for home in ["https://rosmarops.com/fr", "https://www.qtorb.com", "http://rosmarops.com"]:
            log, out = self.run_once(home, self.db())
            self.assertIsNone(log, home)
            self.assertEqual(out["posts"], [])

    def test_author_falls_back_to_the_first_administrator(self):
        _, out = self.run_once(SITES["en"], self.db(users=[ADMIN]))
        self.assertEqual(out["posts"][0]["post_author"], 1)

    def test_a_failed_insert_is_tried_again(self):
        log, out = self.run_once(SITES["en"], self.db(), fail=True)
        self.assertIn(f"failed: {descriptions()['en']['slug']} not created", log)
        self.assertNotIn("rosmarops_draft_loop-engineering_done", out["options"])
        log, out = self.run_once(SITES["en"])
        self.assertEqual(len(out["posts"]), 1)

    def test_never_publishes_or_updates(self):
        src = (TESTS.parent / "mu-plugins" / "rosmarops-blog-drafts.php").read_text(encoding="utf-8")
        for word in ["wp_update_post", "wp_publish_post", "wp_delete_post", "'publish'", "wp_trash_post"]:
            self.assertNotIn(word, src)


if __name__ == "__main__":
    unittest.main()
