"""GTM-206: the card that asks for a star on GitHub after a click on «Download» (observatory/star_card.py).

Run from the repository root:  python3 -m unittest observatory/tests/test_star_card.py
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import star_card  # noqa: E402

SITE = ROOT / "site"
JS = (SITE / "assets" / "star" / "star.js").read_text(encoding="utf-8")
CSS = (SITE / "assets" / "star" / "star.css").read_text(encoding="utf-8")
REPO = "https://github.com/qtorb/rosmarops"

# Literal from vigil docs/research/2026-11-24-estrella-en-github.md §3.
TEXTS = {
    "es": ("Gracias por probarlo. Si te resulta útil, una estrella en GitHub ayuda a que otros lo encuentren.",
           "Poner una estrella en GitHub"),
    "en": ("Thanks for trying it. If you find it useful, a star on GitHub helps others find it.", "Star on GitHub"),
    "ca": ("Gràcies per provar-lo. Si et resulta útil, una estrella a GitHub ajuda que altres el trobin.",
           "Posa una estrella a GitHub"),
}
DOWNLOAD = re.compile(r'href="/(?:download|es/descargar|ca/descarregar)/?\?')


def marked_pages():
    return [f for f in SITE.rglob("*.html") if "data-star-block" in f.read_text(encoding="utf-8")]


class Texts(unittest.TestCase):
    def test_the_three_texts_are_literal(self):
        self.assertEqual(star_card.TEXT, TEXTS)

    def test_each_card_carries_its_language(self):
        for lang, (text, button) in TEXTS.items():
            c = star_card.card(lang)
            self.assertIn(f"<p>{text}</p>", c)
            self.assertIn(f"{button}</a>", c)


class Card(unittest.TestCase):
    def test_hidden_on_load_and_announced(self):
        for lang in TEXTS:
            self.assertTrue(star_card.card(lang).startswith('<div class="star-card" id="star-card" role="status" hidden>'))

    def test_no_count_no_outside_badge_or_icon(self):
        for lang in TEXTS:
            c = star_card.card(lang)
            self.assertEqual(re.findall(r'(?:href|src)="([^"]+)"', c), [REPO])
            self.assertNotIn("<img", c)
            self.assertIsNone(re.search(r"\d+[.,]?\d*\s*(?:k|mil|stars|estrellas|estrelles)", c, re.I))
            self.assertIn('target="_blank" rel="noopener"', c)

    def test_every_marked_page_has_one_hidden_card_its_style_and_script(self):
        pages = marked_pages()
        self.assertGreater(len(pages), 20)
        for f in pages:
            s = f.read_text(encoding="utf-8")
            name = str(f.relative_to(ROOT))
            self.assertEqual(s.count('id="star-card"'), 1, name)
            self.assertIn('role="status" hidden>', s, name)
            self.assertEqual(s.count(star_card.SCRIPT), 1, name)
            self.assertEqual(s.count(star_card.CSS_LINK), 1, name)
            lang = star_card.lang_of(s)
            self.assertIn(star_card.card(lang), s, name)

    def test_the_pages_with_download_buttons_take_part(self):
        for rel in list(star_card.HAND) + ["sandbox/index.html", "es/sandbox/index.html", "ca/sandbox/index.html",
                                           "observatory/ai-agent-map/index.html", "es/observatorio/mapa-agentes-ia/index.html",
                                           "ca/observatori/mapa-agents-ia/index.html", "observatory/claude-code/index.html",
                                           "es/observatorio/claude-code/index.html", "ca/observatori/claude-code/index.html"]:
            s = (SITE / rel).read_text(encoding="utf-8")
            self.assertTrue(DOWNLOAD.search(s), rel)
            self.assertIn('id="star-card"', s, rel)

    def test_hand_written_pages_are_up_to_date(self):
        for rel, text in star_card.hand_pages().items():
            self.assertEqual((SITE / rel).read_text(encoding="utf-8"), text, rel)

    def test_apply_is_idempotent(self):
        s = '<html lang="en"><head></head><body><div class="x" data-star-block><a href="/download?from=home">D</a></div></body></html>'
        once = star_card.apply(s)
        self.assertEqual(star_card.apply(once), once)
        self.assertIn('</div><div class="star-card"', once)

    def test_inside_goes_inside_the_block(self):
        s = '<html lang="es"><head></head><body><div class="m" data-star-block="inside"><a href="/es/descargar?from=x">D</a><small>s</small></div></body></html>'
        out = star_card.apply(s)
        self.assertIn('<small>s</small><div class="star-card"', out)


class Script(unittest.TestCase):
    def test_nothing_stored_or_sent(self):
        code = re.sub(r"//[^\n]*", "", JS)
        for word in ("localStorage", "sessionStorage", "indexedDB", "cookie", "fetch(", "XMLHttpRequest", "sendBeacon",
                     "WebSocket", "history", "location", "gtag", "dataLayer"):
            self.assertNotIn(word, code, word)

    def test_no_outside_url_in_script_or_style(self):
        for s in (JS, CSS):
            self.assertIsNone(re.search(r"https?:", s))
            self.assertNotIn("url(", s)

    def test_shows_once_and_without_animation(self):
        self.assertIn("if (shown) return;", JS)
        self.assertNotIn("transition", CSS)
        self.assertNotIn("animation", CSS)


if __name__ == "__main__":
    unittest.main()
