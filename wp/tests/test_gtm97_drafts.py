"""Tests for wp/mu-plugins/rosmarops-gtm97-drafts.php: group 3 of the legacy blog to draft, once, on /es/ (GTM-97).

Run from the repository root:  python3 -m unittest wp/tests/test_gtm97_drafts.py   (needs php on PATH)
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
RETIRED = re.findall(r"^\t'([^']+)',$", (TESTS.parent / "mu-plugins" / "rosmarops-retired.php").read_text(encoding="utf-8"), re.M)
PAGES = {"guerra-de-la-informacion-iw", "ai-seo", "ciberseguridad-en-ia", "seo-adversarial", "agentes-autonomia"}
ES = "https://rosmarops.com/es"


def db():
    posts, n = [], 0
    for s in RETIRED:
        n += 1
        posts.append({"ID": n, "post_name": s, "post_type": "page" if s in PAGES else "post", "post_status": "publish"})
    for s in ("mi-maquina-saco-un-18-de-100", "que-es-rosmarops", "mcp-seguridad-agentes-cadena-suministro-confianza"):
        n += 1
        posts.append({"ID": n, "post_name": s, "post_type": "page" if s == "que-es-rosmarops" else "post", "post_status": "publish"})
    return {"options": {}, "posts": posts}


class Drafts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbf = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "wp-content"
        self.content.mkdir()

    def run_once(self, data=None, home=ES, mode="tsf5"):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, GTM97_DB=str(self.dbf), GTM97_CONTENT=str(self.content))
        p = subprocess.run(["php", str(TESTS / "gtm97-stub.php"), home, mode], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    @staticmethod
    def status(d, slug):
        return next(p["post_status"] for p in d["posts"] if p["post_name"] == slug)

    def test_list_is_the_signed_one(self):
        self.assertEqual(len(RETIRED), 90)

    def test_first_run(self):
        log, out = self.run_once(db())
        for s in RETIRED:
            self.assertEqual(self.status(out, s), "draft", s)
        for s in ("mi-maquina-saco-un-18-de-100", "que-es-rosmarops", "mcp-seguridad-agentes-cadena-suministro-confianza"):
            self.assertEqual(self.status(out, s), "publish", s)
        self.assertEqual(len(out["posts"]), 93)  # nothing deleted
        self.assertEqual(sum(l.startswith("done: ") for l in log), 90)
        self.assertIn("done: ai-seo (page) publish -> draft", log)
        self.assertIn("total: 90 turned to draft, 90 in the list", log)
        self.assertIn("sitemap: cache cleared (The SEO Framework 5, Sitemap\\Cache::clear_sitemap_caches)", log)
        self.assertEqual(out["options"]["sitemap_cleared"], "tsf5")
        self.assertEqual((self.content / "rosmarops-private" / "gtm97-es.log").read_text(encoding="utf-8").splitlines(), log)
        self.assertIn("rosmarops_gtm97_done", out["options"])
        self.assertNotIn("rosmarops_gtm97_lock", out["options"])

    def test_second_run_changes_nothing(self):
        _, first = self.run_once(db())
        log, second = self.run_once()
        self.assertIsNone(log)
        self.assertEqual(first, second)

    def test_draft_missing_and_product(self):
        d = db()
        d["posts"][0]["post_status"] = "draft"
        gone = d["posts"].pop(1)["post_name"]
        log, out = self.run_once(d)
        self.assertIn(f"skipped: {d['posts'][0]['post_name']} (post) is draft; left as it is", log)
        self.assertIn(f"skipped: {gone} not found", log)
        self.assertIn("total: 88 turned to draft, 90 in the list", log)
        self.assertEqual(self.status(out, "mi-maquina-saco-un-18-de-100"), "publish")
        self.assertEqual(len(out["posts"]), 92)

    def test_only_on_the_spanish_site(self):
        for home in ("https://rosmarops.com", "https://rosmarops.com/ca"):
            log, out = self.run_once(db(), home=home)
            self.assertIsNone(log)
            self.assertTrue(all(p["post_status"] == "publish" for p in out["posts"]))

    def test_recent_lock_waits(self):
        d = db()
        d["options"]["rosmarops_gtm97_lock"] = 9999999999
        log, out = self.run_once(d)
        self.assertIsNone(log)
        self.assertEqual(self.status(out, RETIRED[0]), "publish")

    def test_without_tsf5_falls_back(self):
        log, _ = self.run_once(db(), mode="none")
        self.assertEqual(log[-1], "sitemap: not cleared (no The SEO Framework API found)")


if __name__ == "__main__":
    unittest.main()
