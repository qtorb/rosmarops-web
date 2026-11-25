"""GTM-206: lesson 2 of the course, «The chain» (observatory/course_pages.py).

Run from the repository root:  python3 -m unittest observatory/tests/test_course_pages.py
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import course_pages  # noqa: E402

SITE = ROOT / "site"
DATA = course_pages.load()
PATHS = DATA["path"]
JS = (SITE / "assets" / "course" / "chain.js").read_text(encoding="utf-8")
CSS = (SITE / "assets" / "course" / "chain.css").read_text(encoding="utf-8")

# The six state messages, literal from the signed texts (ES §4.4 of the pilot lesson; EN and CA §4.4).
MESSAGES = {
    "es": {
        "allow0": "**La cadena está entera.** Claude Code puede leer el .env sin preguntarte, y la clave abre tu cuenta de Stripe.",
        "allow1": "**La cadena está entera.** Claude Code puede leer el .env sin preguntarte. Y como además puede lanzar comandos, tiene un segundo camino para llegar.",
        "ask0": "**La cadena se corta en el segundo eslabón.** Antes de leer el .env, Claude Code te tiene que preguntar. La puerta la tienes tú.",
        "ask1": "**La cadena sigue, en parte.** Claude Code te preguntaría antes de abrir el .env, pero puede lanzar un programa sin preguntarte, y ese programa sí puede leerlo.",
        "deny0": "**La cadena se corta en el segundo eslabón.** Claude Code no puede leer el .env. No hay camino hasta la clave ni hasta tu cuenta de Stripe.",
        "deny1": "**La cadena sigue, en parte.** La regla impide que Claude Code abra el .env él mismo, pero un programa que lance sin preguntarte sí puede leerlo. Para cortarla del todo, quítale también eso.",
    },
    "en": {
        "allow0": "**The chain is whole.** Claude Code can read the .env without asking you, and the key opens your Stripe account.",
        "allow1": "**The chain is whole.** Claude Code can read the .env without asking you. And since it can also run commands, it has a second way to get there.",
        "ask0": "**The chain breaks at the second link.** Before reading the .env, Claude Code has to ask you. You hold the door.",
        "ask1": "**The chain still holds, partly.** Claude Code would ask you before opening the .env, but it can launch a program without asking you, and that program can read it.",
        "deny0": "**The chain breaks at the second link.** Claude Code can't read the .env. There's no path to the key or to your Stripe account.",
        "deny1": "**The chain still holds, partly.** The rule stops Claude Code from opening the .env itself, but a program it launches without asking you can read it. To break it completely, take that away too.",
    },
    "ca": {
        "allow0": "**La cadena està sencera.** Claude Code pot llegir el .env sense preguntar-te, i la clau obre el teu compte de Stripe.",
        "allow1": "**La cadena està sencera.** Claude Code pot llegir el .env sense preguntar-te. I com que a més pot llançar ordres, té un segon camí per arribar-hi.",
        "ask0": "**La cadena es trenca a la segona baula.** Abans de llegir el .env, Claude Code t'ho ha de preguntar. La porta la tens tu.",
        "ask1": "**La cadena continua, en part.** Claude Code et preguntaria abans d'obrir el .env, però pot llançar un programa sense preguntar-te, i aquest programa sí que el pot llegir.",
        "deny0": "**La cadena es trenca a la segona baula.** Claude Code no pot llegir el .env. No hi ha camí fins a la clau ni fins al teu compte de Stripe.",
        "deny1": "**La cadena continua, en part.** La regla impedeix que Claude Code obri el .env ell mateix, però un programa que llanci sense preguntar-te sí que el pot llegir. Per trencar-la del tot, treu-li també això.",
    },
}


def page(lang):
    return (SITE / PATHS[lang].strip("/") / "index.html").read_text(encoding="utf-8")


class Texts(unittest.TestCase):
    def test_the_six_messages_are_literal_in_three_languages(self):
        for lang, msgs in MESSAGES.items():
            self.assertEqual(DATA[lang]["piece"]["msg"], msgs, lang)

    def test_the_page_carries_its_messages_for_the_script(self):
        for lang, msgs in MESSAGES.items():
            s = page(lang)
            for m in msgs.values():
                self.assertIn(m, s, lang)

    def test_the_first_state_is_rendered_without_the_script(self):
        for lang in MESSAGES:
            first = course_pages.fmt(MESSAGES[lang]["allow0"])
            self.assertIn(f'id="cs-msg" role="status" aria-live="polite">{first}</div>', page(lang), lang)

    def test_footer_is_literal_from_block_178(self):
        """GTM-215 B.5 (vigil docs/briefs/GTM-215.md): the footer names no list; the repository goes as text."""
        want = {
            "es": "Cada dato de esta lección sale del código de RosmarOps, que es público (github.com/qtorb/rosmarops), del Observatorio y de la documentación oficial de Claude Code.",
            "en": "Every fact in this lesson comes from RosmarOps's code, which is public (github.com/qtorb/rosmarops), from the Observatory and from Claude Code's official documentation.",
            "ca": "Cada dada d'aquesta lliçó surt del codi de RosmarOps, que és públic (github.com/qtorb/rosmarops), de l'Observatori i de la documentació oficial de Claude Code.",
        }
        for lang, text in want.items():
            self.assertEqual(DATA[lang]["close"]["footer"], text, lang)
            self.assertIn(course_pages.esc(text), page(lang), lang)

    def test_no_forbidden_words(self):
        course_pages.check(DATA)


class Pages(unittest.TestCase):
    def test_pages_are_up_to_date(self):
        for path, text in course_pages.pages(DATA).items():
            f = SITE / path.strip("/") / "index.html"
            self.assertEqual(f.read_text(encoding="utf-8"), text, path)

    def test_noindex_and_hreflang(self):
        for lang in MESSAGES:
            s = page(lang)
            self.assertIn('<meta name="robots" content="noindex">', s)
            for l2, p in PATHS.items():
                self.assertIn(f'<link rel="alternate" hreflang="{l2}" href="https://rosmarops.com{p}">', s)

    def test_not_in_the_sitemap_or_llms(self):
        for f in list(SITE.glob("sitemap*.xml")) + [SITE / "llms.txt"]:
            if f.exists():
                s = f.read_text(encoding="utf-8")
                for p in PATHS.values():
                    self.assertNotIn(p, s, f.name)

    def test_no_page_links_to_the_lesson(self):
        own = {(SITE / p.strip("/") / "index.html").resolve() for p in PATHS.values()}
        for f in SITE.rglob("*.html"):
            if f.resolve() in own:
                continue
            s = f.read_text(encoding="utf-8", errors="replace")
            for p in PATHS.values():
                self.assertNotIn(f'href="{p}', s, str(f.relative_to(ROOT)))

    def test_no_external_urls(self):
        for lang in MESSAGES:
            for u in re.findall(r'(?:href|src)="(https?:[^"]+|//[^"]+)"', page(lang)):
                self.assertTrue(u.startswith("https://rosmarops.com/"), (lang, u))
        for name, s in (("chain.js", JS), ("chain.css", CSS)):
            self.assertIsNone(re.search(r"https?:", s), name)
            self.assertNotIn("@import", s)
            self.assertNotIn("url(", s)

    def test_download_link_counts_as_course(self):
        for lang in MESSAGES:
            self.assertIn(f'href="{course_pages.DOWNLOAD[lang]}"', page(lang))
        self.assertIn("'course'", (ROOT / "wp" / "mu-plugins" / "rosmarops-downloads.php").read_text(encoding="utf-8"))


class Script(unittest.TestCase):
    def test_no_writes_to_the_address_or_storage_and_nothing_sent(self):
        code = re.sub(r"//[^\n]*", "", JS)
        for word in ("location", "history", "localStorage", "sessionStorage", "indexedDB", "cookie",
                     "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "postMessage", "navigator"):
            self.assertNotIn(word, code, word)


if __name__ == "__main__":
    unittest.main()
