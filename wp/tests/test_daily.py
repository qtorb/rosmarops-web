"""Tests for wp/mu-plugins/rosmarops-daily.php (GTM-23 §8), with a minimal WordPress stand-in and php -S.

Run from the repository root:  python3 -m unittest wp/tests/test_daily.py
Needs php (8.1+) on PATH.
"""

import copy
import json
import os
import re
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

    # ---- «Today in the Observatory» (GTM-88)

    def today(self, d, lang):
        f = Path(self.tmp.name) / "today.json"
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return subprocess.run(["php", str(TESTS / "daily-cli.php"), "today", str(f), lang],
                              env=self.env, capture_output=True, text=True, check=True).stdout

    def test_today_route_uses_latest_day(self):
        for prefix, line, empty in [
            ("/observatory/daily/", "3 November 2026 · 2 sources checked", "No new changes in the sources today."),
            ("/es/observatorio/diario/", "3 de noviembre de 2026 · 2 fuentes revisadas", "Hoy no hay cambios nuevos en las fuentes."),
            ("/ca/observatori/diari/", "3 de novembre de 2026 · 2 fonts revisades", "Avui no hi ha canvis nous a les fonts."),
        ]:
            st, h, body = self.get(prefix + "today.html")
            self.assertEqual(st, 200, prefix)
            self.assertIn("text/html", h["Content-Type"])
            self.assertEqual(h["Cache-Control"], "public, max-age=900")
            self.assertEqual(h["X-Robots-Tag"], "noindex")
            self.assertEqual(body, f'<p class="note">{line}</p>\n<p class="empty box">{empty}</p>\n')

    def test_today_items(self):
        out = self.today(self.valid, "es")
        self.assertTrue(out.startswith('<p class="note">15 de enero de 2026 · 2 fuentes revisadas</p>\n<ol class="changes box"><li><p>El 14 de enero de 2026'), out)
        self.assertIn('<p class="meta">example-mcp-package · 14 de enero de 2026 · <a href="https://osv.dev/vulnerability/MAL-2026-1" rel="noopener">Fuente oficial</a></p></li>', out)
        self.assertEqual(out.count("<li>"), 2)
        self.assertNotIn("incompleta", out)
        self.assertIn("Official source</a>", self.today(self.valid, "en"))
        self.assertIn("Font oficial</a>", self.today(self.valid, "ca"))

    def test_today_escapes_and_caps(self):
        d = copy.deepcopy(self.valid)
        d["items"][1]["text"]["en"] = "<script>alert(1)</script> Example"
        d["items"][1]["subject"] = "<b>x</b>"
        out = self.today(d, "en")
        self.assertNotIn("<script>", out)
        self.assertNotIn("<b>", out)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; Example", out)
        d["items"] = [copy.deepcopy(self.valid["items"][0]) for _ in range(7)]
        self.assertEqual(self.today(d, "en").count("<li>"), 5)

    def test_today_incomplete(self):
        d = copy.deepcopy(self.valid)
        d.update(status="incomplete", not_checked=["Example source"])
        d["checked"].append({"name": "Internal", "url": "https://github.com/qtorb/rosmarops-vigil/tree/master/docs/observatorio", "latest_seen": "", "latest_date": None})
        out = self.today(d, "ca")
        self.assertTrue(out.startswith('<p class="note">15 de gener de 2026 · 2 fonts revisades</p>\n'
                                       "<p class=\"note\">La revisió d&#039;avui és incompleta: al dia a dia veus què no s&#039;ha pogut revisar.</p>\n"), out)
        d["items"] = []
        out = self.today(d, "es")
        self.assertIn('<p class="note">La revisión de hoy está incompleta: en el día a día ves qué no se pudo revisar.</p>', out)
        self.assertIn('<p class="empty box">Hoy no hay cambios nuevos en las fuentes.</p>', out)

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

    def test_incomplete_without_not_checked_rejected(self):
        d = copy.deepcopy(self.valid)
        d.update(date="2026-01-20", status="incomplete", items=[], summary_ref="docs/observatorio/2026-01-20.md")
        self.assertEqual(self.store_day(d), "not stored")
        st, _, _ = self.get("/observatory/daily/2026-01-20/")
        self.assertEqual(st, 404)
        d["not_checked"] = []
        self.assertEqual(self.store_day(d), "not stored")

    def test_up_to_fifty_sources(self):  # GTM-98: 42 sources F1-F43 (no F30); the cap is 50
        d = copy.deepcopy(self.valid)
        d.update(date="2026-01-09", status="incomplete", summary_ref="docs/observatorio/2026-01-09.md",
                 checked=[dict(d["checked"][0], name=f"Source {i}") for i in range(42)], not_checked=["F43 Comet"])
        self.assertEqual(self.store_day(d), "stored")
        self.rejected(lambda x: x.update(checked=[x["checked"][0]] * 51))

    # ---- incomplete days are published too (GTM-48). Dates before 2026-01-15, so the index and feed tests keep their order.

    def incomplete_day(self, date, items, checked, not_checked):
        d = copy.deepcopy(self.valid)
        d.update(date=date, status="incomplete", summary_ref=f"docs/observatorio/{date}.md", not_checked=not_checked)
        d["items"] = d["items"][:items]
        d["checked"] = d["checked"][:checked]
        self.assertEqual(self.store_day(d), "stored")
        return d

    def test_incomplete_with_items(self):
        d = self.incomplete_day("2026-01-10", 1, 2, ["F3 OpenAI Codex"])
        st, _, body = self.get("/observatory/daily/2026-01-10/")
        self.assertEqual(st, 200)
        self.assertIn('<ol class="changes box">', body)
        self.assertIn(d["items"][0]["text"]["en"].replace("'", "&#039;"), body)
        self.assertIn('<p class="empty box">Checked today: 2 of 3 sources. Not checked: F3 OpenAI Codex.</p>', body)
        self.assertNotIn("No security changes found", body)

    def test_incomplete_without_items(self):
        self.incomplete_day("2026-01-11", 0, 2, ["F3 OpenAI Codex", "F15 NVD"])
        st, _, body = self.get("/es/observatorio/diario/2026-01-11/")
        self.assertEqual(st, 200)
        self.assertNotIn('<ol class="changes box">', body)
        self.assertIn('<p class="empty box">No hemos encontrado cambios en las 2 fuentes revisadas hoy. Sin revisar: F3 OpenAI Codex, F15 NVD.</p>', body)
        st, _, body = self.get("/es/observatorio/diario/")
        self.assertIn("No hemos encontrado cambios en las 2 fuentes revisadas hoy. Sin revisar: F3 OpenAI Codex, F15 NVD.", body)

    def test_incomplete_nothing_checked(self):
        self.incomplete_day("2026-01-12", 0, 0, ["F1 Claude Code"])
        st, _, body = self.get("/ca/observatori/diari/2026-01-12/")
        self.assertEqual(st, 200)
        self.assertIn('<p class="empty box">Avui la revisió no ha pogut comprovar cap font.</p>', body)
        st, _, body = self.get("/ca/observatori/diari/feed.xml")
        descs = [i.findtext("description") for i in ET.fromstring(body).findall("channel/item")]
        self.assertIn("Avui la revisió no ha pogut comprovar cap font.", descs)

    # GTM-74: an entry pointing at the internal repository is not a source: none_checked, and no link to it.
    def test_internal_summary_is_not_a_source(self):
        d = copy.deepcopy(self.valid)
        d.update(date="2026-01-13", status="incomplete", items=[], summary_ref="docs/observatorio/2026-01-13.md",
                 not_checked=["Claude Code", "NVD"])
        d["checked"] = [{"name": "Resumen interno del Observatorio",
                         "url": "https://github.com/qtorb/rosmarops-vigil/tree/master/docs/observatorio",
                         "latest_seen": "", "latest_date": None}]
        self.assertEqual(self.store_day(d), "stored")
        for path, sentence in (
            ("/observatory/daily/2026-01-13/", "The review could not check any source today."),
            ("/es/observatorio/diario/2026-01-13/", "Hoy la revisión no ha podido comprobar ninguna fuente."),
            ("/ca/observatori/diari/2026-01-13/", "Avui la revisió no ha pogut comprovar cap font."),
        ):
            st, _, body = self.get(path)
            self.assertEqual(st, 200)
            self.assertIn(f'<p class="empty box">{sentence}</p>', body)
            self.assertNotIn("rosmarops-vigil", body)
            self.assertNotIn("Resumen interno", body)
        st, _, body = self.get("/es/observatorio/diario/feed.xml")
        self.assertNotIn("rosmarops-vigil", body)


if __name__ == "__main__":
    unittest.main()


AGENTS = ROOT / "observatory" / "data" / "agents"
FIXTURE = ROOT / "observatory" / "tests" / "fixture" / "example-agent.json"
SITE = ROOT / "site"


def norm(h):
    """Static HTML (build.py) and the plugin escape an apostrophe differently; the hook attribute only exists in the static page."""
    return h.replace(" data-live-target", "").replace("&#x27;", "&#039;")


class Agents(unittest.TestCase):
    """GTM-89: the security changes on the Observatory, served by the plugin from the agent files."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Path(cls.tmp.name) / "store.json"
        cls.env = dict(os.environ, DAILY_STORE=str(cls.store))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cli(self, *args, env=None):
        return subprocess.run(["php", str(TESTS / "daily-cli.php"), *map(str, args)], env=env or self.env,
                              capture_output=True, text=True, check=True).stdout

    def route(self, path):
        status, _, body = self.cli("route", path).partition("\n")
        return status, body

    def store_all(self):
        for f in sorted(AGENTS.glob("*.json")):
            self.assertEqual(self.cli("store-agent", f, f.stem).strip(), "stored", f.name)

    def test_1_incomplete_store_keeps_static(self):
        self.assertEqual(self.route("/es/observatorio/diario/changes.html")[0], "404")
        f = next(AGENTS.glob("*.json"))
        self.cli("store-agent", f, f.stem)
        self.assertEqual(self.route("/es/observatorio/diario/last-change.html")[0], "404")

    def test_2_live_matches_static(self):
        self.store_all()
        for lang, prefix, index in [("en", "/observatory/daily/", "observatory"), ("es", "/es/observatorio/diario/", "es/observatorio"),
                                    ("ca", "/ca/observatori/diari/", "ca/observatori")]:
            static = (SITE / index / "index.html").read_text(encoding="utf-8")
            status, body = self.route(prefix + "changes.html")
            self.assertEqual(status, "200")
            start = static.index('<ol class="changes box" data-live-target>')
            self.assertEqual(body, norm(static[start:static.index("</ol>", start) + 5]), lang)
            status, body = self.route(prefix + "last-change.html")
            self.assertEqual(status, "200")
            cells = re.findall(r'data-last="([a-z0-9-]+)">(.*?)</td>', static)
            self.assertGreater(len(cells), 10)
            for aid, cell in cells:
                self.assertIn(f'<span data-agent="{aid}">{norm(cell)}</span>', body, (lang, aid))
            for page in (SITE / index).glob("*/index.html"):
                aid = page.parent.name
                if aid in ("ai-agent-map", "mapa-agentes-ia", "mapa-agents-ia"):  # GTM-138: the map page, not an agent page
                    continue
                st = page.read_text(encoding="utf-8")
                status, body = self.route(f"{prefix}history-{aid}.html")
                self.assertEqual(status, "200", aid)
                m = re.search(r'(<ol class="changes box" data-live-target>.*?</ol>|<p class="empty box" data-live-target>.*?</p>)', st, re.S)
                self.assertEqual(body, norm(m.group(1)), (lang, aid))
        self.assertEqual(self.route("/es/observatorio/diario/history-not-an-agent.html")[0], "404")

    def test_3_last_check_line(self):
        """GTM-90: «Checked every day. Last check: {date}.» above the list, from the newest stored daily; absent without one."""
        self.store_all()
        status, body = self.route("/observatory/daily/changes.html")
        self.assertEqual(status, "200")
        self.assertNotIn("last-check", body)
        valid = json.loads(VALID.read_text(encoding="utf-8"))
        newer = copy.deepcopy(valid)
        newer.update(date="2026-11-05", summary_ref="docs/observatorio/2026-11-05.md")
        for d in (newer, valid):  # stored out of order: the newest date wins, not the last stored
            f = Path(self.tmp.name) / "day.json"
            f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(self.cli("store", f, d["date"]).strip(), "stored")
        style = 'style="margin:0 0 12px;font-size:14px;color:var(--muted)"'
        for prefix, line in [("/observatory/daily/", "Checked every day. Last check: 5 November 2026."),
                             ("/es/observatorio/diario/", "Revisado cada día. Última revisión: 5 de noviembre de 2026."),
                             ("/ca/observatori/diari/", "Revisat cada dia. Última revisió: 5 de novembre de 2026.")]:
            status, body = self.route(prefix + "changes.html")
            self.assertEqual(status, "200")
            self.assertTrue(body.startswith(f'<p class="meta last-check" {style}>{line}</p><ol class="changes box">'), body[:200])

    def test_writer_entry(self):
        for lang, line in [("en", "Collected automatically on 4 November 2026 from the official changelog."),
                           ("es", "Recogido automáticamente el 4 de noviembre de 2026 del registro de cambios oficial."),
                           ("ca", "Recollit automàticament el 4 de novembre de 2026 del registre de canvis oficial.")]:
            out = self.cli("history", FIXTURE, lang)
            self.assertIn(f'<p class="meta">{line} <a href="https://example.com/changelog#1.3.0" rel="noopener">', out, lang)
        self.assertIn("Comprobado el 28 de octubre de 2026 con el registro de cambios oficial.", self.cli("history", FIXTURE, "es"))
        d = json.loads(FIXTURE.read_text(encoding="utf-8"))
        d["changes"][-1]["verified"]["how"] = "official_doc"
        f = Path(self.tmp.name) / "doc.json"
        f.write_text(json.dumps(d), encoding="utf-8")
        self.assertIn("Recogido automáticamente el 4 de noviembre de 2026 de la documentación oficial.", self.cli("history", f, "es"))

    def test_writer_entry_escaped(self):
        d = json.loads(FIXTURE.read_text(encoding="utf-8"))
        d["changes"][-1]["after"]["es"] = '<img src=x onerror="alert(1)"> desde 1.3.0'
        f = Path(self.tmp.name) / "xss.json"
        f.write_text(json.dumps(d), encoding="utf-8")
        out = self.cli("history", f, "es")
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt; desde 1.3.0", out)

    def test_invalid_agent_file(self):
        base = json.loads(FIXTURE.read_text(encoding="utf-8"))
        f = Path(self.tmp.name) / "bad.json"
        for mutate in (lambda c: c["verified"].update(by="robot"), lambda c: c["source"].update(url="http://example.com/x"),
                       lambda c: c.update(extra=1), lambda c: c.update(category="other"), lambda c: c["after"].pop("en"),
                       lambda c: c.update(id="chg-UPPER")):
            d = copy.deepcopy(base)
            mutate(d["changes"][-1])
            f.write_text(json.dumps(d), encoding="utf-8")
            self.assertEqual(self.cli("history", f, "en"), "invalid")
        # An invalid file never replaces the stored copy.
        env = dict(os.environ, DAILY_STORE=str(Path(self.tmp.name) / "s2.json"))
        self.assertEqual(self.cli("store-agent", FIXTURE, "example-agent", env=env).strip(), "stored")
        self.assertEqual(self.cli("store-agent", f, "example-agent", env=env).strip(), "not stored")
