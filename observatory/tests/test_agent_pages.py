"""Agent pages: who_decides "unknown" (GTM-159, texts signed by Albert 2026-11-13)."""
import html
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import build  # noqa: E402

# Literal texts signed by Albert (advisor brief 2026-11-13 22:55).
MODE_LINE = {
    "en": "When an action needs permission, who gives it: not documented.",
    "es": "Cuando una acción necesita permiso, quién lo da: no está documentado.",
    "ca": "Quan una acció necessita permís, qui el dona: no està documentat.",
}
SUMMARY_END = {
    "en": ": the documentation does not say who gives permission.",
    "es": ": la documentación no dice quién da el permiso.",
    "ca": ": la documentació no diu qui dona el permís.",
}
PAGES = {
    "en": ROOT / "site/observatory/grok-bot/index.html",
    "es": ROOT / "site/es/observatorio/grok-bot/index.html",
    "ca": ROOT / "site/ca/observatori/grok-bot/index.html",
}


class WhoDecidesUnknown(unittest.TestCase):
    def test_schema_accepts_unknown(self):
        schema = json.loads((ROOT / "observatory/schema/observatory.v1.schema.json").read_text(encoding="utf-8"))
        def find(node):
            if isinstance(node, dict):
                if "who_decides" in node.get("properties", {}):
                    return node["properties"]["who_decides"]["enum"]
                for v in node.values():
                    r = find(v)
                    if r:
                        return r
            if isinstance(node, list):
                for v in node:
                    r = find(v)
                    if r:
                        return r
            return None
        self.assertIn("unknown", find(schema))

    def test_catalog_texts(self):
        for lang in PAGES:
            cat = json.loads((ROOT / f"observatory/i18n/{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(cat["agent.mode_who"].replace("{who}", cat["who.unknown"]), MODE_LINE[lang], lang)
            self.assertTrue(SUMMARY_END[lang].endswith(cat["summary.who.unknown"] + "."), lang)

    def test_grok_bot_page_renders_unknown(self):
        data = json.loads((ROOT / "observatory/data/agents/grok-bot.json").read_text(encoding="utf-8"))
        self.assertEqual(data["default_mode"]["who_decides"], "unknown")
        for lang, f in PAGES.items():
            page = html.unescape(f.read_text(encoding="utf-8"))
            self.assertIn(MODE_LINE[lang], page, lang)
            self.assertIn(SUMMARY_END[lang], page, lang)

    def test_grok_bot_published(self):
        self.assertIn("grok-bot", build.PUBLISHED_AGENT_PAGES)
        for lang, f in PAGES.items():
            self.assertNotIn('name="robots"', f.read_text(encoding="utf-8"), lang)


if __name__ == "__main__":
    unittest.main()


class Families(unittest.TestCase):
    """GTM-191 (signed by Albert 20-11 07:08): the five families in order, and every new file with its source."""

    AGENTS = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "observatory/data/agents").glob("*.json")}
    NEW = ("orca", "paseo", "claude-squad", "paradev")
    NEW_FRAMEWORKS = ("openai-agents-sdk",)

    def test_order(self):
        self.assertEqual(build.FAMILIES, ("local", "orchestrators", "tooling", "automation", "builders", "cloud"))
        self.assertEqual(list(build.FAMILY_H2), list(build.FAMILIES))

    def test_family_of_each_kind(self):
        f = lambda kinds, fp="yes", i="x": build.family({"agent": {"id": i, "kinds": kinds, "local_footprint": fp}})
        self.assertEqual(f(["orchestrator", "agent_tooling"]), "orchestrators")
        self.assertEqual(f(["framework"]), "tooling")
        self.assertEqual(f(["agent_tooling"]), "tooling")
        self.assertEqual(f(["workflow_automation"], "no"), "automation")
        self.assertEqual(f(["agent_builder"], "no"), "builders")  # GTM-208
        self.assertEqual(f(["cloud"], "no"), "cloud")
        self.assertEqual(f(["cli"]), "local")
        self.assertEqual(build.family(self.AGENTS["paperclip"]), "orchestrators")
        self.assertEqual(build.family(self.AGENTS["n8n"]), "automation")

    def test_application_category_comes_from_the_family(self):
        """GTM-210: BusinessApplication only for the builders family; the rest DeveloperApplication."""
        for i, a in self.AGENTS.items():
            want = "BusinessApplication" if build.family(a) == "builders" else "DeveloperApplication"
            self.assertEqual(build.software_app(a)["applicationCategory"], want, i)
        for i in ("lindy", "relevance-ai", "copilot-studio"):
            self.assertEqual(build.software_app(self.AGENTS[i])["applicationCategory"], "BusinessApplication", i)
        for i in ("n8n", "make", "multica", "claude-code"):
            self.assertEqual(build.software_app(self.AGENTS[i])["applicationCategory"], "DeveloperApplication", i)
        page = (ROOT / "site/observatory/index.html").read_text(encoding="utf-8")
        self.assertIn('"name":"Lindy","applicationCategory":"BusinessApplication"', page)
        self.assertIn('"name":"Make","applicationCategory":"DeveloperApplication"', page)

    def test_index_lists_follow_the_order(self):
        names = {"en": json.loads((ROOT / "observatory/i18n/en.json").read_text(encoding="utf-8"))}["en"]
        page = (ROOT / "site/observatory/index.html").read_text(encoding="utf-8")
        lists = [names[build.FAMILY_H2[f]] for f in build.FAMILIES
                 if f == "local" or any(build.family(a) == f for a in self.AGENTS.values())]
        found = [n for n in lists if f'"@type":"ItemList","name":"{n}"' in page]
        self.assertEqual(found, lists)
        self.assertEqual(sorted(found, key=lambda n: page.index(f'"@type":"ItemList","name":"{n}"')), lists)

    def test_new_files_have_a_source(self):
        sources = json.loads((ROOT / "observatory/sources.json").read_text(encoding="utf-8"))["sources"]
        scopes = {s["scope"] for s in sources}
        for i in self.NEW:
            a = self.AGENTS[i]
            self.assertIn(i, scopes, i)
            self.assertIn("orchestrator", a["agent"]["kinds"], i)
            self.assertEqual(a["agent"]["rosmarops"]["status"], "not_supported", i)
            for s in a.get("surfaces", []) + a["agent"].get("sources", []):
                self.assertTrue(s["source"]["official"], i)
                self.assertIn(s["verified"]["how"], ("official_doc", "official_code"), i)

    def test_h1_key(self):
        self.assertEqual(build.h1_key(self.AGENTS["paperclip"]["agent"]), "agent.h1_orchestrator")
        self.assertEqual(build.h1_key(self.AGENTS["kanvas"]["agent"]), "agent.h1_tool")
        self.assertEqual(build.h1_key(self.AGENTS["claude-code"]["agent"]), "agent.h1")

    def test_new_framework_has_a_source(self):
        scopes = {s["scope"] for s in json.loads((ROOT / "observatory/sources.json").read_text(encoding="utf-8"))["sources"]}
        for i in self.NEW_FRAMEWORKS:
            a = self.AGENTS[i]
            self.assertIn(i, scopes, i)
            self.assertEqual(build.family(a), "tooling", i)
            for s in a.get("surfaces", []) + a["agent"].get("sources", []) + a["agent"].get("notes", []):
                self.assertTrue(s["source"]["official"], i)

    def test_orchestrator_title_is_its_h1(self):
        """GTM-191 (advisor, 20-11): an orchestrator's page uses agent.h1_orchestrator as its title too."""
        import tempfile
        fixture = json.loads(next((ROOT / "observatory/tests/fixture").glob("*.json")).read_text(encoding="utf-8"))
        fixture["agent"]["kinds"] = ["orchestrator"]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / (fixture["agent"]["id"] + ".json")).write_text(json.dumps(fixture), encoding="utf-8")
            out = Path(d) / "out"
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "observatory/build.py"), "--data", d, "--out", str(out)], check=True,
                           capture_output=True)
            en = json.loads((ROOT / "observatory/i18n/en.json").read_text(encoding="utf-8"))["agent.h1_orchestrator"]
            want = html.escape(en.replace("{agent}", fixture["agent"]["name"]), quote=False)
            page = (out / "observatory" / fixture["agent"]["id"] / "index.html").read_text(encoding="utf-8")
            self.assertIn(f"<title>{want}</title>", page)
            self.assertIn(f"<h1>{want}</h1>", page)
