"""GTM-129 and GTM-137: the home's download rows follow the visitor's system (site/assets/download/os.js), run in node
against the real rows of the three homes with a minimal DOM, and in Chromium for the layout. Without JavaScript the
HTML stays as served: Windows first, the Store badge, and the three systems in the line of other systems.

Run from the repository root:  python3 -m unittest wp/tests/test_download_os.py   (needs node on PATH)
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "site" / "assets" / "download" / "os.js"
HOMES = {"en": ROOT / "site" / "index.html", "es": ROOT / "site" / "es" / "index.html", "ca": ROOT / "site" / "ca" / "index.html"}
BASE = {"en": "", "es": "/es", "ca": "/ca"}
DL = {"en": "/download", "es": "/es/descargar", "ca": "/ca/descarregar"}
WIN = {"en": "Download for Windows", "es": "Descargar para Windows", "ca": "Descarrega per a Windows"}
MAC = {"en": "Download for Mac", "es": "Descargar para Mac", "ca": "Descarrega per a Mac"}
LINUX = {"en": "Download for Linux", "es": "Descargar para Linux", "ca": "Descarrega per a Linux"}
SRC = ("home", "home-band")

AGENTS = {
    "windows": {"platform": "Win32", "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "maxTouchPoints": 0},
    "windows-chrome": {"userAgentData": {"platform": "Windows"}, "platform": "Win32", "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0", "maxTouchPoints": 0},
    "mac": {"platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15", "maxTouchPoints": 0},
    "mac-chrome": {"userAgentData": {"platform": "macOS"}, "platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130.0", "maxTouchPoints": 0},
    "linux": {"platform": "Linux x86_64", "userAgent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0", "maxTouchPoints": 0},
    "android": {"userAgentData": {"platform": "Android"}, "platform": "Linux armv8l", "userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36", "maxTouchPoints": 5},
    "android-old": {"platform": "Linux armv8l", "userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36", "maxTouchPoints": 5},
    "ipad": {"platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", "maxTouchPoints": 5},
    "iphone": {"platform": "iPhone", "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1", "maxTouchPoints": 5},
    "chromeos": {"userAgentData": {"platform": "Chrome OS"}, "platform": "Linux x86_64", "userAgent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) Chrome/130.0", "maxTouchPoints": 0},
}

# A minimal DOM: the .dlrow rows (their <a> with attributes and text), the .os-o items and the .store elements.
HARNESS = r"""
const [src, page, nav] = process.argv.slice(2);
const html = require('fs').readFileSync(page, 'utf8');
const unesc = s => s.replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"');
function parseAttrs(s) { const a = {}; s.replace(/([\w-]+)="([^"]*)"/g, (m, k, v) => { a[k] = unesc(v); }); return a; }
function el(attrs, text, kids) {
  return { attrs, textContent: text, hidden: false, kids: kids || [],
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    setAttribute(k, v) { this.attrs[k] = v; }, removeAttribute(k) { delete this.attrs[k]; },
    querySelector(q) { return this.kids.find(c => q === 'a' || (q === '.primary' && /\bprimary\b/.test(c.attrs['class'] || ''))) || null; } };
}
const anchors = s => { const out = []; s.replace(/<a ([^>]*)>(.*?)<\/a>/g, (m, at, tx) => { out.push(el(parseAttrs(at), unesc(tx.replace(/<[^>]+>/g, '')))); }); return out; };
const rows = [], items = [], stores = [];
html.replace(/<div class="dlrow">(.*?)<\/div>/g, (m, inner) => { rows.push(el({}, '', anchors(inner))); });
html.replace(/<span class="os-o" data-os="(\w+)">(.*?)<\/span>/g, (m, k, inner) => { items.push(el({ 'data-os': k }, '', anchors(inner))); });
html.replace(/<(a|p) class="store[^"]*"([^>]*)>/g, (m, tag, rest) => { stores.push(el({ tag }, '')); });
const lang = (html.match(/<html lang="([^"]+)"/) || [])[1];
const doc = { documentElement: { lang }, querySelectorAll(q) { return q === '.dlrow' ? rows : q === '.os-o' ? items : q === '.store' ? stores : []; } };
const mod = { exports: {} };
new Function('module', 'navigator', 'document', require('fs').readFileSync(src, 'utf8'))(mod, {}, {});
const os = mod.exports.detect(JSON.parse(nav));
mod.exports.apply(doc, os);
console.log(JSON.stringify({ os,
  mains: rows.map(r => { const a = r.querySelector('.primary'); return { text: a.textContent, href: a.attrs.href, target: a.attrs.target || null, rel: a.attrs.rel || null }; }),
  others: items.map(i => ({ os: i.attrs['data-os'], hidden: i.hidden, href: i.kids[0].attrs.href, text: i.kids[0].textContent })),
  stores: stores.map(s => ({ tag: s.attrs.tag, hidden: s.hidden })) }));
"""


class DownloadOs(unittest.TestCase):
    def run_js(self, lang, agent):
        if not shutil.which("node"):
            self.skipTest("node not on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(HARNESS)
        try:
            p = subprocess.run(["node", f.name, str(SCRIPT), str(HOMES[lang]), json.dumps(AGENTS[agent])],
                               capture_output=True, text=True, check=True)
        finally:
            os.unlink(f.name)
        return json.loads(p.stdout)

    def windows_main(self, lang, src):
        return {"text": WIN[lang], "href": f"{DL[lang]}?from={src}&os=windows", "target": "_blank", "rel": "nofollow noopener"}

    def others(self, lang, hide=None):
        b = BASE[lang]
        names = {"en": "Mac (preview)", "es": "Mac (vista previa)", "ca": "Mac (vista prèvia)"}[lang]
        out = []
        for src in SRC:
            out += [{"os": "windows", "hidden": hide == "windows", "href": f"{DL[lang]}?from={src}&os=windows", "text": "Windows"},
                    {"os": "mac", "hidden": hide == "mac", "href": f"{b}/macos/", "text": names},
                    {"os": "linux", "hidden": hide == "linux", "href": f"{b}/linux/", "text": "Linux"}]
        return out

    def test_unknown_phones_and_tablets_keep_the_served_html(self):
        for lang in HOMES:
            for agent in ("android", "android-old", "ipad", "iphone", "chromeos"):
                r = self.run_js(lang, agent)
                self.assertEqual(r["os"], "", (lang, agent))
                self.assertEqual(r["mains"], [self.windows_main(lang, s) for s in SRC], (lang, agent))
                self.assertEqual(r["others"], self.others(lang), (lang, agent))  # the three systems
                self.assertFalse(any(s["hidden"] for s in r["stores"]), (lang, agent))

    def test_windows(self):
        for lang in HOMES:
            for agent in ("windows", "windows-chrome"):
                r = self.run_js(lang, agent)
                self.assertEqual(r["os"], "windows", agent)
                self.assertEqual(r["mains"], [self.windows_main(lang, s) for s in SRC], (lang, agent))
                self.assertEqual(r["others"], self.others(lang, hide="windows"), (lang, agent))  # Mac and Linux
                self.assertEqual(len(r["stores"]), 3, lang)  # badge in each row and the Store line of the close
                self.assertFalse(any(s["hidden"] for s in r["stores"]), (lang, agent))

    def test_mac(self):
        for lang in HOMES:
            for agent in ("mac", "mac-chrome"):
                r = self.run_js(lang, agent)
                self.assertEqual(r["os"], "mac")
                self.assertEqual(r["mains"], [{"text": MAC[lang], "href": f"{BASE[lang]}/macos/", "target": None, "rel": None}] * 2, (lang, agent))
                self.assertEqual(r["others"], self.others(lang, hide="mac"), (lang, agent))  # Windows (with its counter) and Linux
                self.assertTrue(all(s["hidden"] for s in r["stores"]), (lang, agent))

    def test_linux(self):
        for lang in HOMES:
            r = self.run_js(lang, "linux")
            self.assertEqual(r["os"], "linux")
            self.assertEqual(r["mains"], [{"text": LINUX[lang], "href": f"{BASE[lang]}/linux/", "target": None, "rel": None}] * 2, lang)
            self.assertEqual(r["others"], self.others(lang, hide="linux"), lang)
            self.assertTrue(all(s["hidden"] for s in r["stores"]), lang)

    def test_without_javascript_the_html_is_as_served(self):
        for lang, page in HOMES.items():
            html = page.read_text(encoding="utf-8")
            self.assertEqual(html.count('<script src="/assets/download/os.js?v=4" defer></script>'), 1, lang)
            self.assertEqual(html.count('<div class="dlrow">'), 2, lang)
            self.assertEqual(html.count('<p class="oth">'), 2, lang)
            self.assertEqual(html.count('class="os-o"'), 6, lang)
            for src in SRC:
                self.assertEqual(html.count(f'{DL[lang]}?from={src}&amp;os=store'), 1, (lang, src))
            self.assertIn(".store[hidden]{display:none}", html, lang)
            self.assertIn(".os-o[hidden]{display:none}", html, lang)

    def test_nothing_stored_or_sent(self):
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", SCRIPT.read_text(encoding="utf-8"), flags=re.S).lower()
        for w in ("fetch", "xmlhttprequest", "sendbeacon", "cookie", "localstorage", "sessionstorage", "indexeddb"):
            self.assertNotIn(w, code, w)


class Layout(unittest.TestCase):
    """GTM-129b and GTM-137 in Chromium (wp/tests/download-os-layout.js); skipped where Playwright is not installed."""

    def layout(self, path, width, agent):
        if not shutil.which("node") or subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode:
            self.skipTest("node playwright not installed")
        p = subprocess.run(["node", str(Path(__file__).parent / "download-os-layout.js"), str(ROOT / "site"), path, str(width), agent],
                           capture_output=True, text=True, check=True, timeout=120)
        return json.loads(p.stdout)

    def test_es_mac_1280_main_button_on_one_line_without_the_store(self):
        r = self.layout("/es/", 1280, "mac")
        self.assertEqual([[t for t, _, _ in row] for row in r["rows"]], [["Descargar para Mac"]] * 2)
        for row in r["rows"]:
            self.assertLessEqual(row[0][2], 50, row)  # one line
        self.assertEqual(r["others"], [["Windows", "Linux"]] * 2)

    def test_windows_1280_row_above_800_px_and_side_by_side(self):
        # GTM-137 §2.1: the drawing must not push the download row below 800 px at 1280.
        for path, lang in (("/", "en"), ("/es/", "es"), ("/ca/", "ca")):
            r = self.layout(path, 1280, "windows")
            self.assertLess(r["heroRowBottom"], 800, lang)
            for row in r["rows"]:
                self.assertEqual(row[0][0], WIN[lang])
                self.assertEqual(len(row), 2, row)
                mids = [top + h / 2 for _, top, h in row]
                self.assertLessEqual(max(mids) - min(mids), 2, row)  # vertically centred on one line
            self.assertEqual(r["others"], [["Mac (preview)" if lang == "en" else "Mac (vista previa)" if lang == "es" else "Mac (vista prèvia)", "Linux"]] * 2)

    def test_390_no_horizontal_scroll(self):
        for path in ("/", "/es/", "/ca/"):
            for agent in ("windows", "mac"):
                self.assertFalse(self.layout(path, 390, agent)["overflow"], (path, agent))


if __name__ == "__main__":
    unittest.main()
