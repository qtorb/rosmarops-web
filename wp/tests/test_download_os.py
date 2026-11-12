"""GTM-137 (Albert, 12-11 17:49): the home's download rows are the same for every visitor, with no system detection:
the Microsoft Store badge (Windows), «Mac (preview)» and «Linux», at the same height, and under them the GitHub
legend (T1) with the direct Windows download. Checks the served HTML of the three homes, and the layout in Chromium
with Windows, Mac and Linux agents. (Formerly the tests of site/assets/download/os.js, GTM-129, removed by GTM-137.)

Run from the repository root:  python3 -m unittest wp/tests/test_download_os.py   (Chromium part needs node playwright)
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOMES = {"en": ROOT / "site" / "index.html", "es": ROOT / "site" / "es" / "index.html", "ca": ROOT / "site" / "ca" / "index.html"}
PATHS = {"en": "/", "es": "/es/", "ca": "/ca/"}
BASE = {"en": "", "es": "/es", "ca": "/ca"}
DL = {"en": "/download", "es": "/es/descargar", "ca": "/ca/descarregar"}
MAC = {"en": "Mac (preview)", "es": "Mac (vista previa)", "ca": "Mac (vista prèvia)"}
STORE = {"en": "Download from the Microsoft Store", "es": "Descargar desde Microsoft Store", "ca": "Descarrega del Microsoft Store"}
AUTH = {"en": "How to check it's authentic", "es": "Cómo comprobar que es auténtico", "ca": "Com comprovar que és autèntic"}
SRC = ("home", "home-band")


class ServedHtml(unittest.TestCase):
    def rows(self, html):
        return re.findall(r'<div class="dlrow">(.*?)</div>\n<p class="gh">(.*?)</p>', html)

    def test_three_options_and_the_github_legend(self):
        for lang, page in HOMES.items():
            html = page.read_text(encoding="utf-8")
            rows = self.rows(html)
            self.assertEqual(len(rows), 2, lang)
            for (row, gh), src in zip(rows, SRC):
                links = re.findall(r'<a ([^>]*)>(.*?)</a>', row)
                self.assertEqual([re.search(r'href="([^"]*)"', a).group(1) for a, _ in links],
                                 [f"{DL[lang]}?from={src}&amp;os=store", f"{BASE[lang]}/macos/", f"{BASE[lang]}/linux/"], (lang, src))
                self.assertIn(f'alt="{STORE[lang]}"', links[0][1], (lang, src))
                self.assertEqual([t for _, t in links[1:]], [MAC[lang], "Linux"], (lang, src))
                gh_links = re.findall(r'<a [^>]*href="([^"]*)"[^>]*>(.*?)</a>', gh)
                self.assertEqual(gh_links[0], (f"{DL[lang]}?from={src}&amp;os=windows", "GitHub"), (lang, src))
                # «How to check it's authentic» only under the hero row.
                self.assertEqual(len(gh_links), 2 if src == "home" else 1, (lang, src))
                if src == "home":
                    self.assertEqual(gh_links[1][1], AUTH[lang].replace("'", "'"), lang)

    def test_no_system_detection_and_no_windows_button(self):
        for lang, page in HOMES.items():
            html = page.read_text(encoding="utf-8")
            self.assertNotIn("os.js", html, lang)
            self.assertIsNone(re.search(r"<[^>]*\shidden[\s>=]", re.search(r"<main>.*</main>", html, re.S).group(0)), lang)  # nothing hidden by system
            self.assertNotIn({"en": "Download for Windows", "es": "Descargar para Windows", "ca": "Descarrega per a Windows"}[lang], html, lang)
            self.assertNotIn({"en": "Or install it from the Microsoft Store", "es": "O instálalo desde la Microsoft Store",
                              "ca": "O instal·la'l des de la Microsoft Store"}[lang], html, lang)
        self.assertFalse((ROOT / "site" / "assets" / "download" / "os.js").exists())


class Layout(unittest.TestCase):
    """In Chromium (wp/tests/download-os-layout.js); skipped where Playwright is not installed."""

    def layout(self, path, width, agent, font=None):
        if not shutil.which("node") or subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode:
            self.skipTest("node playwright not installed")
        env = dict(os.environ, LAYOUT_FONT=font) if font else None
        p = subprocess.run(["node", str(Path(__file__).parent / "download-os-layout.js"), str(ROOT / "site"), path, str(width), agent],
                           capture_output=True, text=True, check=True, timeout=120, env=env)
        return json.loads(p.stdout)

    def test_1280_same_row_for_everyone_above_800_px(self):
        # GTM-137 §2.1: the drawing must not push the download row below 800 px at 1280. Measured with the runner's own
        # system-ui (DejaVu Sans on Ubuntu, the widest seen) and with Liberation Sans (Arial's metrics).
        for lang, path in PATHS.items():
            for agent in ("windows", "mac", "linux"):
                for font in (None, "Liberation Sans"):
                    r = self.layout(path, 1280, agent, font=font)
                    self.assertLess(r["heroRowBottom"], 800, (lang, agent, font))
                    for row in r["rows"]:
                        self.assertEqual([t for t, _, _ in row], [STORE[lang], MAC[lang], "Linux"], (lang, agent, font))
                        self.assertEqual(len({h for _, _, h in row}), 1, row)  # the same height
                        self.assertEqual(len({top for _, top, _ in row}), 1, row)  # on one line
                    self.assertEqual(r["others"], [["GitHub", AUTH[lang]], ["GitHub"]], (lang, agent))

    def test_390_one_per_line_and_no_horizontal_scroll(self):
        for lang, path in PATHS.items():
            for agent in ("windows", "mac"):
                r = self.layout(path, 390, agent)
                self.assertFalse(r["overflow"], (lang, agent))
                for row in r["rows"]:
                    self.assertEqual(len({top for _, top, _ in row}), 3, row)


if __name__ == "__main__":
    unittest.main()
