"""Tests for wp/mu-plugins/rosmarops-downloads.php against a real MySQL/MariaDB (wp-stub.php + php -S).

Run from the repository root, with a database the user can create tables in:
    DB_USER=wp DB_PASS=wp DB_NAME=wptest python3 -m unittest wp/tests/test_downloads.py
Skipped when no database is reachable.
"""

import json
import os
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "wp" / "tests"
PREFIX = "dltest_"
TABLE = PREFIX + "rosmarops_downloads"
LATEST = "https://github.com/qtorb/rosmarops/releases/latest"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


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


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class Downloads(unittest.TestCase):
    def setUp(self):
        # A table from before the os column, with counts that must survive the migration.
        mysql(f"DROP TABLE IF EXISTS {TABLE}")
        mysql(f"CREATE TABLE {TABLE} (day DATE NOT NULL, src VARCHAR(40) NOT NULL, lang CHAR(2) NOT NULL,"
              f" count INT UNSIGNED NOT NULL DEFAULT 0, PRIMARY KEY (day, src, lang))")
        mysql(f"INSERT INTO {TABLE} VALUES (UTC_DATE(), 'home', 'en', 7), (UTC_DATE(), 'faq', 'es', 3)")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        env = dict(os.environ, DB_PREFIX=PREFIX)
        self.srv = subprocess.Popen(["php", "-S", f"127.0.0.1:{self.port}", str(TESTS / "router.php")],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)

    def tearDown(self):
        self.srv.terminate()
        self.srv.wait()
        mysql(f"DROP TABLE IF EXISTS {TABLE}")

    def get(self, path, method="GET"):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        try:
            r = OPENER.open(req, timeout=5)
            return r.status, dict(r.headers), r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode()

    def rows(self):
        return mysql(f"SELECT src, lang, os, count FROM {TABLE} ORDER BY src, lang, os").splitlines()

    def test_targets(self):
        cases = {
            "/download?from=home&os=windows": LATEST + "/download/rosmarops.exe",
            "/es/descargar?from=macos-page&os=mac-arm": LATEST + "/download/rosmarops-macos-apple-silicon",
            "/ca/descarregar?from=macos-page&os=mac-intel": LATEST + "/download/rosmarops-macos-intel",
            "/download?from=home": LATEST,
            "/download?from=home&os=linux": LATEST,
            "/download/?from=blog-v040": LATEST,
        }
        for path, target in cases.items():
            st, h, _ = self.get(path)
            self.assertEqual(st, 302, path)
            self.assertEqual(h["Location"], target, path)
            self.assertEqual(h["Cache-Control"], "no-store", path)

    def test_migration_keeps_counts_and_adds_os(self):
        self.get("/download?from=home&os=windows")
        self.get("/download?from=home")
        self.get("/download?from=macos-page&os=mac-arm")
        self.get("/download?from=nowhere&os=bogus")
        self.assertEqual(self.rows(), [
            "faq\tes\t\t3",
            "home\ten\t\t8",
            "home\ten\twindows\t1",
            "macos-page\ten\tmac-arm\t1",
            "other\ten\t\t1",
        ])
        key = mysql(f"SHOW KEYS FROM {TABLE} WHERE Key_name = 'PRIMARY'").splitlines()
        self.assertEqual([k.split("\t")[4] for k in key], ["day", "src", "lang", "os"])

    def test_fresh_table(self):
        mysql(f"DROP TABLE {TABLE}")
        self.get("/ca/descarregar?from=home&os=windows")
        self.assertEqual(self.rows(), ["home\tca\twindows\t1"])

    def test_head_not_counted(self):
        st, h, _ = self.get("/download?from=home&os=windows", method="HEAD")
        self.assertEqual(st, 302)
        self.assertEqual(h["Location"], LATEST + "/download/rosmarops.exe")
        # Not counted, so the table is not touched either (still without the os column).
        self.assertEqual(mysql(f"SELECT SUM(count) FROM {TABLE}").strip(), "10")

    def test_endpoint_migrates_on_read_and_adds_os(self):
        st, _, body = self.get("/wp-json/rosmarops/v1/downloads")
        self.assertEqual(st, 200)
        d = json.loads(body)
        self.assertEqual(set(d), {"generated_at", "rows"})
        self.assertEqual(sorted((r["from"], r["lang"], r["os"], r["count"]) for r in d["rows"]),
                         [("faq", "es", "", 3), ("home", "en", "", 7)])
        self.assertEqual(set(d["rows"][0]), {"day", "from", "lang", "os", "count"})


if __name__ == "__main__":
    unittest.main()
