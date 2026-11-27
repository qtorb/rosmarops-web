"""GTM-230: RosmarOps Academy (observatory/academy.py), its page and its place in the menu, behind one switch.

Run from the repository root:  python3 -m unittest observatory/tests/test_academy.py
(The 390 px layout test needs node and playwright; it is skipped without them.)
"""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import academy  # noqa: E402
import course_pages  # noqa: E402
import sandbox_section  # noqa: E402
import videos_pages  # noqa: E402

SITE = ROOT / "site"
LANGS = ("en", "es", "ca")
DATA = academy.load()
OPEN = dict(copy.deepcopy(DATA), open=True)
LESSONS = course_pages.load_all()
LESSON_PATHS = [LESSONS[n]["path"] for n in course_pages.LESSONS]

# Spec §1.3: the header menus, closed (today) and open.
INNER = {
    "en": ["Blog", "About", "Observatory", "Sandbox", "Methodology", "FAQ", "ES", "CA"],
    "es": ["Blog", "Acerca de", "Observatorio", "Sandbox", "Metodología", "Preguntas", "EN", "CA"],
    "ca": ["Bloc", "Quant a", "Observatori", "Sandbox", "Metodologia", "Preguntes", "EN", "ES"],
}
INNER_OPEN = {
    "en": ["Blog", "About", "Observatory", "Sandbox", "Academy", "Methodology", "ES", "CA"],
    "es": ["Blog", "Acerca de", "Observatorio", "Sandbox", "Academy", "Metodología", "EN", "CA"],
    "ca": ["Bloc", "Quant a", "Observatori", "Sandbox", "Academy", "Metodologia", "EN", "ES"],
}
HOME = {
    "en": ["Blog", "About", "Observatory", "Sandbox", "Your space", "ES", "CA"],
    "es": ["Blog", "Acerca de", "Observatorio", "Sandbox", "Tu espacio", "EN", "CA"],
    "ca": ["Bloc", "Quant a", "Observatori", "Sandbox", "El teu espai", "EN", "ES"],
}
HOME_OPEN = {l: e[:4] + ["Academy"] + e[4:] for l, e in HOME.items()}
HOMES = {"en": "index.html", "es": "es/index.html", "ca": "ca/index.html"}
INNER_PAGE = {"en": "methodology/index.html", "es": "es/metodologia/index.html", "ca": "ca/metodologia/index.html"}
OBS_PAGE = {"en": "observatory/index.html", "es": "es/observatorio/index.html", "ca": "ca/observatori/index.html"}


def site_pages():
    """Every page in site/ with the site menu, and the daily shells: (name, lang, html)."""
    out = []
    for f in sorted(list(SITE.rglob("*.html")) + sorted((ROOT / "wp" / "daily").glob("shell-*.html"))):
        s = f.read_text(encoding="utf-8")
        lang = academy.page_lang(s) or (f.stem[-2:] if f.stem.startswith("shell-") else None)
        if lang and "<header" in s and academy.nav(s, lang, True, OPEN) != s:
            out.append((str(f.relative_to(ROOT)), lang, s))
    return out


PAGES = site_pages()


class Closed(unittest.TestCase):
    """The repository as delivered: the switch is closed and nothing of Academy shows."""

    def test_delivered_closed(self):
        self.assertIs(DATA["open"], False)
        self.assertEqual(academy.pages(), {})
        self.assertEqual(academy.sitemap_urls(), [])

    def test_site_matches_the_switch(self):
        self.assertEqual(academy.check_site(), [])

    def test_no_academy_page_and_no_link_to_it(self):
        for lang in LANGS:
            self.assertFalse((SITE / DATA["path"][lang].strip("/")).exists())
        for name, lang, s in PAGES:
            for p in DATA["path"].values():
                self.assertNotIn(f'href="{p}"', s, name)

    def test_menus_are_the_ones_of_today(self):
        for name, lang, s in PAGES:
            want = HOME[lang] if name == "site/" + HOMES[lang] else INNER[lang]
            self.assertEqual(academy.menu_entries(s), want, name)

    def test_lessons_noindex_out_of_the_sitemap_and_no_back_button(self):
        sm = (SITE / "sitemap-pages.xml").read_text(encoding="utf-8")
        for paths in LESSON_PATHS:
            for lang, p in paths.items():
                s = (SITE / p.strip("/") / "index.html").read_text(encoding="utf-8")
                self.assertIn('<meta name="robots" content="noindex">', s)
                self.assertNotIn(f"<loc>https://rosmarops.com{p}</loc>", sm)
                self.assertNotIn(DATA[lang]["back"], s)

    def test_no_course_entry_page(self):
        for p in ("course", "es/curso", "ca/curs"):
            self.assertFalse((SITE / p / "index.html").exists(), p)
        self.assertFalse((ROOT / "observatory" / "data" / "course" / "course.json").exists())
        self.assertFalse(hasattr(course_pages, "entry_html"))


class Open(unittest.TestCase):
    """The switch open, in memory: the page, the menu, the lessons and the sitemap."""

    @classmethod
    def setUpClass(cls):
        cls.pages = academy.pages(OPEN)
        cls.lessons = course_pages.pages(academy=OPEN)

    def test_three_pages(self):
        self.assertEqual(sorted(self.pages), sorted(OPEN["path"].values()))
        for lang in LANGS:
            s = self.pages[OPEN["path"][lang]]
            t = OPEN[lang]
            self.assertIn("<title>RosmarOps Academy</title>", s)
            self.assertIn(f'<meta name="description" content="{academy.esc(t["lead"])}">', s)
            self.assertNotIn('name="robots"', s)
            self.assertIn(f'<link rel="canonical" href="https://rosmarops.com{OPEN["path"][lang]}">', s)
            for k in ("eyebrow", "h1", "lead", "what.h2", "what.p", "why.h2", "why.1", "why.2", "why.3", "who.h2", "who.p", "ex.h2",
                      "ex.p", "course.h2", "course.title", "course.meta", "course.need", "course.cta", "videos.h2", "videos.p",
                      "videos.all", "foot"):
                self.assertIn(academy.esc(t[k]), s, (lang, k))
            self.assertEqual(academy.menu_entries(s), INNER_OPEN[lang])
            self.assertIn(f'<a href="{OPEN["path"][lang]}" aria-current="page">Academy</a>', s)

    def test_five_lessons_two_linked_three_coming_soon(self):
        for lang in LANGS:
            s = self.pages[OPEN["path"][lang]]
            self.assertEqual(s.count('class="cs-lesson"'), 5)
            for paths in LESSON_PATHS:
                self.assertIn(f'<a class="cs-lesson" href="{paths[lang]}">', s)
            self.assertEqual(s.count(f'<span class="cs-pill-soon">{academy.esc(OPEN[lang]["soon"])}</span>'), 3)
            for h, txt in OPEN[lang]["course.lessons"]:
                self.assertIn(f"<b>{academy.esc(h)}</b>", s)
            # Spec §2: lessons 3 to 5 carry the pill, not the «Coming soon.» line.
            self.assertEqual([x[1] for x in OPEN[lang]["course.lessons"][2:]], ["", "", ""])
            self.assertIn(f'<a class="cs-btn primary" href="{LESSON_PATHS[0][lang]}">{academy.esc(OPEN[lang]["course.cta"])}</a>', s)

    def test_videos_as_on_the_videos_index(self):
        videos = videos_pages.load()
        for lang in LANGS:
            s = self.pages[OPEN["path"][lang]]
            self.assertIn(f'<ul class="vl" style="margin-top:28px">{videos_pages.cards(videos, lang)}</ul>', s)
            index = (SITE / videos_pages.INDEX[lang].strip("/") / "index.html").read_text(encoding="utf-8")
            self.assertIn(videos_pages.cards(videos, lang), index)
            self.assertIn(f'<a href="{videos_pages.INDEX[lang]}">{academy.esc(OPEN[lang]["videos.all"])}</a>', s)

    def test_lessons_open(self):
        for paths in LESSON_PATHS:
            for lang in LANGS:
                s = self.lessons[paths[lang]]
                self.assertNotIn('name="robots"', s)
                self.assertEqual(academy.menu_entries(s), INNER_OPEN[lang])
                self.assertIn(f'<a href="{OPEN["path"][lang]}" aria-current="page">Academy</a>', s)
        for lang in LANGS:
            two = self.lessons[LESSON_PATHS[1][lang]]
            self.assertIn(f'<a class="cs-btn primary" href="{OPEN["path"][lang]}">{academy.esc(OPEN[lang]["back"])}</a>', two)

    def test_sitemap(self):
        urls = academy.sitemap_urls(OPEN)
        self.assertEqual(sorted(p for p, _ in urls), sorted([OPEN["path"][l] for l in LANGS] + [p[l] for p in LESSON_PATHS for l in LANGS]))

    def test_every_menu_open_and_back(self):
        """Every page of the site and the daily shells: open gives the menus of spec §1.3, and closing gives back the
        page as it is today, byte for byte. Only the header menu changes: the footer keeps «FAQ»."""
        for name, lang, s in PAGES:
            o = academy.nav(s, lang, True, OPEN)
            home = name == "site/" + HOMES[lang]
            self.assertEqual(academy.menu_entries(o), (HOME_OPEN if home else INNER_OPEN)[lang], name)
            self.assertEqual(academy.nav(o, lang, True, OPEN), o, name)  # idempotent
            self.assertEqual(academy.nav(o, lang, False, OPEN), s, name)
            foot = re.search(r"<footer\b.*?</footer>", s, re.S)
            if foot:
                self.assertIn(foot.group(0), o, name)

    def test_generated_headers_open(self):
        """The generated sources follow the switch through academy.nav(): the guide shell and the Observatory header."""
        for lang in LANGS:
            header = sandbox_section.shell_parts(lang)[1]
            self.assertEqual(academy.menu_entries(academy.nav(header, lang, True, OPEN)), INNER_OPEN[lang])


class MenuAcrossPages(unittest.TestCase):
    """GTM-230 point 7: the header menu of the hand-written pages and of the generated ones must not drift apart. Every
    inner page of a language has the same entries, every home the same, in both states of the switch."""

    def test_same_entries_everywhere(self):
        kinds = {}
        for name, lang, s in PAGES:
            home = name == "site/" + HOMES[lang]
            for state, data in (("closed", DATA), ("open", OPEN)):
                kinds.setdefault((lang, home, state), {}).setdefault(
                    tuple(academy.menu_entries(academy.nav(s, lang, data["open"], data))), []).append(name)
        for key, groups in kinds.items():
            self.assertEqual(len(groups), 1, (key, {k: v[:3] for k, v in groups.items()}))
        # Both kinds of source are in the comparison.
        names = [n for n, _, _ in PAGES]
        for must in ("site/es/metodologia/index.html", "site/es/observatorio/index.html", "site/es/sandbox/index.html",
                     "site/es/videos/index.html", "site/es/curso/la-cadena/index.html", "site/es/glosario/index.html",
                     "site/_static/about-en.html", "wp/daily/shell-es.html", "site/es/index.html"):
            self.assertIn(must, names)


class Safe(unittest.TestCase):
    def test_no_outside_resources_and_no_braces(self):
        for lang in LANGS:
            s = academy.pages(OPEN)[OPEN["path"][lang]]
            for u in re.findall(r'(?:src|href)="((?:https?:)?//[^"]+)"', s):
                self.assertTrue(u.startswith("https://rosmarops.com/"), u)
            self.assertNotRegex(s, r"<link [^>]*href=\"(?:https?:)?//(?!rosmarops\.com)")
            body = s[s.index("<main"):s.index("</main>")]
            text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S))
            m = re.search(r".{0,40}[{}].{0,40}", text)
            self.assertIsNone(m, (lang, m and m.group(0)))

    def test_english_quotes(self):
        for k, v in DATA["en"].items():
            for s in ([v] if isinstance(v, str) else sum(v, [])):
                self.assertNotIn("«", s, k)


# Spec §6.2: at 390 px the visitor is a phone. The menu with «Academy» must stay on two lines with the Windows-metric
# font (Liberation Sans), Chromium's default and Roboto (Android). With DejaVu Sans (desktop Linux) the lines measured
# on 27-11 are pinned so they do not get worse: Spanish inner page and home up to three, everything else two.
PHONE_FONTS = (None, "Liberation Sans", "Roboto")
DEJAVU_MAX = {"es": {"inner": 3, "home": 3, "obs": 2}, "en": {"inner": 2, "home": 2, "obs": 2}, "ca": {"inner": 2, "home": 2, "obs": 2}}


def font_installed(name):
    out = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True).stdout
    return any(name in line.split(",") for line in out.splitlines())


class Layout390(unittest.TestCase):
    """Spec §4 and §6.2: the header menu at 390 px with the switch open, in the three languages, on an inner page, a home
    and an Observatory page. Measured in Chromium (observatory/tests/academy-nav-layout.js) on copies of the pages;
    skipped where node playwright is not installed. CI installs Roboto as the system package fonts-roboto."""

    def measure(self, tmp, paths, font):
        env = dict(os.environ, LAYOUT_FONT=font) if font else None
        p = subprocess.run(["node", str(Path(__file__).parent / "academy-nav-layout.js"), tmp, "390", *paths],
                           capture_output=True, text=True, check=True, timeout=180, env=env)
        return json.loads(p.stdout)

    def test_lines_at_390(self):
        if not shutil.which("node") or subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode:
            self.skipTest("node playwright not installed")
        for f in ("Liberation Sans", "Roboto", "DejaVu Sans"):
            self.assertTrue(font_installed(f), f"font {f} is not installed (CI: fonts-liberation, fonts-roboto, fonts-dejavu-core)")
        with tempfile.TemporaryDirectory() as tmp:
            os.symlink(SITE / "assets", Path(tmp) / "assets")
            kind = {}
            for lang in LANGS:
                for k, rel in (("inner", INNER_PAGE[lang]), ("home", HOMES[lang]), ("obs", OBS_PAGE[lang])):
                    s = (SITE / rel).read_text(encoding="utf-8")
                    f = Path(tmp) / rel
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text(academy.nav(s, lang, True, OPEN), encoding="utf-8")
                    kind["/" + rel.replace("index.html", "")] = (lang, k)
            # Every font is measured before anything is asserted, so a failure reports all the measurements at once.
            seen, bad = {}, []
            for font in PHONE_FONTS + ("DejaVu Sans",):
                name = font or "Chromium default"
                for path, r in self.measure(tmp, list(kind), font).items():
                    lang, k = kind[path]
                    seen.setdefault(name, {})[path] = r["lines"]
                    most = DEJAVU_MAX[lang][k] if font == "DejaVu Sans" else 2
                    if "Academy" not in r["entries"] or r["lines"] > most or r["overflow"]:
                        bad.append((name, path, r))
            print("lines at 390 px:", json.dumps(seen))
            self.assertEqual(bad, [], json.dumps(seen))


if __name__ == "__main__":
    unittest.main()
