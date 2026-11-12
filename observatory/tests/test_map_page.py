"""GTM-138: the Observatory map page (observatory/map_page.py): phrases, rules, and that it stays hidden.

Run from the repository root:  python3 -m unittest observatory/tests/test_map_page.py
"""

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import map_page as mp  # noqa: E402

PAGES = {l: ROOT / "site" / p.strip("/") / "index.html" for l, p in mp.MAP_PATH.items()}


class Phrases(unittest.TestCase):
    def test_every_inputs_code_of_the_release_has_a_phrase(self):
        # A new code without a row in the table makes this fail, so the advisor writes its phrase (GTM-138).
        ep, _, cat = mp.load()
        self.assertEqual(mp.missing_phrases(ep, cat["phrases"]), [])

    def test_a_code_without_phrase_is_reported_and_shown_without_one(self):
        ep, _, cat = mp.load()
        ep = copy.deepcopy(ep)
        a = ep["agents"][0]
        a["axes"]["autonomy"]["inputs"] = ["brand_new_code"] + a["axes"]["autonomy"]["inputs"]
        self.assertEqual(mp.missing_phrases(ep, cat["phrases"]), ["brand_new_code"])
        self.assertIsNone(mp.top_phrase(a, ep["weights"], "es", cat["phrases"]))


class Rules(unittest.TestCase):
    W = {"autonomy": 2, "reach": 2, "contagion": 2, "delegation": 1, "opacity": 1, "complexity": 1}
    P = {"x": {"es": "x"}, "y": {"es": "y"}, "z": {"es": "z"}}

    def agent(self, **levels):
        return {"product": "p", "evaluated": True,
                "axes": {k: ({"level": None, "no_data": "x"} if v is None else {"level": v[0], "inputs": v[1]}) for k, v in levels.items()}}

    def test_top_phrase_weight_times_level_then_tie_order(self):
        a = self.agent(autonomy=(1, ["x"]), delegation=(3, ["y"]), complexity=None)
        self.assertEqual(mp.top_phrase(a, self.W, "es", self.P), "y")  # 3x1 beats 1x2
        a = self.agent(reach=(2, ["x"]), autonomy=(2, ["y"]))
        self.assertEqual(mp.top_phrase(a, self.W, "es", self.P), "y")  # tie: autonomy before reach
        a = self.agent(autonomy=(0, []), reach=(0, []))
        self.assertIsNone(mp.top_phrase(a, self.W, "es", self.P))

    def test_who_decides(self):
        a = {"axes": {"autonomy": {"level": 3, "inputs": ["reads_files:machine", "writes_files"]},
                      "contagion": {"level": 3, "inputs": ["C3:instructions"]},
                      "delegation": {"level": 3, "inputs": ["writes_files:model"]}}}
        got = {act[0]: mp.decider(a, act) for act in mp.ACTIONS}
        self.assertEqual(got, {"reads_files": "nobody", "writes_files": "model", "runs_commands": "you",
                               "sends_out": "you", "changes_other_agents": "nobody"})


class HiddenPage(unittest.TestCase):
    def test_noindex_and_cta(self):
        for lang, f in PAGES.items():
            html = f.read_text(encoding="utf-8")
            self.assertIn('<meta name="robots" content="noindex">', html, lang)
            self.assertIn(f'{mp.DOWNLOAD[lang]}?from=observatory-map"', html, lang)
            self.assertEqual(html.count('class="m-row"'), 9, lang)

    def test_not_in_sitemap_llms_or_any_link(self):
        sitemap = (ROOT / "site" / "sitemap-pages.xml").read_text(encoding="utf-8")
        llms = (ROOT / "site" / "llms.txt").read_text(encoding="utf-8")
        for p in mp.MAP_PATH.values():
            self.assertNotIn(p, sitemap)
            self.assertNotIn(p, llms)
        rx = re.compile(r'href="(?:https://rosmarops\.com)?(' + "|".join(re.escape(p) for p in mp.MAP_PATH.values()) + r')"')
        own = set(PAGES.values())
        for f in list((ROOT / "site").rglob("*.html")) + list((ROOT / "wp").rglob("*.html")) + list((ROOT / "wp").rglob("*.php")):
            if f in own:
                continue
            self.assertIsNone(rx.search(f.read_text(encoding="utf-8", errors="ignore")), f)

    def test_what_waits_for_the_engine_is_not_shown(self):
        cat = json.loads(mp.MAP_TEXTS.read_text(encoding="utf-8"))
        for lang, f in PAGES.items():
            html = f.read_text(encoding="utf-8")
            T = cat["texts"][lang]
            for k in ("b5.shares", "b5.fix", "b5.fix.after.label", "b5.fix.none", "b5.shares.none"):
                self.assertNotIn(T[k], html, (lang, k))
            self.assertNotIn(T["b5.sources"].split("{")[0].strip(), html, lang)


if __name__ == "__main__":
    unittest.main()
