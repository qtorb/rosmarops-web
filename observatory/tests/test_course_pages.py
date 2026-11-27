"""GTM-206, GTM-227: the course (observatory/course_pages.py): lesson 1 «The inspector», lesson 2 «The chain» and the
RosmarOps Academy page that presents them (GTM-230, tested in test_academy.py).

Run from the repository root:  python3 -m unittest observatory/tests/test_course_pages.py
"""

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import course_pages  # noqa: E402

SITE = ROOT / "site"
ALL = course_pages.load_all()
DATA = ALL["the-chain"]
ONE = ALL["the-inspector"]
import academy  # noqa: E402
ENTRY = academy.load()
PATHS = DATA["path"]
ONE_PATHS = ONE["path"]
COURSE_PATHS = list(PATHS.values()) + list(ONE_PATHS.values()) + list(ENTRY["path"].values())
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


def page(lang, paths=PATHS):
    return (SITE / paths[lang].strip("/") / "index.html").read_text(encoding="utf-8")


def check_signed():
    spec = importlib.util.spec_from_file_location("check_signed", ROOT / "tools" / "course" / "check_signed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Texts(unittest.TestCase):
    def test_the_six_messages_are_literal_in_three_languages(self):
        for lang, msgs in MESSAGES.items():
            self.assertEqual(DATA[lang]["try"]["piece"]["msg"], msgs, lang)

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
            self.assertEqual(DATA[lang]["take"]["footer"], text, lang)
            self.assertIn(course_pages.esc(text), page(lang), lang)

    def test_retouches_of_block_188_are_in_place(self):
        """GTM-217 (vigil docs/briefs/GTM-217.md): each retouch is in its text, the part it replaced is gone, and no
        text points to a lesson 3 that does not exist yet. tools/course/check_signed.py checks them against the brief."""
        mod = check_signed()
        self.assertEqual(len(mod.RETOUCHES), 18)
        for path, new, old in mod.RETOUCHES:
            s = DATA
            for k in path:
                s = s[k]
            self.assertIn(new, s, path)
            if old not in new:
                self.assertNotIn(old, s, path)
            else:
                self.assertNotEqual(s, old, path)
        for lang, word in (("en", "lesson 3"), ("es", "lección 3"), ("ca", "lliçó 3")):
            self.assertNotIn(word, json.dumps(DATA[lang], ensure_ascii=False).lower(), lang)
            self.assertNotIn(word, json.dumps(ONE[lang], ensure_ascii=False).lower(), lang)

    def test_the_two_corrected_sentences_of_gtm_219(self):
        """GTM-227 §5: in the capability card and in change 1 of the game, the new sentence is in place and the two
        old ones are gone, in the three languages, in the data and in the served page."""
        mod = check_signed()
        for lang, (new, old) in mod.CORRECTED.items():
            for path in mod.CORRECTED_AT:
                s = DATA[lang]
                for k in path:
                    s = s[k]
                self.assertIn(new, s, (lang, path))
                for o in old:
                    self.assertNotIn(o, s, (lang, path))
            served = page(lang)
            self.assertEqual(served.count(new), 2, lang)
            for o in old:
                self.assertNotIn(o, served, lang)

    def test_no_forbidden_words_and_english_quotes(self):
        for d in ALL.values():
            course_pages.check(d)


class Pages(unittest.TestCase):
    def test_pages_are_up_to_date(self):
        for path, text in course_pages.pages().items():
            f = SITE / path.strip("/") / "index.html"
            self.assertEqual(f.read_text(encoding="utf-8"), text, path)

    def test_noindex_and_hreflang(self):
        for paths in (PATHS, ONE_PATHS):
            for lang in MESSAGES:
                s = page(lang, paths)
                self.assertIn('<meta name="robots" content="noindex">', s)
                for l2, p in paths.items():
                    self.assertIn(f'<link rel="alternate" hreflang="{l2}" href="https://rosmarops.com{p}">', s)

    def test_not_in_the_sitemap_or_llms(self):
        for f in list(SITE.glob("sitemap*.xml")) + [SITE / "llms.txt"]:
            if f.exists():
                s = f.read_text(encoding="utf-8")
                for p in COURSE_PATHS:
                    self.assertNotIn(f"rosmarops.com{p}", s, f.name)

    def test_no_page_links_to_the_course(self):
        """Only the course pages link to each other (lesson 1 to lesson 2); no other page or menu links to them."""
        own = {(SITE / p.strip("/") / "index.html").resolve() for p in COURSE_PATHS}
        for f in SITE.rglob("*.html"):
            if f.resolve() in own:
                continue
            s = f.read_text(encoding="utf-8", errors="replace")
            for p in COURSE_PATHS:
                self.assertNotIn(f'href="{p}"', s, str(f.relative_to(ROOT)))

    def test_no_external_urls(self):
        for lang in MESSAGES:
            for u in re.findall(r'(?:href|src)="(https?:[^"]+|//[^"]+)"', page(lang) + page(lang, ONE_PATHS)):
                # The one outside address: the repository, in the GitHub star card (GTM-206 PR 3).
                self.assertTrue(u.startswith("https://rosmarops.com/") or u == "https://github.com/qtorb/rosmarops", (lang, u))
        for name, s in (("chain.js", JS), ("chain.css", CSS)):
            self.assertIsNone(re.search(r"https?:", s), name)
            self.assertNotIn("@import", s)
            self.assertNotIn("url(", s)

    def test_download_link_counts_as_course(self):
        for lang in MESSAGES:
            self.assertIn(f'href="{course_pages.DOWNLOAD[lang]}"', page(lang))
            self.assertIn(f'href="{course_pages.DOWNLOAD[lang]}"', page(lang, ONE_PATHS))
        self.assertIn("'course'", (ROOT / "wp" / "mu-plugins" / "rosmarops-downloads.php").read_text(encoding="utf-8"))


SAMPLE = {"en": "/sample-report/", "es": "/es/informe-de-ejemplo/", "ca": "/ca/informe-dexemple/"}
MODES = {"manual": ["alone", "you", "you", "you"], "auto": ["alone", "alone", "model", "model"],
         "bypass": ["alone", "alone", "alone", "alone"]}


class Six(unittest.TestCase):
    """GTM-227: both lessons in six steps, the entry page held back, and lesson 1's own pieces."""

    def test_six_steps_with_their_index(self):
        for paths, d in ((PATHS, DATA), (ONE_PATHS, ONE)):
            for lang in MESSAGES:
                s = page(lang, paths)
                for n in range(1, 7):
                    self.assertEqual(s.count(f'<section class="cs-step" id="p{n}">'), 1, (lang, n))
                    self.assertIn(f'<a href="#p{n}"><b>{n}</b>', s)
                    self.assertIn(course_pages.esc(d[lang]["labels"][n - 1]), s)
                self.assertIn(f'aria-label="{course_pages.esc(d[lang]["steps_aria"])}"', s)

    def test_who_decides_in_the_three_modes(self):
        """The table of the signed texts: who gives permission for each action, in each mode, in the three languages."""
        for lang in MESSAGES:
            M = ONE[lang]["try"]["modes"]
            self.assertEqual(M["states"], MODES, lang)
            self.assertEqual(list(M["buttons"]), ["manual", "auto", "bypass"])
            self.assertEqual(len(M["actions"]), 4)
            for mode in MODES:
                html = course_pages.rows(M, mode)
                self.assertEqual(html.count('class="cs-row"'), 4)
                for k, key in enumerate(MODES[mode]):
                    self.assertIn(f'<span class="cs-num">{k + 1}</span><span>{course_pages.esc(M["actions"][k])}</span></div>'
                                  f'<span class="cs-mtag {key}">{course_pages.esc(M["tags"][key])}</span>', html)

    def test_manual_is_the_first_state_without_the_script(self):
        for lang in MESSAGES:
            s, M = page(lang, ONE_PATHS), ONE[lang]["try"]["modes"]
            self.assertIn(f'aria-checked="true" tabindex="0" data-m="manual">{course_pages.esc(M["buttons"]["manual"])}', s)
            self.assertIn(f'<div class="cs-rows" id="cs-rows" aria-live="polite">{course_pages.rows(M, "manual")}</div>', s)
            self.assertIn(f'<p class="cs-msg manual" id="cs-mmsg" role="status">{course_pages.fmt(M["msg"]["manual"])}</p>', s)
            for m in M["msg"].values():
                self.assertIn(json.dumps(m, ensure_ascii=False), s)  # the script's copy

    def test_the_note_carries_the_date_of_the_check(self):
        want = {"es": "comprobada el 26 de noviembre de 2026.", "en": "checked on 26 November 2026.",
                "ca": "comprovada el 26 de novembre de 2026."}
        for lang, w in want.items():
            self.assertIn(course_pages.esc(w), page(lang, ONE_PATHS))
            self.assertNotIn("{fecha", page(lang, ONE_PATHS))

    def test_game_of_lesson_1(self):
        """Six cases, two answers that go on their own; right answers as in the signed texts."""
        for lang in MESSAGES:
            G = ONE[lang]["check"]["game"]
            self.assertEqual(len(G["options"]), 2)
            self.assertEqual(G["exclusive"], [0, 1])
            self.assertEqual([i["answer"] for i in G["items"]], [[0], [1], [0], [0], [1], [1]], lang)
            self.assertEqual(G["question"], "")

    def test_test_of_lesson_1(self):
        for lang in MESSAGES:
            Q = ONE[lang]["check"]["test"]
            self.assertEqual(len(Q["items"]), 4)
            self.assertTrue(all(len(i["options"]) == 3 for i in Q["items"]))
            self.assertEqual([i["answer"] for i in Q["items"]], [1, 1, 1, 1], lang)
            self.assertIn("{score}", Q["result"])

    def test_lesson_2_keeps_its_answers(self):
        for lang in MESSAGES:
            G = DATA[lang]["check"]["game"]
            self.assertEqual([i["answer"] for i in G["items"]], [[1], [2, 3], [0], [3], [4], [1]], lang)
            self.assertEqual(G["exclusive"], [4])
            self.assertEqual([i["answer"] for i in DATA[lang]["check"]["test"]["items"]], [1, 1, 1, 1], lang)

    def test_sample_report_link_in_step_5(self):
        for lang in MESSAGES:
            s = page(lang, ONE_PATHS)
            self.assertEqual(s.count(f'<a href="{SAMPLE[lang]}">'), 1, lang)

    def test_lesson_1_leads_to_lesson_2(self):
        for lang in MESSAGES:
            self.assertIn(f'<a class="cs-btn primary" href="{PATHS[lang]}">{course_pages.esc(ONE[lang]["take"]["button"])}</a>',
                          page(lang, ONE_PATHS))

    def test_no_link_to_academy_while_it_is_closed(self):
        """GTM-227 point 4, now GTM-230: while Academy is closed, no page for it and no «Back to Academy» button."""
        self.assertFalse(academy.is_open(ENTRY))
        built = course_pages.pages()
        for p in ENTRY["path"].values():
            self.assertNotIn(p, built)
            self.assertFalse((SITE / p.strip("/") / "index.html").exists(), p)
        for lang in MESSAGES:
            for paths in (PATHS, ONE_PATHS):
                s = page(lang, paths)
                self.assertNotIn(ENTRY[lang]["back"], s, lang)
                for p in ENTRY["path"].values():
                    self.assertNotIn(f'href="{p}"', s)

    def test_back_to_academy_once_open(self):
        """Rendered in memory only: with the switch open, lesson 2 ends with «Back to Academy»; lesson 1 still leads to
        lesson 2."""
        e = dict(json.loads(json.dumps(ENTRY)), open=True)
        built = course_pages.pages(academy=e)
        for lang in MESSAGES:
            self.assertIn(f'<a class="cs-btn primary" href="{ENTRY["path"][lang]}">{course_pages.esc(ENTRY[lang]["back"])}</a>',
                          built[PATHS[lang]])
            self.assertIn(f'<a class="cs-btn primary" href="{PATHS[lang]}">{course_pages.esc(ONE[lang]["take"]["button"])}</a>',
                          built[ONE_PATHS[lang]])
            # Spec §6.1: lesson 1 keeps its button and gets «Back to Academy» under it, as a text link.
            self.assertIn(f'<a class="cs-btn primary" href="{PATHS[lang]}">{course_pages.esc(ONE[lang]["take"]["button"])}</a></p>'
                          f'<p class="cs-back"><a href="{ENTRY["path"][lang]}">{course_pages.esc(ENTRY[lang]["back"])}</a></p>',
                          built[ONE_PATHS[lang]])
            self.assertNotIn('class="cs-back"', built[PATHS[lang]])

    def test_no_braces_in_sight(self):
        """GTM-229: no { or } is left for a reader to see, in the served HTML or in the texts the script shows
        (where only {i}, {score} and {source} are placeholders the script fills in)."""
        for paths in (PATHS, ONE_PATHS):
            for lang in MESSAGES:
                s = page(lang, paths)
                body = s[s.index("<main"):s.index("</main>")]
                text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S))
                m = re.search(r".{0,40}[{}].{0,40}", text)
                self.assertIsNone(m, (lang, paths[lang], m and m.group(0)))
                data = json.loads(re.search(r'<script type="application/json" id="cs-data">(.*?)</script>', s, re.S).group(1))
                for x in course_pages.strings(data):
                    self.assertNotRegex(re.sub(r"\{(i|score|source)\}", "", x), r"[{}]", (lang, x))

    def test_english_quotes(self):
        for paths in (PATHS, ONE_PATHS):
            s = page("en", paths)
            body = s[s.index('<main'):s.index('</main>')]
            self.assertNotIn("«", body)
            self.assertIn("“", body)


class Script(unittest.TestCase):
    def test_no_writes_to_the_address_or_storage_and_nothing_sent(self):
        code = re.sub(r"//[^\n]*", "", JS)
        for word in ("location", "history", "localStorage", "sessionStorage", "indexedDB", "cookie",
                     "fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "postMessage", "navigator"):
            self.assertNotIn(word, code, word)


if __name__ == "__main__":
    unittest.main()
