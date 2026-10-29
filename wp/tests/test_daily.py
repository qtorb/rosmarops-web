"""Tests for wp/mu-plugins/rosmarops-daily.php (GTM-23 §8), with a minimal WordPress stand-in and php -S.

Run from the repository root:  python3 -m unittest wp/tests/test_daily.py
Needs php (8.1+) on PATH.
"""

import copy
import json
import os
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "wp" / "tests"
VALID = ROOT / "observatory" / "tests" / "daily" / "2026-01-15.json"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Daily(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Path(cls.tmp.name) / "store.json"
        cls.env = dict(os.environ, DAILY_STORE=str(cls.store))
        cls.valid = json.loads(VALID.read_text(encoding="utf-8"))
        # A day with markup in a text (must come out escaped), and a no_changes day.
        xss = copy.deepcopy(cls.valid)
        xss["date"] = "2026-01-16"
        xss["summary_ref"] = "docs/observatorio/2026-01-16.md"
        xss["items"][1]["text"]["en"] = "<script>alert(1)</script> Example Agent 2.4.0"
        empty = copy.deepcopy(cls.valid)
        empty.update(date="2026-11-03", status="no_changes", items=[], summary_ref="docs/observatorio/2026-11-03.md")
        for d in (cls.valid, xss, empty):
            assert cls.store_day(d) == "stored", d["date"]
        cls.port = free_port()
        cls.srv = subprocess.Popen(["php", "-S", f"127.0.0.1:{cls.port}", str(TESTS / "daily-router.php")],
                                   env=cls.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.terminate()
        cls.srv.wait()
        cls.tmp.cleanup()

    @classmethod
    def store_day(cls, d, date=None):
        f = Path(cls.tmp.name) / "in.json"
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        out = subprocess.run(["php", str(TESTS / "daily-cli.php"), "store", str(f), date or d["date"]],
                             env=cls.env, capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def get(self, path, method="GET"):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        try:
            r = OPENER.open(req, timeout=5)
            return r.status, dict(r.headers), r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode("utf-8")

    # ---- pages

    def test_day_pages(self):
        for prefix, lang, title, host_text in [
            ("/observatory/daily/", "en", "Agent security today: 15 January 2026", "osv.dev"),
            ("/es/observatorio/diario/", "es", "Seguridad de los agentes hoy: 15 de enero de 2026", "osv.dev"),
            ("/ca/observatori/diari/", "ca", "Seguretat dels agents avui: 15 de gener de 2026", "osv.dev"),
        ]:
            st, h, body = self.get(prefix + "2026-01-15/")
            self.assertEqual(st, 200, prefix)
            self.assertIn("text/html", h["Content-Type"])
            self.assertEqual(h["Cache-Control"], "public, max-age=900")
            self.assertIn(f'<html lang="{lang}">', body)
            self.assertIn(f"<title>{title}</title>", body)
            self.assertIn(f"<h1>{title}</h1>", body)
            self.assertIn(f'<link rel="canonical" href="https://rosmarops.com{prefix}2026-01-15/">', body)
            self.assertIn('<link rel="alternate" hreflang="ca" href="https://rosmarops.com/ca/observatori/diari/2026-01-15/">', body)
            self.assertIn(f'<link rel="alternate" type="application/rss+xml"', body)
            self.assertIn(f'href="{prefix}feed.xml"', body)
            self.assertIn('<ol class="changes box"><li><p class="meta">', body)
            self.assertIn(f'rel="noopener">{host_text}</a>', body)
            self.assertIn(' · example-mcp-package · MAL-2026-1</p>', body)
            self.assertIn('<h2 id="checked">', body)
            self.assertIn('<p class="disclaimer">', body)
            self.assertNotIn("@@", body)
        _, _, body = self.get("/es/observatorio/diario/2026-01-15/")
        self.assertIn("El 14 de enero de 2026 el paquete de npm", body)
        self.assertIn("<h2 id=\"checked\">Qué hemos revisado</h2>", body)

    def test_markup_escaped(self):
        st, _, body = self.get("/observatory/daily/2026-01-16/")
        self.assertEqual(st, 200)
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)

    def test_no_changes_day(self):
        st, _, body = self.get("/ca/observatori/diari/2026-11-03/")
        self.assertEqual(st, 200)
        self.assertIn('<p class="empty box">No hem trobat canvis de seguretat en les fonts revisades.</p>', body)
        self.assertIn("3 de novembre de 2026", body)

    def test_index(self):
        st, _, body = self.get("/es/observatorio/diario/")
        self.assertEqual(st, 200)
        self.assertIn("<h1>La seguridad de los agentes, día a día</h1>", body)
        i1, i2, i3 = (body.index(f'href="/es/observatorio/diario/{d}/"') for d in ("2026-11-03", "2026-01-16", "2026-01-15"))
        self.assertLess(i1, i2)
        self.assertLess(i2, i3)

    def test_unknown_date_is_wordpress_404(self):
        st, _, body = self.get("/observatory/daily/2026-01-01/")
        self.assertEqual((st, body), (404, "wp-404"))

    def test_trailing_slash_redirect(self):
        for path in ("/observatory/daily", "/es/observatorio/diario", "/ca/observatori/diari/2026-01-15"):
            st, h, _ = self.get(path)
            self.assertEqual(st, 301, path)
            self.assertEqual(h["Location"], "https://rosmarops.com" + path + "/")
            self.assertNotIn(":443", h["Location"])

    def test_head_and_post(self):
        st, _, body = self.get("/observatory/daily/", method="HEAD")
        self.assertEqual((st, body), (200, ""))
        st, _, body = self.get("/observatory/daily/", method="POST")
        self.assertEqual((st, body), (404, "wp-404"))

    def test_feed(self):
        st, h, body = self.get("/observatory/daily/feed.xml")
        self.assertEqual(st, 200)
        self.assertIn("application/rss+xml", h["Content-Type"])
        root = ET.fromstring(body)
        self.assertEqual(root.findtext("channel/title"), "RosmarOps Observatory: agent security today")
        self.assertEqual(root.findtext("channel/language"), "en")
        items = root.findall("channel/item")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0].findtext("link"), "https://rosmarops.com/observatory/daily/2026-11-03/")
        self.assertEqual(items[0].findtext("description"), "No security changes found in the sources we checked.")
        self.assertTrue(items[1].findtext("pubDate").endswith("+0000"))
        self.assertIn("&lt;script&gt;", body)

    # ---- validation

    def rejected(self, mutate, date="2026-01-15"):
        d = copy.deepcopy(self.valid)
        mutate(d)
        self.assertEqual(self.store_day(d, date), "not stored")

    def test_reject_http(self):
        self.rejected(lambda d: d["items"][0].update(source_url="http://osv.dev/x"))

    def test_reject_host(self):
        self.rejected(lambda d: d["items"][0].update(source_url="https://evil.example/x"))

    def test_reject_lookalike_host(self):
        self.rejected(lambda d: d["items"][0].update(source_url="https://notgithub.com/x"))

    def test_reject_six_items(self):
        self.rejected(lambda d: d.update(items=d["items"] * 3))

    def test_reject_extra_key(self):
        self.rejected(lambda d: d.update(html="<p>x</p>"))

    def test_reject_wrong_date(self):
        self.rejected(lambda d: None, date="2026-01-14")

    def test_incomplete_not_stored(self):
        d = copy.deepcopy(self.valid)
        d.update(date="2026-01-20", status="incomplete", items=[], summary_ref="docs/observatorio/2026-01-20.md")
        self.assertEqual(self.store_day(d), "not stored")
        st, _, _ = self.get("/observatory/daily/2026-01-20/")
        self.assertEqual(st, 404)


if __name__ == "__main__":
    unittest.main()
