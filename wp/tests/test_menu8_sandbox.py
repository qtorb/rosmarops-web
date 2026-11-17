"""Tests for wp/mu-plugins/rosmarops-menu8-sandbox.php: «Sandbox» in the blog menu, right after Observatory (GTM-175).

Run from the repository root:  python3 -m unittest wp/tests/test_menu8_sandbox.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
# The blog menus as read live on 16-11 (ids and order from the public HTML of /blog/, /es/blog/ and /ca/blog/).
SITES = {
    "en": ("https://rosmarops.com", 637, [(1144, "/blog/"), (1155, "/blog/about/"), (1190, "/observatory/"), (1145, "/"),
                                          (1146, "/es/blog/"), (1221, "/ca/blog/")], "/sandbox/"),
    "es": ("https://rosmarops.com/es", 317, [(1120, "/es/blog/"), (1126, "/es/blog/que-es-rosmarops/"), (1178, "/es/observatorio/"),
                                             (1127, "/es/"), (1136, "/blog/"), (1169, "/ca/blog/")], "/es/sandbox/"),
    "ca": ("https://rosmarops.com/ca", 5, [(15, "/ca/blog/"), (16, "/ca/blog/que-es-rosmarops/"), (38, "/ca/observatori/"),
                                           (17, "/ca/"), (18, "/blog/"), (19, "/es/blog/")], "/ca/sandbox/"),
}


def items(menu, rows, parent=None):
    return [{"ID": i, "menu": menu, "url": "https://rosmarops.com" + u, "menu_order": n, "menu_item_parent": (parent or {}).get(i, 0)}
            for n, (i, u) in enumerate(rows, 1)]


class Menu8(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, menu, its, options=None, locations=None):
        self.db.write_text(json.dumps({"options": options or {}, "locations": {"primary": menu} if locations is None else locations,
                                       "menu_items": its, "posts": []}))
        env = dict(os.environ, MENU8_DB=str(self.db), MENU8_CONTENT=str(Path(self.tmp.name) / "content"))
        out = subprocess.run(["php", str(TESTS / "menu8-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def order(self, db):
        return [i["url"].replace("https://rosmarops.com", "") for i in sorted(db["menu_items"], key=lambda i: (i["menu_order"], i["ID"]))]

    def test_after_observatory_on_each_site(self):
        for lang, (home, menu, rows, sec) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, menu, items(menu, rows))
                want = [u for _, u in rows]
                want.insert(3, sec)
                self.assertEqual(self.order(db), want)
                self.assertEqual(sorted(i["menu_order"] for i in db["menu_items"]), list(range(1, 8)))
                new = next(i for i in db["menu_items"] if i["url"].endswith(sec))
                self.assertEqual((new["title"], new["type"], new["menu_item_parent"]), ("Sandbox", "custom", 0))
                self.assertTrue(log[1].startswith("menu done:"), log)
                self.assertIn(f"right after item {rows[2][0]}", log[1])
                self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / f"menu8-{lang}.log").exists())

    def test_stored_menu_order_with_gaps_or_repeats(self):
        """GTM-175: the ES menu 317 had stored menu_order values that were not 1..6 (WordPress shows them as 1..6). menu8
        shifted from the shown numbers and left Blog, Sandbox, … , Acerca de, Observatorio. Now every item is renumbered."""
        home, menu, rows, sec = SITES["es"]
        for stored in ([1, 8, 9, 10, 11, 12], [1, 2, 2, 3, 3, 3], [0, 0, 0, 0, 0, 0]):
            with self.subTest(stored=stored):
                its = items(menu, rows)
                for it, o in zip(its, stored):
                    it["menu_order"] = o
                want_before = [t[2] for t in sorted(zip(stored, [r[0] for r in rows], [r[1] for r in rows]))]
                log, db = self.run_with(home, menu, its)
                want = list(want_before)
                want.insert(want.index("/es/observatorio/") + 1, sec)
                self.assertEqual(self.order(db), want)
                self.assertEqual(sorted(i["menu_order"] for i in db["menu_items"]), list(range(1, 8)))

    def test_runs_once(self):
        home, menu, rows, _ = SITES["es"]
        log, db = self.run_with(home, menu, items(menu, rows), options={"rosmarops_menu8_done": "x"})
        self.assertEqual(len(db["menu_items"]), 6)

    def test_skips_when_the_item_is_already_there(self):
        home, menu, rows, sec = SITES["ca"]
        log, db = self.run_with(home, menu, items(menu, rows + [(99, sec)]))
        self.assertEqual(len(db["menu_items"]), 7)
        self.assertTrue(log[1].startswith("menu skipped: item 99"), log)

    def test_skips_without_exactly_one_top_level_observatory(self):
        home, menu, rows, _ = SITES["en"]
        log, db = self.run_with(home, menu, items(menu, [r for r in rows if r[0] != 1190]))
        self.assertTrue(log[1].startswith("menu skipped:") and "has 0 top-level" in log[1], log)
        log, db = self.run_with(home, menu, items(menu, rows + [(2000, "/observatory/")]))
        self.assertIn("has 2 top-level", log[1])
        log, db = self.run_with(home, menu, items(menu, rows, parent={1190: 1144}))
        self.assertIn("has 0 top-level", log[1])
        self.assertEqual([i["menu_order"] for i in db["menu_items"]], [1, 2, 3, 4, 5, 6])

    def test_no_menu_and_other_sites(self):
        home, menu, rows, _ = SITES["en"]
        log, db = self.run_with(home, menu, items(menu, rows), locations={})
        self.assertTrue(log[1].startswith("menu skipped: no menu"), log)
        log, db = self.run_with("https://example.com", menu, items(menu, rows))
        self.assertEqual(log, [])
        self.assertFalse(db["options"])


if __name__ == "__main__":
    unittest.main()
