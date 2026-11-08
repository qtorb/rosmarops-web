"""GTM-111: the visit counter in wp/mu-plugins/rosmarops-downloads.php, against a real MySQL/MariaDB (wp-stub.php +
php -S), and its script site/assets/visits/visits.js (node). One test per filter, and checks that nothing personal is
stored or set.

Run from the repository root:
    DB_USER=wp DB_PASS=wp DB_NAME=wptest python3 -m unittest wp/tests/test_visits.py
The database tests are skipped when no database is reachable; the script and switch tests always run.
"""

import json
import os
import re
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
PLUGIN = ROOT / "wp" / "mu-plugins" / "rosmarops-downloads.php"
SCRIPT = ROOT / "site" / "assets" / "visits" / "visits.js"
PREFIX = "vtest_"
TABLE = PREFIX + "rosmarops_visits"
ORIGIN = "https://rosmarops.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


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


class Server:
    def __init__(self, on, docroot, posts=""):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        env = dict(os.environ, DB_PREFIX=PREFIX, VISITS_DOCROOT=str(docroot), VISITS_POSTS=posts)
        if on:
            env["VISITS_ON"] = "1"
        self.proc = subprocess.Popen(["php", "-S", f"127.0.0.1:{self.port}", str(TESTS / "router.php")],
                                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)

    def stop(self):
        self.proc.terminate()
        self.proc.wait()

    def req(self, path, method="GET", body=None, headers=None):
        data = body.encode() if isinstance(body, str) else body
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(r, timeout=5) as res:
                return res.status, dict(res.headers), res.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read().decode()


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class Visits(unittest.TestCase):
    def setUp(self):
        mysql(f"DROP TABLE IF EXISTS {TABLE}")
        self.tmp = tempfile.mkdtemp()
        for p in ["", "methodology", "es/metodologia", "ca/observatori/cursor"]:
            d = Path(self.tmp, p)
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text("<html></html>")
        self.srv = Server(True, self.tmp, posts=f"{ORIGIN}/blog/my-machine-scored-18-of-100/ {ORIGIN}/es/privacidad/")

    def tearDown(self):
        self.srv.stop()
        shutil.rmtree(self.tmp)
        mysql(f"DROP TABLE IF EXISTS {TABLE}")

    def visit(self, page, ref="", headers=None, path="/wp-json/rosmarops/v1/visits", body=None):
        h = {"Origin": ORIGIN, "User-Agent": UA, "Content-Type": "application/json"}
        h.update(headers or {})
        h = {k: v for k, v in h.items() if v is not None}
        return self.srv.req(path, "POST", body if body is not None else json.dumps({"p": page, "r": ref}), h)

    def rows(self):
        out = mysql(f"SELECT page, lang, ref, count FROM {TABLE} ORDER BY page, lang, ref") if self.has_table() else ""
        return out.splitlines()

    def has_table(self):
        return mysql(f"SHOW TABLES LIKE '{TABLE}'").strip() == TABLE

    def test_counts_page_language_and_referrer(self):
        st, h, body = self.visit("/methodology/", "www.google.com")
        self.assertEqual((st, body), (204, ""))
        self.assertEqual(h.get("Cache-Control"), "no-store")
        self.visit("/es/metodologia", "duckduckgo.com", path="/es/wp-json/rosmarops/v1/visits")  # no trailing slash
        self.visit("/ca/observatori/cursor/", "rosmarops.com", path="/ca/wp-json/rosmarops/v1/visits")
        self.visit("/blog/my-machine-scored-18-of-100/", "news.ycombinator.com")
        self.visit("/es/privacidad/", "")
        self.visit("/", "www.google.com")
        self.visit("/methodology/", "www.google.com")
        self.visit("/es/observatorio/diario/2026-11-07/", "x.com")
        self.assertEqual(self.rows(), [
            "/\ten\tgoogle\t1",
            "/blog/my-machine-scored-18-of-100/\ten\thn\t1",
            "/ca/observatori/cursor/\tca\tinternal\t1",
            "/es/metodologia/\tes\tduckduckgo\t1",
            "/es/observatorio/diario/2026-11-07/\tes\tx\t1",
            "/es/privacidad/\tes\tdirect\t1",
            "/methodology/\ten\tgoogle\t2",
        ])

    def test_pages_outside_the_closed_list_are_other(self):
        for p in ["/no-such-page/", "/Methodology/", "/methodology/../wp-config.php", "/methodology/?q=1",
                  "/a//b/", "x", "/" + "a" * 200 + "/", 12, None]:
            self.visit(p, "")
        self.assertEqual(self.rows(), ["other\ten\tdirect\t9"])

    def test_blog_listings_count_as_the_blog_home_of_their_language(self):
        # GTM-118: pagination, categories, tags, author, dates and search of the blog (url_to_postid = 0).
        cases = {
            "/blog/page/2/": "/blog/", "/blog/category/field-notes/": "/blog/", "/blog/category/a/b/page/3/": "/blog/",
            "/blog/tag/claude-code/": "/blog/", "/blog/author/albert/": "/blog/", "/blog/author/albert/page/2/": "/blog/",
            "/blog/2026/": "/blog/", "/blog/2026/11/": "/blog/", "/blog/2026/11/08/": "/blog/", "/blog/2026/11/page/2/": "/blog/",
            "/blog/search/agentes/": "/blog/", "/search/agents/": "/blog/",
            "/es/blog/page/2": "/es/blog/", "/es/blog/category/nota-de-exposicion/": "/es/blog/", "/es/blog/tag/cursor/": "/es/blog/",
            "/es/blog/author/albert/": "/es/blog/", "/es/blog/2026/10/": "/es/blog/", "/es/search/claves/": "/es/blog/",
            "/ca/blog/category/nota-dexposicio/": "/ca/blog/", "/ca/blog/tag/credencials/": "/ca/blog/",
            "/ca/blog/author/albert/": "/ca/blog/", "/ca/blog/page/3/": "/ca/blog/",
        }
        for p in cases:
            self.visit(p, "")
        want = {}
        for page in cases.values():
            want[page] = want.get(page, 0) + 1
        got = {line.split("\t")[0]: (line.split("\t")[1], int(line.split("\t")[3])) for line in self.rows()}
        self.assertEqual(got, {"/blog/": ("en", want["/blog/"]), "/es/blog/": ("es", want["/es/blog/"]), "/ca/blog/": ("ca", want["/ca/blog/"])})

    def test_not_a_listing_stays_other(self):
        for p in ["/blog/page/", "/blog/page/x/", "/blog/category/", "/blog/12345/", "/blog/2026/1/", "/es/blog/no-such-post/",
                  "/fr/blog/page/2/", "/blogs/page/2/"]:
            self.visit(p, "")
        self.assertEqual([line.split("\t")[0] for line in self.rows()], ["other"])

    def test_referrer_closed_list(self):
        refs = {"": "direct", "rosmarops.com": "internal", "www.rosmarops.com": "internal", "gemini.google.com": "gemini",
                "www.google.es": "google", "www.google.co.uk": "google", "www.bing.com": "bing", "github.com": "github",
                "lnkd.in": "linkedin", "t.co": "x", "old.reddit.com": "reddit", "chatgpt.com": "chatgpt",
                "www.perplexity.ai": "perplexity", "claude.ai": "claude", "evil.example": "other",
                "google.evil.example": "other", "bad host!": "other", "GITHUB.COM": "github"}
        for r in refs:
            self.visit("/methodology/", r)
        got = {}
        for line in self.rows():
            page, lang, ref, n = line.split("\t")
            got[ref] = int(n)
        want = {}
        for r, k in refs.items():
            want[k] = want.get(k, 0) + 1
        self.assertEqual(got, want)

    def test_wrong_or_missing_origin_not_counted(self):
        for o in [None, "https://evil.example", "http://rosmarops.com", "https://www.rosmarops.com", "null"]:
            st, _, _ = self.visit("/methodology/", "", headers={"Origin": o})
            self.assertEqual(st, 204)  # same answer either way
        self.assertEqual(self.rows(), [])

    def test_prefetch_not_counted(self):
        for h in [{"Sec-Purpose": "prefetch"}, {"Sec-Purpose": "prefetch;prerender"}, {"Purpose": "prefetch"}, {"X-Moz": "prefetch"}]:
            self.visit("/methodology/", "", headers=h)
        self.assertEqual(self.rows(), [])

    def test_bots_not_counted(self):
        for ua in ["", "Googlebot/2.1 (+http://www.google.com/bot.html)", "Mozilla/5.0 (compatible; bingbot/2.0)",
                   "curl/8.5.0", "python-requests/2.32", "Mozilla/5.0 HeadlessChrome/130.0", "Mozilla/5.0 (compatible; ClaudeBot/1.0)",
                   "facebookexternalhit/1.1", "Wget/1.21"]:
            self.visit("/methodology/", "", headers={"User-Agent": ua})
        self.assertEqual(self.rows(), [])

    def test_team_not_counted(self):
        self.visit("/methodology/", "", headers={"Cookie": "wordpress_logged_in_0a1b2c=albert%7C1"})
        self.assertEqual(self.rows(), [])

    def test_bad_bodies_not_counted(self):
        self.visit("/methodology/", body="not json")
        self.visit("/methodology/", body=json.dumps({"p": "/methodology/", "r": "x" * 600}))  # over the size limit
        self.visit("/methodology/", body="[1,2]")
        self.assertEqual(self.rows(), [])

    def test_only_post_counts_and_get_reads(self):
        self.visit("/methodology/", "github.com")
        st, h, body = self.srv.req("/wp-json/rosmarops/v1/visits")
        self.assertEqual(st, 200)
        self.assertEqual(h.get("Cache-Control"), "public, max-age=3600")
        d = json.loads(body)
        self.assertEqual(set(d), {"generated_at", "rows"})
        self.assertEqual([(r["page"], r["lang"], r["ref"], r["count"]) for r in d["rows"]], [("/methodology/", "en", "github", 1)])
        self.assertEqual(set(d["rows"][0]), {"day", "page", "lang", "ref", "count"})
        for m in ["PUT", "DELETE", "PATCH"]:
            self.assertEqual(self.srv.req("/wp-json/rosmarops/v1/visits", m, "{}")[0], 404)
        self.assertEqual(len(self.rows()), 1)

    def test_api_keeps_400_days(self):
        self.visit("/methodology/", "")
        mysql(f"INSERT INTO {TABLE} VALUES (UTC_DATE() - INTERVAL 399 DAY, '/', 'en', 'direct', 4),"
              f" (UTC_DATE() - INTERVAL 400 DAY, '/', 'en', 'direct', 5)")
        d = json.loads(self.srv.req("/wp-json/rosmarops/v1/visits")[2])
        self.assertEqual(sorted(r["count"] for r in d["rows"]), [1, 4])

    def test_nothing_personal_stored_or_set(self):
        st, h, _ = self.visit("/methodology/", "www.google.com")
        self.assertNotIn("Set-Cookie", h)
        cols = [c.split("\t")[0] for c in mysql(f"SHOW COLUMNS FROM {TABLE}").splitlines()]
        self.assertEqual(cols, ["day", "page", "lang", "ref", "count"])
        dump = mysql(f"SELECT * FROM {TABLE}")
        for leak in ["127.0.0.1", "Mozilla", "Chrome", "google.com"]:
            self.assertNotIn(leak, dump)


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class SwitchedOff(unittest.TestCase):
    def test_off_means_no_route_and_no_table(self):
        mysql(f"DROP TABLE IF EXISTS {TABLE}")
        tmp = tempfile.mkdtemp()
        srv = Server(False, tmp)
        try:
            h = {"Origin": ORIGIN, "User-Agent": UA, "Content-Type": "application/json"}
            self.assertEqual(srv.req("/wp-json/rosmarops/v1/visits", "POST", json.dumps({"p": "/", "r": ""}), h)[0], 404)
            self.assertEqual(srv.req("/wp-json/rosmarops/v1/visits")[0], 404)
            self.assertEqual(mysql(f"SHOW TABLES LIKE '{TABLE}'").strip(), "")
        finally:
            srv.stop()
            shutil.rmtree(tmp)


NODE_HARNESS = r"""
const fs = require('fs');
const [src, visible, referrer, path, on] = process.argv.slice(2);
let code = fs.readFileSync(src, 'utf8');
code = code.replace(/var ON = (true|false);/, on === '1' ? 'var ON = true;' : 'var ON = false;');
const calls = []; const listeners = {};
const touched = [];
const doc = { visibilityState: visible, referrer,
  addEventListener: (ev, fn) => { listeners[ev] = fn; } };
Object.defineProperty(doc, 'cookie', { get() { touched.push('cookie'); return ''; }, set() { touched.push('cookie'); } });
const trap = (name) => new Proxy({}, { get() { touched.push(name); return () => null; } });
const win = { fetch: (url, opts) => { calls.push({ url, opts }); return Promise.resolve(); } };
const fn = new Function('window', 'document', 'location', 'fetch', 'localStorage', 'sessionStorage', 'indexedDB', 'URL', code);
fn(win, doc, { pathname: path }, win.fetch, trap('localStorage'), trap('sessionStorage'), trap('indexedDB'), URL);
fn(win, doc, { pathname: path }, win.fetch, trap('localStorage'), trap('sessionStorage'), trap('indexedDB'), URL); // included twice
const before = calls.length;
doc.visibilityState = 'visible';
if (listeners.visibilitychange) listeners.visibilitychange();
if (listeners.visibilitychange) listeners.visibilitychange();
console.log(JSON.stringify({ before, calls, touched }));
"""


class Script(unittest.TestCase):
    def run_js(self, visible, referrer, path, on=True):
        if not shutil.which("node"):
            self.skipTest("node not on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(NODE_HARNESS)
        try:
            p = subprocess.run(["node", f.name, str(SCRIPT), visible, referrer, path, "1" if on else "0"],
                               capture_output=True, text=True, check=True)
        finally:
            os.unlink(f.name)
        return json.loads(p.stdout)

    def test_sends_path_and_referrer_domain_once(self):
        r = self.run_js("visible", "https://www.google.com/search?q=rosmarops&secret=1", "/es/metodologia/")
        self.assertEqual(r["before"], 1)
        self.assertEqual(len(r["calls"]), 1)
        c = r["calls"][0]
        self.assertEqual(c["url"], "/es/wp-json/rosmarops/v1/visits")
        self.assertEqual(c["opts"]["method"], "POST")
        self.assertEqual(json.loads(c["opts"]["body"]), {"p": "/es/metodologia/", "r": "www.google.com"})
        self.assertEqual(r["touched"], [])

    def test_waits_until_visible(self):
        r = self.run_js("hidden", "", "/methodology/")
        self.assertEqual(r["before"], 0)
        self.assertEqual(len(r["calls"]), 1)
        self.assertEqual(r["calls"][0]["url"], "/wp-json/rosmarops/v1/visits")
        self.assertEqual(json.loads(r["calls"][0]["opts"]["body"]), {"p": "/methodology/", "r": ""})

    def test_switched_off_sends_nothing(self):
        r = self.run_js("visible", "https://x.com/", "/", on=False)
        self.assertEqual((r["before"], r["calls"], r["touched"]), (0, [], []))

    def test_no_storage_in_the_source(self):
        src = SCRIPT.read_text(encoding="utf-8").lower()
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        for word in ["cookie", "localstorage", "sessionstorage", "indexeddb", "navigator", "screen", "useragent", "date"]:
            self.assertNotIn(word, code, word)


class Switch(unittest.TestCase):
    def test_script_and_plugin_switches_agree_and_are_on(self):
        js = re.search(r"var ON = (true|false);", SCRIPT.read_text(encoding="utf-8")).group(1)
        php = re.search(r"define\('ROSMAROPS_VISITS_ON', (true|false)\)", PLUGIN.read_text(encoding="utf-8")).group(1)
        self.assertEqual(js, php)
        self.assertEqual(js, "true", "switched on with the signed privacy texts (GTM-111 C)")

    def test_every_static_page_with_the_consent_script_loads_the_visit_script(self):
        missing = [str(f.relative_to(ROOT)) for f in sorted((ROOT / "site").rglob("*.html"))
                   if "consent/consent.js" in f.read_text(encoding="utf-8") and "/assets/visits/visits.js" not in f.read_text(encoding="utf-8")]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
