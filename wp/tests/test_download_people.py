"""GTM-200: people who download, not robot clicks. Against a real MySQL/MariaDB, like test_visits.py.

A counted click adds one to `people` in its row only when the visitor's fingerprint of the day (GTM-125) already has
a visit counted today and has no click counted today.

    DB_USER=wp DB_PASS=wp DB_NAME=wptest python3 -m unittest wp/tests/test_download_people.py
Skipped when no database is reachable.
"""

import json
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_visits import ORIGIN, PREFIX, UA, Server, db_available, mysql  # noqa: E402

DOWNLOADS = PREFIX + "rosmarops_downloads"
VISITS = PREFIX + "rosmarops_visits"
VPRINTS = PREFIX + "rosmarops_visits_prints"
DPRINTS = PREFIX + "rosmarops_download_prints"
PEOPLE = PREFIX + "rosmarops_people"
HOURLY = PREFIX + "rosmarops_hourly"
OPTIONS = PREFIX + "stub_sitemeta"
UA2 = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class DownloadPeople(unittest.TestCase):
    def setUp(self):
        self.drop()
        self.tmp = tempfile.mkdtemp()
        (Path(self.tmp) / "index.html").write_text("<html></html>")
        self.srv = None
        self.day("2026-11-23")

    def tearDown(self):
        self.srv.stop()
        shutil.rmtree(self.tmp)
        self.drop()

    def drop(self):
        mysql(f"DROP TABLE IF EXISTS {DOWNLOADS}, {VISITS}, {VPRINTS}, {DPRINTS}, {PEOPLE}, {HOURLY}, {OPTIONS}")

    def day(self, d):
        if self.srv:
            self.srv.stop()
        self.srv = Server(True, self.tmp, today=d)

    def visit(self, ua=UA):
        h = {"Origin": ORIGIN, "User-Agent": ua, "Content-Type": "application/json"}
        self.srv.req("/wp-json/rosmarops/v1/visits", "POST", json.dumps({"p": "/", "r": ""}), h)

    def click(self, ua=UA, headers=None, path="/download?from=home&os=windows"):
        h = {"User-Agent": ua}
        h.update(headers or {})
        r = urllib.request.Request(f"http://127.0.0.1:{self.srv.port}{path}", headers=h)
        try:
            OPENER.open(r, timeout=5)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 302)  # every click is redirected, counted or not
            return e.headers["Location"]
        self.fail("no redirect")

    def rows(self):
        if not mysql(f"SHOW TABLES LIKE '{DOWNLOADS}'").strip():
            return []
        return mysql(f"SELECT day, src, lang, os, count, people FROM {DOWNLOADS} ORDER BY day, src, lang, os").splitlines()

    def count(self, t):
        if not mysql(f"SHOW TABLES LIKE '{t}'").strip():
            return 0
        return int(mysql(f"SELECT COUNT(*) FROM {t}").strip())

    def test_click_after_a_visit_today_is_one_person(self):
        self.visit()
        self.click()
        self.assertEqual(self.rows(), ["2026-11-23\thome\ten\twindows\t1\t1"])
        self.assertEqual(self.count(DPRINTS), 1)

    def test_second_click_of_the_same_fingerprint_adds_no_person(self):
        self.visit()
        self.click()
        self.click()
        self.click(path="/es/descargar?from=faq&os=mac-arm")  # another row, same person: still one person
        self.assertEqual(self.rows(), ["2026-11-23\tfaq\tes\tmac-arm\t1\t0", "2026-11-23\thome\ten\twindows\t2\t1"])

    def test_click_without_a_visit_counts_the_click_not_the_person(self):
        self.click()
        self.assertEqual(self.rows(), ["2026-11-23\thome\ten\twindows\t1\t0"])
        self.assertEqual(self.count(DPRINTS), 0)
        self.visit(ua=UA2)  # someone else's visit does not make this click a person
        self.click()
        self.assertEqual(self.rows(), ["2026-11-23\thome\ten\twindows\t2\t0"])

    def test_robot_and_prefetch_add_nothing(self):
        self.visit()
        loc = self.click(ua="Googlebot/2.1 (+http://www.google.com/bot.html)")
        self.assertIn("rosmarops.exe", loc)
        for hdr in ({"Sec-Purpose": "prefetch"}, {"Sec-Purpose": "prefetch;prerender"}, {"Purpose": "prefetch"},
                    {"X-Moz": "prefetch"}):
            self.assertIn("rosmarops.exe", self.click(headers=hdr))  # the same redirect
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.count(DPRINTS), 0)
        hourly = mysql(f"SELECT COALESCE(SUM(count), 0) FROM {HOURLY} WHERE kind = 'download'").strip()
        self.assertEqual(hourly, "0")
        self.click()  # and a person's click counts, so the five above were filtered, not broken
        self.assertEqual(self.rows(), ["2026-11-23\thome\ten\twindows\t1\t1"])

    def test_new_day_empties_the_download_fingerprints(self):
        self.visit()
        self.click()
        self.assertEqual(self.count(DPRINTS), 1)
        self.day("2026-11-24")
        self.visit(ua=UA2)  # the first counted visit of the new day rotates the key
        self.assertEqual(self.count(DPRINTS), 0)
        self.visit()
        self.click()  # the same person as yesterday is one person again today
        self.assertEqual(self.rows(), ["2026-11-23\thome\ten\twindows\t1\t1", "2026-11-24\thome\ten\twindows\t1\t1"])

    def test_endpoint_has_people_and_keeps_the_rest(self):
        self.visit()
        self.click()
        self.click(ua=UA2)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.srv.port}/wp-json/rosmarops/v1/downloads", timeout=5) as res:
            d = json.loads(res.read().decode())
        self.assertEqual(set(d), {"generated_at", "rows"})
        self.assertEqual(d["rows"], [{"day": "2026-11-23", "from": "home", "lang": "en", "os": "windows", "count": 2,
                                      "people": 1}])

    def test_ip_and_browser_appear_nowhere(self):
        self.visit()
        self.click()
        self.assertEqual([c.split("\t")[0] for c in mysql(f"SHOW COLUMNS FROM {DPRINTS}").splitlines()], ["h"])
        dump = "".join(mysql(f"SELECT * FROM {t}") for t in (DOWNLOADS, DPRINTS))
        for leak in ["127.0.0.1", "Mozilla", "Chrome", "Windows NT"]:
            self.assertNotIn(leak, dump, leak)


if __name__ == "__main__":
    unittest.main()
