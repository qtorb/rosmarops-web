"""Tests for wp/mu-plugins/rosmarops-gtm164-sin-version.php: the 14-11 news post loses the program version in its
title, SEO title and address, with a redirect from the old one (GTM-164).

Run from the repository root:  python3 -m unittest wp/tests/test_gtm164_sin_version.py   (needs php on PATH)
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
DRAFTS = TESTS.parent / "drafts"
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
VERSION = re.compile(r"(?<![\d.,])v?\d{1,2}\.\d{1,2}(\.\d{1,3})?(?![\d.,]?\d)|(^|-)v?\d{1,2}-\d{1,2}(-\d{1,3})?(-|$)")


class Gtm164(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dbf = root / "db.json"
        self.content = root / "wp-content"
        self.content.mkdir()

    def db(self, status="publish", extra=()):
        posts = [{"ID": 50, "post_name": "rosmarops-0-11", "post_type": "post", "post_status": status,
                  "post_title": "RosmarOps 0.11.6: …", "post_content": "<p>body</p>"}] + list(extra)
        return {"options": {}, "posts": posts, "post_meta": {}, "cleaned": []}

    def run_once(self, home, data=None):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, GTM164_DB=str(self.dbf), GTM164_CONTENT=str(self.content))
        p = subprocess.run(["php", str(TESTS / "gtm164-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    def test_each_site_matches_the_draft_and_keeps_the_old_address(self):
        drafts = {l: json.loads((DRAFTS / f"novedades-0-11-{l}.json").read_text(encoding="utf-8")) for l in SITES}
        for lang, home in SITES.items():
            log, out = self.run_once(home, self.db())
            p, meta, d = out["posts"][0], out["post_meta"]["50"], drafts[lang]
            self.assertEqual((p["post_title"], p["post_name"], p["post_content"]), (d["title"], d["slug"], "<p>body</p>"), lang)
            self.assertEqual(meta["_genesis_title"], d["seo_title"], lang)
            self.assertEqual(meta["_wp_old_slug"], ["rosmarops-0-11"], lang)
            self.assertEqual({k[len("rosmarops_url_"):]: v for k, v in meta.items() if k.startswith("rosmarops_url_")},
                             d["translations"], lang)
            for text in (p["post_title"], p["post_name"], meta["_genesis_title"]):
                self.assertIsNone(VERSION.search(text), (lang, text))
            self.assertEqual(out["cleaned"], [50])
            self.assertTrue((self.content / "rosmarops-private" / f"gtm164-{lang}.log").is_file())

    def test_runs_once(self):
        self.run_once(SITES["es"], self.db())
        log, out = self.run_once(SITES["es"])
        self.assertIsNone(log)

    def test_leaves_alone(self):
        log, out = self.run_once(SITES["es"], self.db(status="draft"))
        self.assertTrue(any(l.startswith("skipped:") for l in log))
        self.assertEqual(out["posts"][0]["post_name"], "rosmarops-0-11")
        taken = {"ID": 60, "post_name": "novedades-de-rosmarops-noviembre-2026", "post_type": "page", "post_status": "publish"}
        log, out = self.run_once(SITES["es"], self.db(extra=[taken]))
        self.assertTrue(any("already used" in l for l in log))
        self.assertEqual(out["posts"][0]["post_name"], "rosmarops-0-11")
        log, out = self.run_once(SITES["es"], {"options": {}, "posts": [], "post_meta": {}, "cleaned": []})
        self.assertIn("skipped: 0 posts with slug rosmarops-0-11, 1 expected", log)

    def test_other_site_does_nothing(self):
        log, _ = self.run_once("https://example.com", self.db())
        self.assertIsNone(log)


if __name__ == "__main__":
    unittest.main()
