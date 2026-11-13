"""GTM-138: the Observatory map page (observatory/map_page.py): phrases, rules, and its publication (Albert, 12-11).

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


class PublishedPage(unittest.TestCase):
    def test_indexable_and_cta(self):
        for lang, f in PAGES.items():
            html = f.read_text(encoding="utf-8")
            self.assertNotIn('name="robots"', html, lang)
            self.assertIn(f'{mp.DOWNLOAD[lang]}?from=observatory-map"', html, lang)
            self.assertEqual(html.count('class="m-row"'), 9, lang)
            title = json.loads(mp.MAP_TEXTS.read_text(encoding="utf-8"))["texts"][lang]["title"]
            self.assertIn(f"<title>{title}</title>", html.replace("&#x27;", "'"), lang)
            self.assertIn(f'<meta property="og:title" content="{title}">', html.replace("&#x27;", "'"), lang)
            for l, p in mp.MAP_PATH.items():  # links between languages
                self.assertIn(f'<link rel="alternate" hreflang="{l}" href="https://rosmarops.com{p}">', html, (lang, l))

    def test_in_sitemap_llms_and_linked_from_home_and_observatory(self):
        sitemap = (ROOT / "site" / "sitemap-pages.xml").read_text(encoding="utf-8")
        for p in mp.MAP_PATH.values():
            self.assertIn(f"<loc>https://rosmarops.com{p}</loc>", sitemap)
        self.assertIn(mp.MAP_PATH["en"], (ROOT / "site" / "llms.txt").read_text(encoding="utf-8"))
        homes = {"en": "site/index.html", "es": "site/es/index.html", "ca": "site/ca/index.html"}
        obs = {"en": "site/observatory/index.html", "es": "site/es/observatorio/index.html", "ca": "site/ca/observatori/index.html"}
        for lang, p in mp.MAP_PATH.items():
            for f in (homes[lang], obs[lang]):
                self.assertIn(f'href="{p}"', (ROOT / f).read_text(encoding="utf-8"), (lang, f))

    def test_what_waits_for_the_engine_is_not_shown(self):
        cat = json.loads(mp.MAP_TEXTS.read_text(encoding="utf-8"))
        for lang, f in PAGES.items():
            html = f.read_text(encoding="utf-8")
            T = cat["texts"][lang]
            for k in ("b5.shares", "b5.fix", "b5.fix.after.label", "b5.fix.none", "b5.shares.none"):
                self.assertNotIn(T[k], html, (lang, k))
            self.assertNotIn(T["b5.sources"].split("{")[0].strip(), html, lang)


class StableAnchors(unittest.TestCase):
    """GTM-145 (Albert, 12-11 23:50): each row has the agent's Observatory id as a stable anchor; the Claude Code and
    Hermes Agent pages link to it; three agents have their own title, none longer than 65 characters."""

    FICHAS = {"en": "site/observatory/{}/index.html", "es": "site/es/observatorio/{}/index.html",
              "ca": "site/ca/observatori/{}/index.html"}

    def test_rows_have_the_agent_id_and_it_does_not_depend_on_the_order(self):
        ep, _, _ = mp.load()
        want = sorted(mp.AGENT_FILE.get(a["product"], a["product"]) for a in ep["agents"] if a.get("evaluated"))
        for lang, f in PAGES.items():
            ids = re.findall(r'<button class="m-row" id="([^"]+)"', f.read_text(encoding="utf-8"))
            self.assertEqual(sorted(ids), want, lang)
            self.assertNotIn("m-d", "".join(ids), lang)

    def test_the_two_pages_link_to_their_row_and_the_others_do_not(self):
        for lang, tpl in self.FICHAS.items():
            map_html = PAGES[lang].read_text(encoding="utf-8")
            for agent in ("claude-code", "hermes-agent", "kanvas", "cursor"):
                html = (ROOT / tpl.format(agent)).read_text(encoding="utf-8")
                links = re.findall(r'href="' + re.escape(mp.MAP_PATH[lang]) + r'#([^"]+)"', html)
                if agent in ("claude-code", "hermes-agent"):
                    self.assertEqual(links, [agent], (lang, agent))
                    self.assertIn(f'<button class="m-row" id="{agent}"', map_html, (lang, agent))
                else:
                    self.assertEqual(links, [], (lang, agent))

    def test_signed_titles_fit(self):
        import html as h
        for lang, tpl in self.FICHAS.items():
            for agent in ("claude-code", "hermes-agent", "kanvas"):
                page = (ROOT / tpl.format(agent)).read_text(encoding="utf-8")
                title = h.unescape(re.search(r"<title>([^<]*)</title>", page).group(1))
                self.assertLessEqual(len(title), 65, (lang, agent, title))
                self.assertNotIn("RosmarOps", title, (lang, agent))


class ShareImage(unittest.TestCase):
    def test_each_language_shares_its_own_map_image(self):
        # GTM-152: observatory/map_social.py makes them; no agent data in them, so they don't go stale.
        for lang, f in PAGES.items():
            html = f.read_text(encoding="utf-8")
            self.assertIn(f'<meta property="og:image" content="https://rosmarops.com/assets/brand/observatory/map-social-{lang}.png">', html, lang)
            self.assertIn('<meta property="og:image:alt"', html, lang)
            self.assertTrue((ROOT / "site" / "assets" / "brand" / "observatory" / f"map-social-{lang}.png").is_file(), lang)
        other = (ROOT / "site" / "observatory" / "index.html").read_text(encoding="utf-8")
        self.assertIn("observatory-social.png", other)


if __name__ == "__main__":
    unittest.main()
