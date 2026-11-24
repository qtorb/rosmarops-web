"""GTM-169: the Observatory by company, the protections strip, the recommendation and «Try it in a test environment»."""
import html
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import company_page  # noqa: E402

AGENTS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "observatory/data/agents").glob("*.json"))]
FORBIDDEN = re.compile(r"\b(seguro|segura|protege|a salvo|sin riesgo|safe|safely|protects|risk-free|segur|protegeix|sense risc)\b", re.I)
INDEX = {"en": "site/observatory/index.html", "es": "site/es/observatorio/index.html", "ca": "site/ca/observatori/index.html"}
METHOD = {"en": "site/methodology/index.html", "es": "site/es/metodologia/index.html", "ca": "site/ca/metodologia/index.html"}


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class Data(unittest.TestCase):
    def test_read_only_and_asks_first_have_a_source_unless_unknown(self):
        for a in AGENTS:
            p = a.get("protections")
            if not p:
                continue
            cells = [("read_only", p["read_only"])] + [("asks_first." + k, c) for k, c in p["asks_first"].items()]
            for name, c in cells:
                self.assertEqual("source" in c, c["value"] != "unknown", (a["agent"]["id"], name))

    def test_the_recommendation_is_computed_and_gives_the_signed_set(self):
        cls = company_page.classes()
        got = {a["agent"]["id"]: company_page.recommendation(a, cls.get(a["agent"]["id"])) for a in AGENTS}
        self.assertEqual({k: v for k, v in got.items() if v}, {"codex": 2, "github-copilot": 1})


class Summary(unittest.TestCase):
    T = company_page.texts()["es"]

    def cells(self, w, m, l):
        return {"windows": {"value": w}, "macos": {"value": m}, "linux": {"value": l}}

    def test_rules(self):
        s = lambda *v: company_page.summary(self.T, self.cells(*v))
        self.assertEqual(s("on_by_default", "on_by_default", "on_by_default"), "Windows, macOS y Linux · encendido de serie")
        self.assertEqual(s("none", "off_by_default", "off_by_default"), "macOS y Linux · apagado de serie")
        self.assertEqual(s("off_by_default", "off_by_default", "container_only"), "Windows, macOS y Linux · apagado de serie")
        self.assertEqual(s("unknown", "none", "off_by_default"), "Linux · apagado de serie")
        self.assertEqual(s("off_by_default", "on_by_default", "on_by_default"),
                         "Windows, macOS y Linux · encendido en macOS y Linux, apagado en Windows")
        self.assertEqual(s("container_only", "container_only", "container_only"), "Solo con contenedor")
        self.assertEqual(s("none", "unknown", "none"), "No tiene")
        self.assertEqual(s("unknown", "unknown", "unknown"), "—")


class Pages(unittest.TestCase):
    def test_ten_companies_in_order_and_the_rest_apart(self):
        page = read(INDEX["es"])
        names = re.findall(r'<article class="co"><header><h3>(.*?)</h3>', page)
        self.assertEqual([html.unescape(n) for n in names], ["Anomaly", "Anthropic", "Anysphere", "Cline", "Continue", "Google",
                         "Kilo Code", "Microsoft (GitHub)", "n8n", "Nous Research", "OpenAI", "xAI"])  # + Anomaly, Kilo Code: 0.19.0
        rest = text(page[page.index('class="co-rest"'):])
        for n in names:
            self.assertNotIn(html.unescape(n) + " (", rest)

    def test_new_and_changed_pages_link_and_avoid_the_forbidden_words(self):
        for lang in ("en", "es", "ca"):
            index = read(INDEX[lang])
            self.assertIn(f'href="{company_page.GUIDE_PATH[lang]}"', index)
            self.assertEqual(index.count('class="rec"'), 2, lang)
            self.assertFalse(FORBIDDEN.search(text(index)), lang)
            guide = read("site" + company_page.GUIDE_PATH[lang] + "index.html")
            self.assertNotIn('name="robots"', guide)
            self.assertFalse(FORBIDDEN.search(text(guide[guide.index("<article"):guide.index("</article>")])), lang)
            self.assertIn(f"<loc>https://rosmarops.com{company_page.GUIDE_PATH[lang]}</loc>", read("site/sitemap-pages.xml"))
            method = read(METHOD[lang])
            anchor = company_page.METHOD[lang].split("#")[1]
            sec = method[method.index(f'id="{anchor}"'):method.index("</article>")]
            self.assertFalse(FORBIDDEN.search(text(sec)), lang)
            for a in AGENTS:
                if not company_page.evaluated(a):
                    continue
                f = ROOT / INDEX[lang].replace("index.html", a["agent"]["id"] + "/index.html")
                if not f.exists():  # no agent page yet (Antigravity CLI)
                    continue
                agent = f.read_text(encoding="utf-8")
                sec = agent[agent.index('<section id="try"'):]
                sec = sec[:sec.index("</section>")]
                self.assertIn(f'href="{company_page.GUIDE_PATH[lang]}"', sec)
                self.assertEqual(sec.count("<li>"), 3)
                self.assertFalse(FORBIDDEN.search(text(sec)), (lang, a["agent"]["id"]))


if __name__ == "__main__":
    unittest.main()
