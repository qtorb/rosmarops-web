"""GTM-167: «Which AI coding agents have a sandbox», generated from the protections of the agent files."""
import html
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import sandbox_page  # noqa: E402

AGENTS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "observatory/data/agents").glob("*.json"))]
EVALUATED = {"claude-code", "cursor", "codex", "grok-build", "hermes-agent", "github-copilot", "gemini-cli",
             "antigravity-cli", "cline"}
FORBIDDEN = re.compile(r"\b(seguro|segura|protege|a salvo|safe|safely|protects|segur|protegeix)\b", re.I)


class Data(unittest.TestCase):
    def test_the_nine_evaluated_agents_have_protections(self):
        self.assertEqual({a["agent"]["id"] for a in AGENTS if a.get("protections")}, EVALUATED)

    def test_unknown_has_no_source_and_every_other_value_has_one(self):
        for a in AGENTS:
            for kind in ("sandbox", "network_cut") if a.get("protections") else ():
                for system, c in a["protections"][kind].items():
                    self.assertEqual("source" in c, c["value"] != "unknown", (a["agent"]["id"], kind, system))

    def test_container_only_where_signed(self):
        got = {(a["agent"]["id"], k, s) for a in AGENTS if a.get("protections") for k in ("sandbox", "network_cut")
               for s, c in a["protections"][k].items() if c["value"] == "container_only"}
        want = {("hermes-agent", k, s) for k in ("sandbox", "network_cut") for s in ("windows", "macos", "linux")}
        self.assertEqual(got, want | {("gemini-cli", "sandbox", "linux")})


class Page(unittest.TestCase):
    def test_every_cell_shows_its_value_with_its_source(self):
        for lang in ("en", "es", "ca"):
            T, body = sandbox_page.body(lang, AGENTS, lambda aid: None)
            for a in sandbox_page.rows(AGENTS):
                for kind in ("sandbox", "network_cut"):
                    for system, c in a["protections"][kind].items():
                        label = f'{T["line." + kind]}: '
                        value = html.escape(T["value." + c["value"]], quote=True)
                        if "source" in c:
                            self.assertIn(f'{label}<a href="{html.escape(c["source"]["url"], quote=True)}" rel="noopener">{value}</a>', body)
                        else:
                            self.assertIn(f'{label}{value}</span>', body)
            self.assertEqual(body.count("<tr>"), len(EVALUATED) + 1)
            self.assertIn(sandbox_page.GLOSSARY_SANDBOX[lang], body)
            self.assertFalse(FORBIDDEN.search(html.unescape(re.sub(r"<[^>]+>", " ", body))), lang)

    def test_generated_pages_link_published_agents_and_the_glossary_links_back(self):
        for lang, gloss in (("en", "site/glossary/index.html"), ("es", "site/es/glosario/index.html"),
                            ("ca", "site/ca/glossari/index.html")):
            page = (ROOT / "site" / sandbox_page.SANDBOX_PATH[lang].strip("/") / "index.html").read_text(encoding="utf-8")
            self.assertNotIn('name="robots"', page)
            self.assertIn(f'href="{sandbox_page.SANDBOX_PATH[lang]}"', (ROOT / gloss).read_text(encoding="utf-8"))
            index = {"en": "site/observatory/index.html", "es": "site/es/observatorio/index.html",
                     "ca": "site/ca/observatori/index.html"}[lang]
            self.assertIn(f'href="{sandbox_page.SANDBOX_PATH[lang]}"', (ROOT / index).read_text(encoding="utf-8"))
        self.assertEqual((ROOT / "site/sitemap-pages.xml").read_text(encoding="utf-8").count("<loc>https://rosmarops.com/" + "observatory/ai-agents-with-sandbox/</loc>"), 1)


if __name__ == "__main__":
    unittest.main()
