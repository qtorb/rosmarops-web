"""Tests for wp/mu-plugins/rosmarops-category-loop-engineering.php: the «Loop engineering» category, once per site.

Run from the repository root:  python3 -m unittest wp/tests/test_category_loop_engineering.py   (needs php on PATH)
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
PLUGIN = TESTS.parent / "mu-plugins" / "rosmarops-category-loop-engineering.php"
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
POSTS = {"en": "loop-engineering-agents-working-alone", "es": "loop-engineering-agentes-trabajando-solos",
         "ca": "loop-engineering-agents-treballant-sols"}
SIGNED = {
    "es": "Qué pasa cuando dejas a un agente de IA trabajando en bucle: qué lo pone en marcha, quién comprueba lo que hace, cuándo para y cuánto cuesta. Con estudios y casos fechados, y su fuente.",
    "ca": "Què passa quan deixes un agent d'IA treballant en bucle: què el posa en marxa, qui comprova el que fa, quan s'atura i quant costa. Amb estudis i casos datats, i la seva font.",
}


class LoopCategory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dbf = root / "db.json"
        self.content = root / "wp-content"
        self.content.mkdir()
        self.dir = root / "rosmarops-drafts"
        shutil.copytree(DRAFTS, self.dir)

    def db(self, lang, status="draft", cats=(1,), thumb=None, extra_terms=()):
        posts = [{"ID": 42, "post_name": POSTS[lang], "post_status": status, "cats": list(cats)}]
        return {"options": {"default_category": 1}, "terms": list(extra_terms), "term_meta": {}, "posts": posts,
                "thumbs": {"42": thumb} if thumb else {}, "uploads": [], "attachments": {}, "post_meta": {}}

    def run_once(self, home, data=None, env_extra=None):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, LOOPCAT_DB=str(self.dbf), LOOPCAT_CONTENT=str(self.content), LOOPCAT_DIR=str(self.dir))
        env.update(env_extra or {})
        p = subprocess.run(["php", str(TESTS / "loopcat-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    def test_signed_descriptions(self):
        src = PLUGIN.read_text(encoding="utf-8")
        for lang, text in SIGNED.items():
            self.assertIn(text.replace("'", "\\'") if lang == "es" else text, src, lang)

    def test_each_site(self):
        for lang, home in SITES.items():
            log, out = self.run_once(home, self.db(lang))
            term = next(t for t in out["terms"] if t.get("taxonomy", "category") == "category")
            self.assertEqual((term["name"], term["slug"]), ("Loop engineering", "loop-engineering"))
            if lang in SIGNED:
                self.assertEqual(term["description"], SIGNED[lang])
            tsf = out["term_meta"][str(term["term_id"])]["autodescription-term-settings"]
            self.assertEqual(tsf["noindex"], 1)
            self.assertTrue(40 <= len(tsf["description"]) <= 155, (lang, len(tsf["description"])))
            self.assertTrue(tsf["description"].startswith({"en": "What happens", "es": "Qué pasa", "ca": "Què passa"}[lang]))
            self.assertEqual(out["posts"][0]["cats"], [term["term_id"]])  # default category gone
            self.assertEqual(out["posts"][0]["post_status"], "publish")  # Albert, 08-11: «ya puedes publicar»
            self.assertEqual(out["posts"][0]["post_date_gmt"], "2026-11-08 22:00:00")
            tags = {t["term_id"]: t["slug"] for t in out["terms"] if t.get("taxonomy") == "post_tag"}
            self.assertEqual(sorted(tags[i] for i in out["posts"][0]["tags"]), ["claude-code", "codex"])
            att = out["thumbs"]["42"]
            self.assertEqual(out["uploads"][0][0], "rosmarops-img-13-loop-engineering.jpg")
            self.assertTrue(out["post_meta"][str(att)]["_wp_attachment_image_alt"])
            self.assertEqual(log[0].split(",")[0], "Loop engineering category")
            self.assertTrue(any(l.startswith("D done") for l in log), log)
            self.assertTrue((self.content / "rosmarops-private" / f"loopcat-{lang}.log").is_file())

    def test_runs_once(self):
        self.run_once(SITES["es"], self.db("es"))
        log, out = self.run_once(SITES["es"])
        self.assertIsNone(log)
        self.assertEqual(len(out["terms"]), 3)  # the category and the two tags
        self.assertEqual(len(out["uploads"]), 1)

    def test_existing_category_kept_and_other_categories_kept(self):
        mine = {"term_id": 7, "name": "Mine", "slug": "loop-engineering", "description": "theirs"}
        log, out = self.run_once(SITES["ca"], self.db("ca", cats=[1, 19], extra_terms=[mine]))
        self.assertEqual([t for t in out["terms"] if t.get("taxonomy", "category") == "category"], [mine])
        self.assertEqual(sorted(out["posts"][0]["cats"]), [7, 19])

    def test_meta_description_never_replaced(self):
        mine = {"term_id": 7, "name": "Loop engineering", "slug": "loop-engineering", "description": "x"}
        data = self.db("es", extra_terms=[mine])
        data["term_meta"] = {"7": {"autodescription-term-settings": {"description": "la mía"}}}
        log, out = self.run_once(SITES["es"], data)
        self.assertEqual(out["term_meta"]["7"]["autodescription-term-settings"]["description"], "la mía")
        self.assertIn("B2 skipped: meta description already set; not replaced", log)

    def test_featured_image_never_replaced(self):
        log, out = self.run_once(SITES["en"], self.db("en", thumb=77))
        self.assertEqual(out["thumbs"]["42"], 77)
        self.assertEqual(out["uploads"], [])

    def test_missing_post_still_creates_the_category(self):
        data = self.db("es")
        data["posts"] = []
        log, out = self.run_once(SITES["es"], data)
        self.assertEqual(len(out["terms"]), 1)
        self.assertIn("not found", log[-1])
        self.assertEqual(out["posts"], [])

    def test_failed_category_runs_again(self):
        log, out = self.run_once(SITES["en"], self.db("en"), {"LOOPCAT_TERM_FAIL": "1"})
        self.assertNotIn("rosmarops_loopcat_done", out["options"])
        log, out = self.run_once(SITES["en"])
        self.assertEqual(len([t for t in out["terms"] if t.get("taxonomy", "category") == "category"]), 1)

    def test_other_hosts_do_nothing(self):
        for home in ["https://rosmarops.com/fr", "https://www.qtorb.com"]:
            log, out = self.run_once(home, self.db("en"))
            self.assertIsNone(log)
            self.assertEqual(out["terms"], [])

    def test_existing_tags_reused_and_kept(self):
        data = self.db("ca")
        data["terms"] = [{"term_id": 8, "slug": "claude-code", "name": "Claude Code", "taxonomy": "post_tag"}]
        data["posts"][0]["tags"] = [16]
        log, out = self.run_once(SITES["ca"], data)
        self.assertIn("E done: tag codex created", log)
        self.assertNotIn("E done: tag claude-code created", log)
        self.assertEqual(out["posts"][0]["tags"][:2], [16, 8])

    def test_only_a_draft_is_published(self):
        for status in ("publish", "pending", "future", "private"):
            log, out = self.run_once(SITES["es"], self.db("es", status=status))
            self.assertEqual(out["posts"][0]["post_status"], status)
            self.assertIn(f"F skipped: post 42 is {status}; left as it is", log)

    def test_never_deletes_or_creates_posts(self):
        src = PLUGIN.read_text(encoding="utf-8")
        for word in ["wp_publish_post", "wp_delete_post", "wp_delete_term", "wp_trash_post", "wp_insert_post"]:
            self.assertNotIn(word, src)
        self.assertEqual(src.count("wp_update_post("), 1)


if __name__ == "__main__":
    unittest.main()
