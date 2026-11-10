"""GTM-129: the home's download buttons follow the visitor's system (site/assets/download/os.js), run in node against
the real blocks of the three homes with a minimal DOM. Without JavaScript the HTML stays as served.

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
MAC = {"en": "Download for Mac", "es": "Descargar para Mac", "ca": "Descarrega per a Mac"}
LINUX = {"en": "Download for Linux", "es": "Descargar para Linux", "ca": "Descarrega per a Linux"}

AGENTS = {
    "windows": {"platform": "Win32", "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36", "maxTouchPoints": 0},
    "mac": {"platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15", "maxTouchPoints": 0},
    "mac-chrome": {"userAgentData": {"platform": "macOS"}, "platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/130.0", "maxTouchPoints": 0},
    "linux": {"platform": "Linux x86_64", "userAgent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0", "maxTouchPoints": 0},
    "android": {"userAgentData": {"platform": "Android"}, "platform": "Linux armv8l", "userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36", "maxTouchPoints": 5},
    "android-old": {"platform": "Linux armv8l", "userAgent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36", "maxTouchPoints": 5},
    "ipad": {"platform": "MacIntel", "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1", "maxTouchPoints": 5},
    "iphone": {"platform": "iPhone", "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1", "maxTouchPoints": 5},
    "chromeos": {"userAgentData": {"platform": "Chrome OS"}, "platform": "Linux x86_64", "userAgent": "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) Chrome/130.0", "maxTouchPoints": 0},
}

# A minimal DOM: the .dl blocks (their <a> in order, with attributes and text) and the .dl-note paragraphs of the page.
HARNESS = r"""
const [src, page, nav] = process.argv.slice(2);
const html = require('fs').readFileSync(page, 'utf8');
const unesc = s => s.replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"');
function el(attrs, text) {
  const e = { attrs, className: attrs['class'] || '', textContent: text, hidden: false,
    getAttribute(k) { return k === 'class' ? this.className : (k in this.attrs ? this.attrs[k] : null); } };
  return e;
}
function parseAttrs(s) { const a = {}; s.replace(/([\w-]+)="([^"]*)"/g, (m, k, v) => { a[k] = unesc(v); }); return a; }
const blocks = [];
html.replace(/<div class="dl">(.*?)<\/div>/g, (m, inner) => {
  const kids = [];
  inner.replace(/<a ([^>]*)>(.*?)<\/a>/g, (mm, at, tx) => { kids.push(el(parseAttrs(at), unesc(tx))); });
  blocks.push({ kids, getElementsByTagName() { return kids.slice(); },
    appendChild(c) { const i = kids.indexOf(c); if (i >= 0) kids.splice(i, 1); kids.push(c); } });
});
const notes = [];
html.replace(/<p class="dl-note">(.*?)<\/p>/g, (m, inner) => { notes.push(el({}, unesc(inner.replace(/<[^>]+>/g, '')))); });
const lang = (html.match(/<html lang="([^"]+)"/) || [])[1];
const doc = { documentElement: { lang }, querySelectorAll(q) { return q === '.dl' ? blocks : q === '.dl-note' ? notes : []; } };
const mod = { exports: {} };
new Function('module', 'navigator', 'document', require('fs').readFileSync(src, 'utf8'))(mod, {}, {});
const os = mod.exports.detect(JSON.parse(nav));
mod.exports.apply(doc, os);
console.log(JSON.stringify({ os, blocks: blocks.map(b => b.kids.map(k => ({ cls: k.className, text: k.textContent,
  href: k.attrs.href, target: k.attrs.target || null, rel: k.attrs.rel || null }))), notes: notes.map(n => ({ text: n.textContent.slice(0, 20), hidden: n.hidden })) }));
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

    def windows_btn(self, lang, src, text):
        return {"cls": text[0], "text": text[1], "href": f"{DL[lang]}?from={src}&os=windows", "target": "_blank", "rel": "nofollow noopener"}

    def served(self, lang):
        b = BASE[lang]
        return [[self.windows_btn(lang, src, ("hbtn primary", {"en": "Download for Windows", "es": "Descargar para Windows", "ca": "Descarrega per a Windows"}[lang])),
                 {"cls": "hbtn", "text": {"en": "Mac (preview)", "es": "Mac (vista previa)", "ca": "Mac (vista prèvia)"}[lang], "href": f"{b}/macos/", "target": None, "rel": None},
                 {"cls": "hbtn", "text": "Linux", "href": f"{b}/linux/", "target": None, "rel": None}] for src in ("home", "home-band")]

    def test_windows_phones_tablets_and_others_keep_the_served_html(self):
        for lang in HOMES:
            for agent in ("windows", "android", "android-old", "ipad", "iphone", "chromeos"):
                r = self.run_js(lang, agent)
                self.assertEqual(r["os"], "", (lang, agent))
                self.assertEqual(r["blocks"], self.served(lang), (lang, agent))
                self.assertFalse(any(n["hidden"] for n in r["notes"]), (lang, agent))

    def test_mac(self):
        for lang in HOMES:
            for agent in ("mac", "mac-chrome"):
                r = self.run_js(lang, agent)
                self.assertEqual(r["os"], "mac")
                b = BASE[lang]
                for src, block in zip(("home", "home-band"), r["blocks"]):
                    self.assertEqual(block, [
                        {"cls": "hbtn primary", "text": MAC[lang], "href": f"{b}/macos/", "target": None, "rel": None},
                        self.windows_btn(lang, src, ("hbtn", "Windows")),
                        {"cls": "hbtn", "text": "Linux", "href": f"{b}/linux/", "target": None, "rel": None}], (lang, agent, src))
                self.assertEqual([n["hidden"] for n in r["notes"]], [False, True], lang)  # only the Windows warning goes

    def test_linux(self):
        for lang in HOMES:
            r = self.run_js(lang, "linux")
            self.assertEqual(r["os"], "linux")
            b = BASE[lang]
            for src, block in zip(("home", "home-band"), r["blocks"]):
                self.assertEqual(block, [
                    {"cls": "hbtn primary", "text": LINUX[lang], "href": f"{b}/linux/", "target": None, "rel": None},
                    self.windows_btn(lang, src, ("hbtn", "Windows")),
                    {"cls": "hbtn", "text": {"en": "Mac (preview)", "es": "Mac (vista previa)", "ca": "Mac (vista prèvia)"}[lang], "href": f"{b}/macos/", "target": None, "rel": None}], (lang, src))
            self.assertEqual([n["hidden"] for n in r["notes"]], [False, True], lang)

    def test_without_javascript_the_html_is_as_served(self):
        # The only change to the pages is the script tag; the blocks and notes are exactly the served ones.
        for lang, page in HOMES.items():
            html = page.read_text(encoding="utf-8")
            self.assertEqual(html.count('<script src="/assets/download/os.js?v=2" defer></script>'), 1, lang)
            self.assertEqual(html.count('<div class="dl">'), 2, lang)
            self.assertEqual(len(re.findall(r'<p class="dl-note">Windows', html)), 1, lang)

    def test_nothing_stored_or_sent(self):
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", SCRIPT.read_text(encoding="utf-8"), flags=re.S).lower()
        for w in ("fetch", "xmlhttprequest", "sendbeacon", "cookie", "localstorage", "sessionstorage", "indexeddb"):
            self.assertNotIn(w, code, w)


if __name__ == "__main__":
    unittest.main()



class MacOneLine(unittest.TestCase):
    """GTM-129b: on the Spanish home, with a Mac agent at 1280 px, the three buttons of each .dl block share one line.
    Runs wp/tests/download-os-layout.js with Node Playwright; skipped where Playwright is not installed."""

    def test_es_mac_1280_buttons_on_one_line(self):
        if not shutil.which("node") or subprocess.run(["node", "-e", "require('playwright')"], capture_output=True).returncode:
            self.skipTest("node playwright not installed")
        p = subprocess.run(["node", str(Path(__file__).parent / "download-os-layout.js"), str(ROOT / "site"), "/es/", "1280"],
                           capture_output=True, text=True, check=True, timeout=120)
        blocks = json.loads(p.stdout)
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            self.assertEqual(len({top for _, top in block}), 1, block)
            self.assertEqual([t for t, _ in block], ["Descargar para Mac", "Windows", "Linux"])
