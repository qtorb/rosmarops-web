"""Tests for wp/mu-plugins/rosmarops-gtm124-agente.php: «agent», not «assistant», in two credit lines per site (GTM-124).

Run from the repository root:  python3 -m unittest wp/tests/test_gtm124_agente.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
# The credit lines as they are in the published posts (09-11), and what they must become: only that word changes.
POSTS = {
    "en": [("loop-engineering-agents-working-alone",
            "Written with the help of AI assistants. The reading of the study, the examples and the decision to publish are mine.",
            "Written with the help of AI agents. The reading of the study, the examples and the decision to publish are mine."),
           ("what-wasnt-read-doesnt-count-as-clean", "I wrote this with AI assistants. The machine, the",
            "I wrote this with AI agents. The machine, the")],
    "es": [("loop-engineering-agentes-trabajando-solos", "Escrito con ayuda de asistentes de IA. La interpretación",
            "Escrito con ayuda de agentes de IA. La interpretación"),
           ("lo-que-no-se-leyo-no-cuenta-como-limpio", "Escrito con asistentes de IA. La máquina",
            "Escrito con agentes de IA. La máquina")],
    "ca": [("loop-engineering-agents-treballant-sols", "Escrit amb l'ajuda d'assistents d'IA. La interpretació",
            "Escrit amb l'ajuda d'agents d'IA. La interpretació"),
           ("el-que-no-sha-llegit-no-compta-com-a-net", "Ho he escrit amb assistents d’IA. La màquina",
            "Ho he escrit amb agents d’IA. La màquina")],
}
BLOG_OLD = ("Notes from building RosmarOps: what AI coding agents like Claude Code and Cursor can reach on your machine, "
            "how the Agent Posture Score works, and what I learn along the way.")
BLOG_NEW = ("Notes from building RosmarOps: what AI coding agents like Claude Code and Cursor can reach on your machine, "
            "and how the Agent Posture Score works.")
BODY = '<!-- wp:paragraph -->\n<p>Body with Claude Code and an agent.</p>\n<!-- /wp:paragraph -->\n<p class="wp-block-paragraph"><em>{}</em></p>'


class Gtm124(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dbf = root / "db.json"
        self.content = root / "wp-content"
        self.content.mkdir()

    def db(self, lang, status="publish", texts=None, blog=BLOG_OLD):
        posts = [{"ID": 10 + i, "post_name": slug, "post_type": "post", "post_status": status,
                  "post_content": BODY.format((texts or {}).get(slug, old))} for i, (slug, old, _) in enumerate(POSTS[lang])]
        posts.append({"ID": 81, "post_name": "blog", "post_type": "page", "post_status": "publish", "post_content": ""})
        return {"options": {}, "posts": posts, "post_meta": {"81": {"_genesis_description": blog}}, "cleaned": []}

    def run_once(self, home, data=None, env_extra=None):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, GTM124_DB=str(self.dbf), GTM124_CONTENT=str(self.content))
        env.update(env_extra or {})
        p = subprocess.run(["php", str(TESTS / "gtm124-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    def test_each_site_changes_only_the_word(self):
        for lang, home in SITES.items():
            log, out = self.run_once(home, self.db(lang))
            for (slug, _, new), p in zip(POSTS[lang], out["posts"]):
                self.assertEqual(p["post_content"], BODY.format(new), (lang, slug))
                self.assertIn(f"post done: {slug}", log)
            self.assertEqual(out["cleaned"], [10, 11])
            desc = out["post_meta"]["81"]["_genesis_description"]
            self.assertEqual(desc, BLOG_NEW if lang == "en" else BLOG_OLD, lang)
            self.assertTrue((self.content / "rosmarops-private" / f"gtm124-{lang}.log").is_file())

    def test_html_entity_apostrophe(self):
        slug = POSTS["ca"][1][0]
        log, out = self.run_once(SITES["ca"], self.db("ca", texts={slug: "Ho he escrit amb assistents d&#8217;IA."}))
        self.assertIn("Ho he escrit amb agents d&#8217;IA.", out["posts"][1]["post_content"])

    def test_runs_once(self):
        self.run_once(SITES["es"], self.db("es"))
        log, out = self.run_once(SITES["es"])
        self.assertIsNone(log)

    def test_other_site_untouched(self):
        log, out = self.run_once("https://example.com", self.db("en"))
        self.assertIsNone(log)
        self.assertIn("AI assistants", out["posts"][0]["post_content"])

    def test_leaves_alone_when_not_exactly_one(self):
        slug = POSTS["en"][0][0]
        twice = "Written with AI assistants and other assistants."
        log, out = self.run_once(SITES["en"], self.db("en", texts={slug: twice}))
        self.assertEqual(out["posts"][0]["post_content"], BODY.format(twice))
        self.assertTrue(any(l.startswith("skipped: the word appears 2 times") for l in log), log)
        self.assertIn(f"post done: {POSTS['en'][1][0]}", log)

    def test_leaves_alone_when_other_phrase(self):
        slug = POSTS["es"][0][0]
        other = "Escrito con un asistente de voz."
        log, out = self.run_once(SITES["es"], self.db("es", texts={slug: other}))
        self.assertEqual(out["posts"][0]["post_content"], BODY.format(other))
        self.assertTrue(any(l.startswith("skipped: the word is not in the expected phrase") for l in log), log)

    def test_drafts_untouched(self):
        log, out = self.run_once(SITES["en"], self.db("en", status="draft"))
        self.assertTrue(all("is not published here" in l for l in log[1:3]), log)
        self.assertIn("AI assistants", out["posts"][0]["post_content"])

    def test_blog_description_only_if_previous(self):
        log, out = self.run_once(SITES["en"], self.db("en", blog="Something Albert wrote."))
        self.assertEqual(out["post_meta"]["81"]["_genesis_description"], "Something Albert wrote.")
        self.assertIn("skipped: /blog/ description is not the expected previous text", log)

    def test_write_failure_logged(self):
        log, out = self.run_once(SITES["en"], self.db("en"), {"GTM124_WRITE_FAIL": "1"})
        self.assertTrue(any(l.startswith("failed: post") for l in log), log)

    def test_new_blog_description_length(self):
        self.assertLessEqual(len(BLOG_NEW), 155)
        self.assertIn(BLOG_NEW, (TESTS.parent / "mu-plugins" / "rosmarops-gtm124-agente.php").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
