"""Tests for wp/mu-plugins/rosmarops-menu9-sandbox.php: the ES blog menu back in order (GTM-175).

Run from the repository root:  python3 -m unittest wp/tests/test_menu9_sandbox.py   (needs php on PATH)
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ES = "https://rosmarops.com/es"
WANT = [1120, 1126, 1178, 1243, 1127, 1136, 1169]
# Stored menu_order consistent with what menu8 left live on 16-11 (Blog, Sandbox, producto, EN, CA, Acerca de, Observatorio).
LEFT = {1120: 1, 1243: 4, 1127: 5, 1136: 6, 1169: 7, 1126: 8, 1178: 9}


def items(orders, extra=()):
    out = [{"ID": i, "menu": 317, "url": f"https://rosmarops.com/x{i}/", "title": f"t{i}", "menu_order": o, "menu_item_parent": 0}
           for i, o in orders.items()]
    return out + list(extra)


class Menu9(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, its, home=ES, menu=317, options=None):
        self.db.write_text(json.dumps({"options": options or {}, "locations": {"primary": menu}, "menu_items": its, "posts": []}))
        env = dict(os.environ, MENU9_DB=str(self.db), MENU9_CONTENT=str(Path(self.tmp.name) / "content"))
        out = subprocess.run(["php", str(TESTS / "menu9-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def shown(self, db):
        return [i["ID"] for i in sorted(db["menu_items"], key=lambda i: (i["menu_order"], i["ID"])) if not i["menu_item_parent"]]

    def test_puts_the_seven_in_order_and_logs_the_stored_values(self):
        log, db = self.run_with(items(LEFT))
        self.assertEqual(self.shown(db), WANT)
        self.assertEqual({i["ID"]: i["menu_order"] for i in db["menu_items"]}, {i: n for n, i in enumerate(WANT, 1)})
        self.assertIn("1126=8", log[1])
        self.assertIn("1178=9", log[1])
        self.assertTrue(log[-1].startswith("menu done:"), log)
        before = {i["ID"]: (i["url"], i["title"], i["menu_item_parent"]) for i in items(LEFT)}
        self.assertEqual({i["ID"]: (i["url"], i["title"], i["menu_item_parent"]) for i in db["menu_items"]}, before)
        self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / "menu9-es.log").exists())

    def test_gaps_and_repeats(self):
        for stored in ([0] * 7, [3, 3, 3, 1, 1, 2, 2], [10, 20, 30, 40, 50, 60, 70]):
            with self.subTest(stored=stored):
                log, db = self.run_with(items(dict(zip([1120, 1243, 1127, 1136, 1169, 1126, 1178], stored))))
                self.assertEqual(self.shown(db), WANT)
                self.assertEqual(sorted(i["menu_order"] for i in db["menu_items"]), list(range(1, 8)))

    def test_skips_unless_exactly_the_seven(self):
        for its in (items({k: v for k, v in LEFT.items() if k != 1243}),
                    items(LEFT) + [{"ID": 5000, "menu": 317, "url": "u", "title": "t", "menu_order": 10, "menu_item_parent": 0}]):
            with self.subTest(n=len(its)):
                log, db = self.run_with(its)
                self.assertTrue(log[-1].startswith("menu skipped:"), log)
                self.assertEqual({i["ID"]: i["menu_order"] for i in db["menu_items"]}, {i["ID"]: i["menu_order"] for i in its})
        # a child item does not count as top level, and is not touched
        child = {"ID": 6000, "menu": 317, "url": "c", "title": "c", "menu_order": 3, "menu_item_parent": 1126}
        log, db = self.run_with(items(LEFT, [child]))
        self.assertTrue(log[-1].startswith("menu done:"), log)
        self.assertEqual(next(i for i in db["menu_items"] if i["ID"] == 6000)["menu_order"], 3)

    def test_other_menu_other_sites_and_once(self):
        log, db = self.run_with(items(LEFT), menu=637)
        self.assertTrue(log[-1].startswith("menu skipped: the primary menu is 637"), log)
        for home in ("https://rosmarops.com", "https://rosmarops.com/ca"):
            log, db = self.run_with(items(LEFT), home=home)
            self.assertEqual(log, [])
            self.assertFalse(db["options"])
        log, db = self.run_with(items(LEFT), options={"rosmarops_menu9_done": "x"})
        self.assertEqual({i["ID"]: i["menu_order"] for i in db["menu_items"]}, LEFT)


if __name__ == "__main__":
    unittest.main()
