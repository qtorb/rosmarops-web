"""Tests for wp/mu-plugins/rosmarops-menu10-academy.php: «Academy» in the blog menu, right after Sandbox, only once
RosmarOps Academy is open (GTM-230).

Run from the repository root:  python3 -m unittest wp/tests/test_menu10_academy.py   (needs php on PATH)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]
sys.path.insert(0, str(ROOT / "observatory"))
import academy  # noqa: E402

# The blog menus of 27-11: the ones of 16-11 (test_menu8_sandbox.py) with Sandbox after the Observatory. The Sandbox
# item ids are the ones menu8 gave (ES 1243, as menu9 logged); EN and CA are made up here.
SITES = {
    "en": ("https://rosmarops.com", 637, [(1144, "/blog/"), (1155, "/blog/about/"), (1190, "/observatory/"), (1240, "/sandbox/"),
                                          (1145, "/"), (1146, "/es/blog/"), (1221, "/ca/blog/")], "/academy/"),
    "es": ("https://rosmarops.com/es", 317, [(1120, "/es/blog/"), (1126, "/es/blog/que-es-rosmarops/"), (1178, "/es/observatorio/"),
                                             (1243, "/es/sandbox/"), (1127, "/es/"), (1136, "/blog/"), (1169, "/ca/blog/")], "/es/academy/"),
    "ca": ("https://rosmarops.com/ca", 5, [(15, "/ca/blog/"), (16, "/ca/blog/que-es-rosmarops/"), (38, "/ca/observatori/"),
                                           (40, "/ca/sandbox/"), (17, "/ca/"), (18, "/blog/"), (19, "/es/blog/")], "/ca/academy/"),
}
PLUGIN = ROOT / "wp" / "mu-plugins" / "rosmarops-menu10-academy.php"


def items(menu, rows, parent=None):
    return [{"ID": i, "menu": menu, "url": "https://rosmarops.com" + u, "menu_order": n, "menu_item_parent": (parent or {}).get(i, 0)}
            for n, (i, u) in enumerate(rows, 1)]


class Menu10(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "db.json"
        os.mkdir(Path(self.tmp.name) / "content")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, home, menu, its, options=None, locations=None, open_=True):
        self.db.write_text(json.dumps({"options": options or {}, "locations": {"primary": menu} if locations is None else locations,
                                       "menu_items": its, "posts": []}))
        env = dict(os.environ, MENU10_DB=str(self.db), MENU10_CONTENT=str(Path(self.tmp.name) / "content"))
        if open_:
            env["MENU10_OPEN"] = "1"
        out = subprocess.run(["php", str(TESTS / "menu10-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(out.stdout), json.loads(self.db.read_text())

    def order(self, db):
        return [i["url"].replace("https://rosmarops.com", "") for i in sorted(db["menu_items"], key=lambda i: (i["menu_order"], i["ID"]))]

    def test_nothing_while_academy_is_closed(self):
        for lang, (home, menu, rows, _) in SITES.items():
            log, db = self.run_with(home, menu, items(menu, rows), open_=False)
            self.assertEqual(log, [])
            self.assertEqual(len(db["menu_items"]), 7)
            self.assertFalse(db["options"])

    def test_the_switch_line_follows_the_data(self):
        """The plugin's ROSMAROPS_MENU10_OPEN is written by observatory/academy.py from observatory/data/academy.json."""
        want = "true" if academy.is_open() else "false"
        self.assertEqual(re.findall(r"const ROSMAROPS_MENU10_OPEN = (\w+);", PLUGIN.read_text(encoding="utf-8")), [want])

    def test_after_sandbox_on_each_site(self):
        for lang, (home, menu, rows, sec) in SITES.items():
            with self.subTest(lang=lang):
                log, db = self.run_with(home, menu, items(menu, rows))
                want = [u for _, u in rows]
                want.insert(4, sec)
                self.assertEqual(self.order(db), want)
                self.assertEqual(sorted(i["menu_order"] for i in db["menu_items"]), list(range(1, 9)))
                new = next(i for i in db["menu_items"] if i["url"].endswith(sec))
                self.assertEqual((new["title"], new["type"], new["menu_item_parent"]), ("Academy", "custom", 0))
                self.assertTrue(log[1].startswith("menu done:"), log)
                self.assertIn(f"right after item {rows[3][0]}", log[1])
                self.assertTrue((Path(self.tmp.name) / "content" / "rosmarops-private" / f"menu10-{lang}.log").exists())

    def test_runs_once(self):
        home, menu, rows, _ = SITES["es"]
        log, db = self.run_with(home, menu, items(menu, rows), options={"rosmarops_menu10_done": "x"})
        self.assertEqual(len(db["menu_items"]), 7)

    def test_only_on_the_menu_of_today(self):
        home, menu, rows, sec = SITES["ca"]
        log, db = self.run_with(home, menu, items(menu, rows + [(99, sec)]))
        self.assertTrue(log[1].startswith("menu skipped: item 99"), log)
        for changed in (rows[:-1], rows + [(98, "/ca/x/")], [rows[0], rows[1], rows[3], rows[2]] + rows[4:]):
            with self.subTest(changed=changed):
                log, db = self.run_with(home, menu, items(menu, changed))
                self.assertTrue(log[1].startswith("menu skipped:") and "not the menu of 27-11" in log[1], log)
                self.assertEqual(len(db["menu_items"]), len(changed))

    def test_no_menu_and_other_sites(self):
        home, menu, rows, _ = SITES["en"]
        log, db = self.run_with(home, menu, items(menu, rows), locations={})
        self.assertTrue(log[1].startswith("menu skipped: no menu"), log)
        log, db = self.run_with("https://example.com", menu, items(menu, rows))
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
