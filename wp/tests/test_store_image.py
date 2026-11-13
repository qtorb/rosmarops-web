"""Tests for wp/mu-plugins/rosmarops-store-image.php: the Microsoft Store post gets its featured image, once per site.

Run from the repository root:  python3 -m unittest wp/tests/test_store_image.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
DRAFTS = TESTS.parent / "drafts"
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
SLUG = "rosmarops-microsoft-store"
IMG = "rosmarops-img-18-microsoft-store.jpg"


class StoreImage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "content").mkdir()
        self.db = self.root / "db.json"

    def state(self, posts, meta=None, options=None):
        self.db.write_text(json.dumps({"options": options or {}, "posts": posts, "meta": meta or {}}), encoding="utf-8")

    def run_site(self, home, drafts=DRAFTS):
        env = dict(os.environ, STOREIMG_DB=str(self.db), STOREIMG_CONTENT=str(self.root / "content"), STOREIMG_DRAFTS=str(drafts))
        out = subprocess.run(["php", str(TESTS / "storeimg-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text(encoding="utf-8"))

    def test_the_image_is_there_and_is_a_jpeg(self):
        self.assertEqual((DRAFTS / IMG).read_bytes()[:3], b"\xff\xd8\xff")

    def test_each_site_sets_it_once_with_its_alt(self):
        alts = set()
        for lang, home in SITES.items():
            self.state([{"ID": 77, "post_name": SLUG, "post_status": "publish"}])
            log, db = self.run_site(home)
            self.assertTrue(log[-1].startswith("done: attachment 900 is the featured image of post 77"), (lang, log))
            self.assertEqual(db["meta"]["77"]["_thumbnail_id"], 900)
            self.assertEqual(db["attachments"], [{"ID": 900, "file": "uploads-" + IMG, "parent": 77}])
            alt = db["meta"]["900"]["_wp_attachment_image_alt"]
            self.assertIn("Microsoft Store", alt)
            alts.add(alt)
            self.assertIn("rosmarops_storeimg_done", db["options"])
            self.assertNotIn("rosmarops_storeimg_lock", db["options"])
            self.assertTrue((self.root / "content" / "rosmarops-private" / f"storeimg-{lang}.log").exists())
            again, db2 = self.run_site(home)  # a second request does nothing
            self.assertEqual(len(db2["attachments"]), 1)
        self.assertEqual(len(alts), 3)

    def test_a_post_with_a_featured_image_is_left_alone(self):
        self.state([{"ID": 77, "post_name": SLUG, "post_status": "publish"}], meta={"77": {"_thumbnail_id": 5}})
        log, db = self.run_site(SITES["es"])
        self.assertIn("already has a featured image", log[-1])
        self.assertEqual(db["meta"]["77"]["_thumbnail_id"], 5)
        self.assertNotIn("attachments", db)

    def test_no_post_or_two_posts_are_skipped(self):
        for posts in ([], [{"ID": 1, "post_name": SLUG, "post_status": "publish"}, {"ID": 2, "post_name": SLUG, "post_status": "draft"}]):
            self.state(posts)
            log, db = self.run_site(SITES["en"])
            self.assertTrue(log[-1].startswith(f"skipped: {len(posts)} posts with slug"), log)
            self.assertNotIn("attachments", db)

    def test_other_sites_do_nothing(self):
        self.state([{"ID": 77, "post_name": SLUG, "post_status": "publish"}])
        log, db = self.run_site("https://example.com")
        self.assertEqual(log, [])
        self.assertFalse(db["options"])  # PHP writes an empty object as []


if __name__ == "__main__":
    unittest.main()
