"""GTM-186: hourly totals of visits and download clicks in wp/mu-plugins/rosmarops-downloads.php, against a real
MySQL/MariaDB (wp-stub.php + php -S), and the public texts that describe them.

Run from the repository root:
    DB_USER=wp DB_PASS=wp DB_NAME=wptest python3 -m unittest wp/tests/test_hourly.py
The database tests are skipped when no database is reachable; the text tests always run.
"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "wp" / "tests"
PREFIX = "hrtest_"
HOURLY = PREFIX + "rosmarops_hourly"
ORIGIN = "https://rosmarops.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
NOW = 1795428800  # 2026-11-23 10:13:20 UTC
HOUR = "2026-11-23 10:00:00"

# Signed with GTM-186 (vigil docs/briefs/GTM-186.md §2), literal.
TEXTS = {
    "site/es/privacidad/index.html": "Totales por hora. Nuestro servidor también suma uno al total de la hora en curso: uno de visitas y otro de clics en descargar, sin página, idioma, procedencia ni sistema. Los usamos para seguir el día mientras pasa y los borramos a las 48 horas. Como los otros recuentos, son públicos.",
    "site/privacy/index.html": "Hourly totals. Our server also adds one to a total for the current hour: one for visits and one for download clicks, with no page, language, origin or system. We use them to follow the day as it goes and delete them after 48 hours. Like the other counts, they are public.",
    "site/ca/privadesa/index.html": "Totals per hora. El nostre servidor també suma u al total de l'hora en curs: un de visites i un altre de clics de descàrrega, sense pàgina, idioma, procedència ni sistema. Els fem servir per seguir el dia mentre passa i els esborrem al cap de 48 hores. Com els altres recomptes, són públics.",
}
AFTER = {"site/es/privacidad/index.html": "<p>Contador de visitas.", "site/privacy/index.html": "<p>Visit counter.",
         "site/ca/privadesa/index.html": "<p>Comptador de visites."}
VISITS_JS = ("The server keeps only a count per day, page, language and kind of referrer, and an hourly total with none of "
             "these, deleted after 48 hours.")


def mysql(sql):
    args = ["mysql", "-h", "127.0.0.1", "-u", os.environ.get("DB_USER", "root"), "-N", "-B",
            os.environ.get("DB_NAME", "wptest"), "-e", sql]
    if os.environ.get("DB_PASS"):
        args.insert(5, "-p" + os.environ["DB_PASS"])
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout


def db_available():
    try:
        mysql("SELECT 1")
        return True
    except Exception:
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


class Texts(unittest.TestCase):
    def test_paragraph_right_after_the_visit_counter(self):
        for f, text in TEXTS.items():
            s = (ROOT / f).read_text(encoding="utf-8")
            self.assertEqual(s.count(text), 1, f)
            i = s.index(AFTER[f])
            self.assertTrue(s[s.index("</p>", i) + 4:].lstrip().startswith(f"<p>{text}</p>"), f)

    def test_visits_js(self):
        self.assertIn(VISITS_JS, (ROOT / "site" / "assets" / "visits" / "visits.js").read_text(encoding="utf-8"))


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class Hourly(unittest.TestCase):
    def setUp(self):
        for t in ("rosmarops_hourly", "rosmarops_visits", "rosmarops_downloads", "rosmarops_visits_prints",
                  "rosmarops_people", "stub_sitemeta"):
            mysql(f"DROP TABLE IF EXISTS {PREFIX}{t}")
        self.tmp = tempfile.mkdtemp()
        (Path(self.tmp) / "methodology").mkdir()
        (Path(self.tmp) / "methodology" / "index.html").write_text("<html></html>")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        env = dict(os.environ, DB_PREFIX=PREFIX, VISITS_ON="1", VISITS_DOCROOT=self.tmp, HOURLY_NOW=str(NOW),
                   VISITS_TODAY="2026-11-23")
        self.proc = subprocess.Popen(["php", "-S", f"127.0.0.1:{self.port}", str(TESTS / "router.php")],
                                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait()
        shutil.rmtree(self.tmp)
        for t in ("rosmarops_hourly", "rosmarops_visits", "rosmarops_downloads", "rosmarops_visits_prints",
                  "rosmarops_people", "stub_sitemeta"):
            mysql(f"DROP TABLE IF EXISTS {PREFIX}{t}")

    def req(self, path, method="GET", body=None, headers=None):
        h = {"User-Agent": UA}
        h.update(headers or {})
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body.encode() if body else None,
                                   method=method, headers=h)
        try:
            with OPENER.open(r, timeout=5) as res:
                return res.status, dict(res.headers), res.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode()

    def visit(self, ua=UA):
        return self.req("/wp-json/rosmarops/v1/visits", "POST", json.dumps({"p": "/methodology/", "r": ""}),
                        {"Origin": ORIGIN, "Content-Type": "application/json", "User-Agent": ua})

    def hourly(self):
        return mysql(f"SELECT hour, kind, count FROM {HOURLY} ORDER BY hour, kind").splitlines()

    def test_each_visit_and_click_adds_to_its_hour(self):
        self.visit()
        self.visit()
        st, h, _ = self.req("/download?from=home&os=windows")
        self.assertEqual(st, 302)
        self.req("/es/descargar?from=faq")
        self.assertEqual(self.hourly(), [f"{HOUR}\tdownload\t2", f"{HOUR}\tvisit\t2"])
        # what the counters do not count does not add either: a robot, the team
        self.visit(ua="Googlebot/2.1")
        self.req("/download?from=home", headers={"Cookie": "rosmarops_internal=1"})
        self.req("/download?from=home", method="HEAD")
        self.assertEqual(self.hourly(), [f"{HOUR}\tdownload\t2", f"{HOUR}\tvisit\t2"])
        # and the tables of today keep their counts
        self.assertEqual(mysql(f"SELECT SUM(count) FROM {PREFIX}rosmarops_visits").strip(), "2")
        self.assertEqual(mysql(f"SELECT SUM(count) FROM {PREFIX}rosmarops_downloads").strip(), "2")

    def test_only_hour_kind_and_count(self):
        self.visit()
        cols = [c.split("\t")[0] for c in mysql(f"SHOW COLUMNS FROM {HOURLY}").splitlines()]
        self.assertEqual(cols, ["hour", "kind", "count"])
        self.assertIn("PRIMARY KEY (`hour`,`kind`)", mysql(f"SHOW CREATE TABLE {HOURLY}").replace("\\n", "\n"))
        # every row is an hour, a kind and a number: nothing of the page, the language, the referrer or the person
        for line in mysql(f"SELECT * FROM {HOURLY}").splitlines():
            self.assertRegex(line, r"^\d{4}-\d\d-\d\d \d\d:00:00\t(visit|download)\t\d+$")

    def test_older_than_48_hours_neither_shown_nor_kept(self):
        self.visit()  # creates the table
        mysql(f"INSERT INTO {HOURLY} VALUES ('2026-11-21 11:00:00', 'visit', 5), ('2026-11-21 10:00:00', 'visit', 7), "
              f"('2026-11-20 03:00:00', 'download', 9)")
        st, h, body = self.req("/wp-json/rosmarops/v1/hours")
        d = json.loads(body)
        self.assertEqual(d[0], {"hour": "2026-11-21T11:00:00Z", "visits": 5, "downloads": 0})  # 47 hours back: kept
        self.assertNotIn("2026-11-21T10:00:00Z", body)
        self.assertEqual(self.hourly(), ["2026-11-21 11:00:00\tvisit\t5", f"{HOUR}\tvisit\t1"])  # deleted on read
        mysql(f"INSERT INTO {HOURLY} VALUES ('2026-11-01 00:00:00', 'visit', 3)")
        self.visit()  # and on write
        self.assertNotIn("2026-11-01", "".join(self.hourly()))

    def test_route_format_and_cache(self):
        self.visit()
        self.req("/download?from=home")
        st, h, body = self.req("/wp-json/rosmarops/v1/hours")
        self.assertEqual(st, 200)
        self.assertEqual(h.get("Cache-Control"), "max-age=60")
        d = json.loads(body)
        self.assertIsInstance(d, list)
        self.assertEqual(len(d), 48)
        self.assertEqual(d[-1], {"hour": "2026-11-23T10:00:00Z", "visits": 1, "downloads": 1})
        self.assertEqual(d[0]["hour"], "2026-11-21T11:00:00Z")
        self.assertTrue(all(set(r) == {"hour", "visits", "downloads"} for r in d))
        self.assertEqual(sum(r["visits"] + r["downloads"] for r in d), 2)
        # the two routes of today keep their cache and shape
        st, h, body = self.req("/wp-json/rosmarops/v1/visits")
        self.assertEqual((h.get("Cache-Control"), sorted(json.loads(body))), ("public, max-age=3600", ["generated_at", "people", "rows"]))
        st, h, body = self.req("/wp-json/rosmarops/v1/downloads")
        self.assertEqual((h.get("Cache-Control"), sorted(json.loads(body))), ("public, max-age=3600", ["generated_at", "rows"]))
        self.assertEqual(self.req("/wp-json/rosmarops/v1/hours", "POST")[0], 404)  # read only

    def test_empty_before_any_count(self):
        st, h, body = self.req("/wp-json/rosmarops/v1/hours")
        d = json.loads(body)
        self.assertEqual((st, len(d), sum(r["visits"] + r["downloads"] for r in d)), (200, 48, 0))


if __name__ == "__main__":
    unittest.main()
