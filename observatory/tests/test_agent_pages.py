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
