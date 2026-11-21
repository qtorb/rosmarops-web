"""Tests for wp/mu-plugins/rosmarops-gtm198-enlace.php: one line at the end of the 21-11 post.

Run from the repository root:  python3 -m unittest wp/tests/test_gtm198_enlace.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": ("https://rosmarops.com", 1258, "when-one-agent-puts-other-agents-to-work", '<a href="/agent-orchestrators/">'),
         "es": ("https://rosmarops.com/es", 1248, "cuando-un-agente-pone-a-trabajar-a-otros-agentes", '<a href="/es/orquestadores-de-agentes/">'),
         "ca": ("https://rosmarops.com/ca", 101, "quan-un-agent-posa-a-treballar-altres-agents", '<a href="/ca/orquestradors-dagents/">')}
BODY = ('<!-- wp:paragraph -->\n<p>Last paragraph.</p>\n<!-- /wp:paragraph -->\n\n'
        '<!-- wp:image {"sizeSlug":"large"} -->\n<figure><a href="https://youtu.be/2IKYyCEKZ0E"><img src="x.jpg"/></a></figure>\n<!-- /wp:image -->\n')


def post(pid, slug, status="publish", ptype="post", content=BODY):
    return {"ID": pid, "post_name": slug, "post_type": ptype, "post_status": status, "post_content": content,
            "post_date": "2026-11-21 17:00:00", "post_modified": "2026-11-21 17:00:00"}


class Gtm198(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "content"
        os.mkdir(self.content)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, posts, options=None):
        self.db.write_text(json.dumps({"options": options or {}, "posts": posts}))
        env = dict(os.environ, GTM198_DB=str(self.db), GTM198_CONTENT=str(self.content))
        out = subprocess.run(["php", str(TESTS / "gtm198-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def test_line_goes_at_the_end_and_nothing_else_changes(self):
        for lang, (home, pid, slug, href) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, [post(pid, slug), post(7, "other")])
                p = next(x for x in db["posts"] if x["ID"] == pid)
                self.assertTrue(p["post_content"].startswith(BODY.rstrip()))
                tail = p["post_content"][len(BODY.rstrip()):]
                self.assertTrue(tail.startswith("\n\n<!-- wp:paragraph {\"className\":\"rosmarops-gtm198\"} -->"))
                self.assertIn(href, tail)
                self.assertTrue(tail.endswith("<!-- /wp:paragraph -->\n"))
                self.assertEqual(p["post_date"], "2026-11-21 17:00:00")
                self.assertEqual(p["post_modified"], "2026-11-21 17:00:00")
                self.assertEqual(next(x for x in db["posts"] if x["ID"] == 7), post(7, "other"))
                self.assertTrue(log[-1].startswith("done:"))
                self.assertTrue((self.content / "rosmarops-private" / f"gtm198-{lang}.log").exists())

    def test_leaves_alone_anything_unexpected(self):
        home, pid, slug, _ = SITES["es"]
        for p in (post(pid, slug, "draft"), post(pid, slug + "-2"), post(pid, slug, ptype="page")):
            with self.subTest(p=p["post_status"] + p["post_name"] + p["post_type"]):
                log, db = self.run_with(home, [p])
                self.assertEqual(db["posts"], [p])
                self.assertTrue(log[-1].startswith("skipped:"))

    def test_never_twice(self):
        home, pid, slug, _ = SITES["en"]
        _, db = self.run_with(home, [post(pid, slug)])
        once = db["posts"][0]["post_content"]
        log, db = self.run_with(home, [post(pid, slug, content=once)])
        self.assertEqual(db["posts"][0]["post_content"], once)
        self.assertIn("already has the line", log[-1])
        _, db = self.run_with(home, [post(pid, slug)], options={"rosmarops_gtm198_done": "x"})
        self.assertEqual(db["posts"][0]["post_content"], BODY)

    def test_other_sites_do_nothing(self):
        p = post(1258, SITES["en"][2])
        log, db = self.run_with("https://rosmarops.com/fr", [p])
        self.assertIsNone(log)
        self.assertEqual(db["posts"], [p])


if __name__ == "__main__":
    unittest.main()
