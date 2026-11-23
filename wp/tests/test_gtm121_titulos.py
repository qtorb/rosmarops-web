"""Tests for wp/mu-plugins/rosmarops-gtm121-titulos.php: the Google title and description of two posts.

Run from the repository root:  python3 -m unittest wp/tests/test_gtm121_titulos.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {
    "en": ("https://rosmarops.com", 1200, "can-one-ai-agent-change-another-agents-configuration",
           "Can one AI agent rewrite another agent's settings?",
           "Yes, if it can write where the other keeps its settings or instructions. Where Claude Code, Cursor and Hermes "
           "Agent keep theirs on Windows, and who asks first."),
    "es": ("https://rosmarops.com/es", 1100, "modo-auto-claude-code-que-puede-leer",
           "Modo auto de Claude Code: qué aprueba sin ti y cómo acotarlo",
           "Las versiones recientes de Claude Code arrancan en modo auto: otro modelo de IA aprueba lo que antes te "
           "preguntaba. Qué sigue preguntando y cómo acotarlo."),
}


def post(pid, slug, status="publish", ptype="post"):
    return {"ID": pid, "post_name": slug, "post_type": ptype, "post_status": status, "post_title": "Old H1",
            "post_content": "<p>Body.</p>", "post_date": "2026-10-29 10:00:00", "post_modified": "2026-11-04 10:00:00"}


class Gtm121(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "content"
        os.mkdir(self.content)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, posts, options=None, meta=None):
        self.db.write_text(json.dumps({"options": options or {}, "posts": posts, "post_meta": meta or {}}))
        env = dict(os.environ, GTM121_DB=str(self.db), GTM121_CONTENT=str(self.content))
        out = subprocess.run(["php", str(TESTS / "gtm121-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def test_sets_only_the_google_title_and_description(self):
        for lang, (home, pid, slug, title, desc) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, [post(pid, slug), post(7, "other")],
                                        meta={str(pid): {"_genesis_description": "old"}})
                self.assertEqual(db["post_meta"][str(pid)], {"_genesis_title": title, "_genesis_description": desc})
                self.assertEqual(db["posts"], [post(pid, slug), post(7, "other")])  # H1, content, slug and dates as they were
                self.assertIn("description before: old", log)
                self.assertTrue(log[-1].startswith("done:"))
                self.assertTrue((self.content / "rosmarops-private" / f"gtm121-{lang}.log").exists())

    def test_texts_are_the_signed_ones_and_fit(self):
        for _, (_, _, _, title, desc) in SITES.items():
            self.assertLessEqual(len(title), 60)
            self.assertLessEqual(len(desc), 160)
            for w in ("seguro", "protege", "safe", "telemetr"):
                self.assertNotIn(w, (title + desc).lower())

    def test_leaves_alone_anything_unexpected(self):
        home, pid, slug, _, _ = SITES["es"]
        for posts in ([post(pid, slug, "draft")], [post(pid, slug + "-2")], [post(pid, slug), post(pid + 1, slug)]):
            with self.subTest(posts=posts):
                log, db = self.run_with(home, posts)
                self.assertTrue(log[-1].startswith("skipped:"))
                self.assertNotIn("post_meta", {k: v for k, v in db.items() if v})

    def test_once_per_site_and_nothing_on_ca(self):
        home, pid, slug, _, _ = SITES["en"]
        log, _ = self.run_with(home, [post(pid, slug)], options={"rosmarops_gtm121_done": "2026-11-23"})
        self.assertIsNone(log)
        log, db = self.run_with("https://rosmarops.com/ca", [post(pid, slug)])
        self.assertIsNone(log)
        self.assertFalse(db["post_meta"])


if __name__ == "__main__":
    unittest.main()
