"""Tests for wp/mu-plugins/rosmarops-blog-drafts.php: blog posts from wp/drafts/ created as drafts, once per site.

Run from the repository root:  python3 -m unittest wp/tests/test_blog_drafts.py   (needs php on PATH)
"""

import json
import re
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
IDS = {"loop-engineering", "agente-he-terminado", "errores-repetidos", "harness-engineering", "novedades-0-10", "microsoft-store", "mapa-agentes", "novedades-0-11", "sandbox-v3", "novedades-0-17", "worktree", "video-decide"}
IN_NEWS = {"harness-engineering", "novedades-0-10", "microsoft-store", "mapa-agentes", "novedades-0-11", "sandbox-v3", "novedades-0-17", "worktree", "video-decide"}
NO_IMAGE = {"microsoft-store", "mapa-agentes"}  # GTM-139: news post without a featured image (optional in the plugin)  # the rest of the series goes in loop-engineering
ONLY = {}  # every post in EN, ES and CA (Albert, 20-11)
NO_TAGS = {"novedades-0-17", "video-decide"}  # plan 23-29-11: the 0.16 + 0.17 post goes without tags, like the 0.16 one
NEWS = {"en": "field-notes", "es": "novedades-de-rosmarops", "ca": "notes-de-camp"}


def per_site(lang):
    """How many drafts a site gets (GTM-193: not every post is in every language)."""
    return sum(1 for i in IDS if lang in ONLY.get(i, {"en", "es", "ca"}))


def descriptions():
    """{id: {lang: description}}"""
    out = {}
    for f in sorted(DRAFTS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.setdefault(d["id"], {})[d["lang"]] = d
    return out


def site_terms(lang):
    """The categories that exist on each site, and one tag already there."""
    cats = [{"term_id": 10, "taxonomy": "category", "slug": "loop-engineering", "name": "Loop engineering"},
            {"term_id": 11, "taxonomy": "category", "slug": NEWS[lang], "name": "news"}]
    return cats + [{"term_id": 20, "taxonomy": "post_tag", "slug": "claude-code", "name": "Claude Code"}]


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
    def db(posts=(), users=(ADMIN, ALBERT), lang="en", options=None):
        return {"options": options or {}, "posts": list(posts), "users": list(users), "meta": {}, "terms": site_terms(lang)}

    def test_no_program_version_in_title_or_address(self):
        """Albert, 14-11 (GTM-164): no post names a specific version of the program in its title, SEO title or slug.
        novedades-0-10 is the old draft that was never published."""
        # 0.11, v0.11.6 or 1.2 in text, 0-11 in a slug; not 36.487 (a count) nor 2026 (a year).
        version = re.compile(r"(?<![\d.,])v?\d{1,2}\.\d{1,2}(\.\d{1,3})?(?![\d.,]?\d)|(^|-)v?\d{1,2}-\d{1,2}(-\d{1,3})?(-|$)")
        for did, by_lang in descriptions().items():
            if did == "novedades-0-10":
                continue
            for lang, d in by_lang.items():
                for k in ("title", "seo_title", "slug"):
                    self.assertIsNone(version.search(d[k]), (did, lang, k, d[k]))

    def test_descriptions_are_complete_and_link_each_other(self):
        all_ = descriptions()
        self.assertEqual(set(all_), IDS)
        for pid, d in all_.items():
            self.assertEqual(set(d), ONLY.get(pid, {"en", "es", "ca"}), pid)
            urls = {l: f"{SITES[l]}/blog/{d[l]['slug']}/" for l in d}
            for l, x in d.items():
                self.assertTrue((DRAFTS / x["content"]).is_file())
                self.assertLessEqual(len(x["seo_title"]), 60, (pid, l))
                self.assertLessEqual(len(x["seo_description"]), 160, (pid, l))
                self.assertEqual(x["translations"], {o: urls[o] for o in urls if o != l})
                html = (DRAFTS / x["content"]).read_text(encoding="utf-8")
                self.assertNotIn("<h1", html)
                self.assertNotIn("<script", html.lower())
                self.assertNotIn("](", html, "markdown link left in the HTML")
                self.assertNotIn("**", html)
                if pid != "loop-engineering":
                    if pid in NO_IMAGE:
                        self.assertNotIn("image", x)
                    else:
                        self.assertTrue((DRAFTS / x["image"]).is_file(), x["image"])
                        self.assertTrue(x["alt"])
                    if pid in NO_TAGS:
                        self.assertNotIn("tags", x)
                    else:
                        self.assertTrue(x["tags"])
                    self.assertEqual(x["category"], NEWS[l] if pid in IN_NEWS else "loop-engineering")
        self.assertIn("arxiv.org/abs/2608.21884v3", (DRAFTS / all_["loop-engineering"]["es"]["content"]).read_text(encoding="utf-8"))

    def test_each_site_gets_its_own_drafts_and_only_drafts(self):
        all_ = descriptions()
        for lang, home in SITES.items():
            log, out = self.run_once(home, self.db(lang=lang))
            self.assertEqual(len(out["posts"]), per_site(lang), lang)
            by_slug = {p["post_name"]: p for p in out["posts"]}
            for pid, d in all_.items():
                if lang not in d:
                    continue
                x = d[lang]
                p = by_slug[x["slug"]]
                self.assertEqual(p["post_status"], "draft")
                self.assertEqual(p["post_type"], "post")
                self.assertEqual((p["post_title"], p["post_excerpt"]), (x["title"], x["excerpt"]))
                self.assertEqual(p["post_content"], (DRAFTS / x["content"]).read_text(encoding="utf-8"))
                self.assertEqual(p["post_author"], 3)
                meta = out["meta"][str(p["ID"])]
                self.assertEqual(meta["_genesis_title"], x["seo_title"])
                self.assertEqual(meta["_genesis_description"], x["seo_description"])
                self.assertEqual({k: v for k, v in meta.items() if k.startswith("rosmarops_url_")},
                                 {f"rosmarops_url_{o}": u for o, u in x["translations"].items()})
                self.assertIn(f"done: {x['slug']} created as draft, post {p['ID']}, author 3", log)
                if pid == "loop-engineering":
                    self.assertNotIn("_thumbnail_id", meta)
                    continue
                rel = out["rel"][str(p["ID"])]
                self.assertEqual(rel["category"], [11 if pid in IN_NEWS else 10])
                slugs = {t["term_id"]: t["slug"] for t in out["terms"] if t["taxonomy"] == "post_tag"}
                self.assertEqual({slugs[i] for i in rel.get("post_tag", [])}, set(x.get("tags", {})))
                if pid in NO_IMAGE:
                    self.assertNotIn("_thumbnail_id", meta)
                    continue
                att = [a for a in out["attachments"] if a["ID"] == meta["_thumbnail_id"]][0]
                self.assertEqual((att["file"], att["parent"]), ("uploads-" + x["image"], p["ID"]))
                self.assertEqual(out["meta"][str(att["ID"])]["_wp_attachment_image_alt"], x["alt"])
            tags = [t["slug"] for t in out["terms"] if t["taxonomy"] == "post_tag"]
            self.assertEqual(len(tags), len(set(tags)), "a tag was created twice")
            self.assertTrue(log[0].startswith(f"Blog drafts, site {lang}, "))
            self.assertTrue((self.content / "rosmarops-private" / f"drafts-{lang}.log").is_file())
            self.assertEqual((self.content / "rosmarops-private" / ".htaccess").read_text(), "Require all denied\n")

    def test_already_done_drafts_are_not_created_again(self):
        # On the live sites the loop engineering post was created (and published) on 08-11: only the new ones run.
        log, out = self.run_once(SITES["es"], self.db(lang="es", options={"rosmarops_draft_loop-engineering_done": "x"}))
        self.assertEqual(len(out["posts"]), len(IDS) - 1)
        self.assertFalse(any("loop-engineering-agentes" in l for l in log))

    def test_a_missing_category_is_logged_and_left_out(self):
        data = self.db(lang="ca")
        data["terms"] = [t for t in data["terms"] if t["slug"] != "loop-engineering"]
        log, out = self.run_once(SITES["ca"], data)
        self.assertIn("category skipped: loop-engineering does not exist on this site", " ".join(log))
        self.assertFalse(any(t["slug"] == "loop-engineering" for t in out["terms"]))

    def test_a_malformed_extra_skips_that_draft(self):
        f = self.dir / "errores-repetidos-en.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["image"] = "../evil.php"
        f.write_text(json.dumps(d), encoding="utf-8")
        log, out = self.run_once(SITES["en"], self.db())
        self.assertIn("skipped: errores-repetidos-en.json has a category, tag or image that is not well formed", log)
        self.assertNotIn("ai-agents-repeated-mistakes", [p["post_name"] for p in out["posts"]])

    def test_runs_once(self):
        _, out = self.run_once(SITES["es"], self.db(lang="es"))
        log, again = self.run_once(SITES["es"])
        self.assertIsNone(log)
        self.assertEqual(len(again["posts"]), len(IDS))

    def test_a_used_slug_is_left_alone(self):
        slug = descriptions()["loop-engineering"]["ca"]["slug"]
        for status in ("publish", "draft", "trash"):
            name = slug + "__trashed" if status == "trash" else slug
            mine = {"ID": 9, "post_name": name, "post_type": "post", "post_status": status, "post_title": "theirs"}
            log, out = self.run_once(SITES["ca"], self.db([mine], lang="ca"))
            self.assertEqual([p for p in out["posts"] if p["ID"] == 9], [mine], status)
            self.assertEqual(len(out["posts"]), per_site("ca"), status)
            self.assertIn(f"skipped: {slug} already used by post 9 ({status}); nothing changed", log)

    def test_other_hosts_do_nothing(self):
        for home in ["https://rosmarops.com/fr", "https://www.qtorb.com", "http://rosmarops.com"]:
            log, out = self.run_once(home, self.db())
            self.assertIsNone(log, home)
            self.assertEqual(out["posts"], [])

    def test_author_falls_back_to_the_first_administrator(self):
        _, out = self.run_once(SITES["en"], self.db(users=[ADMIN]))
        self.assertEqual({p["post_author"] for p in out["posts"]}, {1})

    def test_a_failed_insert_is_tried_again(self):
        log, out = self.run_once(SITES["en"], self.db(), fail=True)
        self.assertIn(f"failed: {descriptions()['loop-engineering']['en']['slug']} not created", log)
        self.assertNotIn("rosmarops_draft_loop-engineering_done", out["options"])
        log, out = self.run_once(SITES["en"])
        self.assertEqual(len(out["posts"]), len(IDS))

    def test_never_publishes_or_updates(self):
        src = (TESTS.parent / "mu-plugins" / "rosmarops-blog-drafts.php").read_text(encoding="utf-8")
        for word in ["wp_update_post", "wp_publish_post", "wp_delete_post", "'publish'", "wp_trash_post", "wp_delete_term"]:
            self.assertNotIn(word, src)


if __name__ == "__main__":
    unittest.main()
