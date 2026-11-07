"""Tests for wp/mu-plugins/rosmarops-gtm103-noindex.php: the 27 legacy posts and the old categories to noindex, once, on /es/.

Run from the repository root:  python3 -m unittest wp/tests/test_gtm103_noindex.py   (needs php on PATH)
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PLUGINS = TESTS.parent / "mu-plugins"
RETIRED = re.findall(r"^\t'([^']+)',$", (PLUGINS / "rosmarops-retired.php").read_text(encoding="utf-8"), re.M)
PRODUCT = re.findall(r"'([a-z0-9-]+)'", (PLUGINS / "rosmarops-gtm103-noindex.php").read_text(encoding="utf-8")
                     .split("ROSMAROPS_GTM103_PRODUCT = [")[1].split("];")[0])
LEGACY = [f"legacy-post-{i}" for i in range(27)]
ES = "https://rosmarops.com/es"


def db(legacy=LEGACY):
    posts, n = [], 0
    for s in PRODUCT + legacy:
        n += 1
        posts.append({"ID": n, "post_name": s, "post_type": "post", "post_status": "publish"})
    for s in RETIRED[:5]:  # group 3: drafts since GTM-97
        n += 1
        posts.append({"ID": n, "post_name": s, "post_type": "post", "post_status": "draft"})
    terms = [{"term_id": 1, "slug": "novedades-de-rosmarops", "count": 3}, {"term_id": 3, "slug": "nota-de-exposicion", "count": 4},
             {"term_id": 7, "slug": "seguridad-llm", "count": 6}, {"term_id": 8, "slug": "seo-adversarial", "count": 0},
             {"term_id": 9, "slug": "sin-categoria", "count": 0}]
    return {"options": {"default_category": 9}, "posts": posts, "postmeta": {"3": {"_genesis_title": "x"}},
            "terms": terms, "termmeta": {"7": {"autodescription-term-settings": {"title": "keep"}}}}


class Noindex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbf = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "wp-content"
        self.content.mkdir()

    def run_once(self, data=None, home=ES):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, GTM103_DB=str(self.dbf), GTM103_CONTENT=str(self.content))
        p = subprocess.run(["php", str(TESTS / "gtm103-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    @staticmethod
    def noindex(d, slug):
        pid = next(p["ID"] for p in d["posts"] if p["post_name"] == slug)
        return d["postmeta"].get(str(pid), {}).get("_genesis_noindex")

    def test_product_list_matches_gtm97(self):
        gtm97 = re.findall(r"'([a-z0-9-]+)'", (PLUGINS / "rosmarops-gtm97-drafts.php").read_text(encoding="utf-8")
                           .split("ROSMAROPS_GTM97_PRODUCT = [")[1].split("];")[0])
        self.assertEqual(PRODUCT, gtm97)

    def test_first_run(self):
        log, out = self.run_once(db())
        for s in LEGACY:
            self.assertEqual(self.noindex(out, s), 1, s)
        for s in PRODUCT:
            self.assertIsNone(self.noindex(out, s), s)
        self.assertEqual(out["postmeta"]["3"]["_genesis_title"], "x")  # other meta untouched
        tm = out["termmeta"]
        self.assertEqual(tm["7"]["autodescription-term-settings"], {"title": "keep", "noindex": 1})
        self.assertEqual(tm["8"]["autodescription-term-settings"], {"noindex": 1})
        self.assertNotIn("1", tm)  # blog categories stay indexable
        self.assertNotIn("3", tm)
        self.assertNotIn("9", tm)  # the default category is not touched
        self.assertIn("total: 27 posts and 2 categories marked noindex", log)
        self.assertIn("skipped: category sin-categoria is the site's default category", log)
        self.assertEqual(out["options"]["sitemap_cleared"], "tsf5")
        self.assertIn("rosmarops_gtm103_done", out["options"])
        self.assertNotIn("rosmarops_gtm103_lock", out["options"])
        self.assertEqual(all(p["post_status"] in ("publish", "draft") for p in out["posts"]), True)
        self.assertEqual(len(out["posts"]), len(PRODUCT) + 27 + 5)  # nothing deleted
        self.assertEqual((self.content / "rosmarops-private" / "gtm103-es.log").read_text(encoding="utf-8").splitlines(), log)
        self.assertEqual((self.content / "rosmarops-private" / ".htaccess").read_text(), "Require all denied\n")

    def test_second_run_changes_nothing(self):
        _, first = self.run_once(db())
        log, second = self.run_once()
        self.assertIsNone(log)
        self.assertEqual(first, second)

    def test_unexpected_count_changes_nothing(self):
        log, out = self.run_once(db(LEGACY + ["a-new-product-post"]))
        self.assertEqual(log[1], "stopped: 28 legacy posts found, 27 expected; nothing changed")
        self.assertIn("found: a-new-product-post", log)
        self.assertEqual(out["termmeta"], db()["termmeta"])
        self.assertNotIn("_genesis_noindex", json.dumps(out["postmeta"]))
        self.assertNotIn("rosmarops_gtm103_done", out["options"])  # runs again once the list is right

    def test_other_sites_and_recent_lock(self):
        self.assertIsNone(self.run_once(db(), home="https://rosmarops.com/")[0])
        d = db()
        d["options"]["rosmarops_gtm103_lock"] = 9999999999
        log, out = self.run_once(d)
        self.assertIsNone(log)
        self.assertNotIn("_genesis_noindex", json.dumps(out["postmeta"]))


if __name__ == "__main__":
    unittest.main()
