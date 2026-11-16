"""Tests for wp/mu-plugins/rosmarops-menu-sandbox.php: «Sandbox» in the blog menu and the link in the sandbox post (GTM-175).

Run from the repository root:  python3 -m unittest wp/tests/test_menu_sandbox.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {
    "en": ("https://rosmarops.com", "/observatory/", "/methodology/", "/sandbox/", "sandbox-ai-agents", "All about sandboxes"),
    "es": ("https://rosmarops.com/es", "/es/observatorio/", "/es/metodologia/", "/es/sandbox/", "sandbox-agentes-de-ia", "Todo sobre el sandbox"),
    "ca": ("https://rosmarops.com/ca", "/ca/observatori/", "/ca/metodologia/", "/ca/sandbox/", "sandbox-agents-dia", "Tot sobre el sandbox"),
}
BODY = "<!-- wp:paragraph -->\n<p>Escrito con ayuda de agentes de IA.</p>\n<!-- /wp:paragraph -->"


def menu(obs, meth, lang_blog="/es/blog/"):
    return [
        {"ID": 1, "menu": 5, "url": "https://rosmarops.com" + lang_blog, "menu_order": 1, "menu_item_parent": 0},
        {"ID": 2, "menu": 5, "url": "https://rosmarops.com" + obs, "menu_order": 2, "menu_item_parent": 0},
        {"ID": 3, "menu": 5, "url": "https://rosmarops.com" + meth, "menu_order": 3, "menu_item_parent": 0},
        {"ID": 4, "menu": 5, "url": "https://rosmarops.com/faq/", "menu_order": 4, "menu_item_parent": 0},
    ]


class Menu7(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, items, posts, locations=None, options=None):
        self.db.write_text(json.dumps({"options": options or {}, "locations": {"primary": 5} if locations is None else locations,
                                       "menu_items": items, "posts": posts}))
        env = dict(os.environ, MENU7_DB=str(self.db), MENU7_CONTENT=str(Path(self.tmp.name) / "content"))
        out = subprocess.run(["php", str(TESTS / "menu7-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def post(self, slug, pid=10, status="publish"):
        return {"ID": pid, "post_name": slug, "post_type": "post", "post_status": status, "post_content": BODY}

    def order(self, db):
        return [(i["url"].replace("https://rosmarops.com", ""), i["menu_order"]) for i in sorted(db["menu_items"], key=lambda i: i["menu_order"])]

    def test_each_site_gets_the_item_and_the_link(self):
        for lang, (home, obs, meth, sec, slug, label) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, menu(obs, meth), [self.post(slug), self.post("other", pid=11)])
                urls = [u for u, _ in self.order(db)]
                self.assertEqual(urls[1:4], [obs, sec, meth])
                self.assertEqual([o for _, o in self.order(db)], [1, 2, 3, 4, 5])
                new = next(i for i in db["menu_items"] if i["url"].endswith(sec))
                self.assertEqual(new["title"], "Sandbox")
                self.assertTrue(db["posts"][0]["post_content"].endswith(
                    f'<p><a href="{sec}">{label}</a></p>\n<!-- /wp:paragraph -->'))
                self.assertTrue(db["posts"][0]["post_content"].startswith(BODY))
                self.assertEqual(db["posts"][1]["post_content"], BODY)
                self.assertTrue(log[1].startswith("menu done:") and log[2].startswith("post done:"), log)
                self.assertIn("rosmarops_menu7_done", db["options"])
                self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / f"menu7-{lang}.log").exists())

    def test_runs_once(self):
        home, obs, meth, sec, slug, _ = SITES["es"]
        log, db = self.run_with(home, menu(obs, meth), [self.post(slug)], options={"rosmarops_menu7_done": "x"})
        self.assertEqual(len(db["menu_items"]), 4)
        self.assertEqual(db["posts"][0]["post_content"], BODY)

    def test_already_there(self):
        home, obs, meth, sec, slug, _ = SITES["es"]
        items = menu(obs, meth) + [{"ID": 9, "menu": 5, "url": "/es/sandbox/", "menu_order": 9, "menu_item_parent": 0}]
        p = self.post(slug)
        p["post_content"] += f'\n<p><a href="{sec}">x</a></p>'
        log, db = self.run_with(home, items, [p])
        self.assertEqual(len(db["menu_items"]), 5)
        self.assertTrue(log[1].startswith("menu skipped:") and log[2].startswith("post skipped:"), log)
        self.assertEqual(db["posts"][0]["post_content"].count(sec), 1)

    def test_no_menu_or_wrong_order_or_no_post(self):
        home, obs, meth, sec, slug, _ = SITES["ca"]
        log, db = self.run_with(home, menu(obs, meth), [self.post(slug + "-2")], locations={})
        self.assertTrue(log[1].startswith("menu skipped: no menu"), log)
        self.assertTrue(log[2].startswith("post skipped: 0 published"), log)
        self.assertEqual(len(db["menu_items"]), 4)
        log, db = self.run_with(home, menu(meth, obs), [self.post(slug, status="draft")])
        self.assertTrue(log[1].startswith("menu skipped:"), log)
        self.assertEqual([o for _, o in self.order(db)], [1, 2, 3, 4])

    def test_other_sites_do_nothing(self):
        log, db = self.run_with("https://example.com", menu("/observatory/", "/methodology/"), [self.post("sandbox-ai-agents")])
        self.assertEqual(log, [])
        self.assertFalse(db["options"])


if __name__ == "__main__":
    unittest.main()
