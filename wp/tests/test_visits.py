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
    def __init__(self, on, docroot, posts="", today=""):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        self.port = s.getsockname()[1]
        s.close()
        env = dict(os.environ, DB_PREFIX=PREFIX, VISITS_DOCROOT=str(docroot), VISITS_POSTS=posts, VISITS_TODAY=today)
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

    def test_the_three_homes_count(self):
        # GTM-118 (5): the home pages are static index.html files at the root of the site, like the deploy puts them.
        for p in ["es", "ca"]:
            (Path(self.tmp, p) / "index.html").write_text("<html></html>")
        self.visit("/", "")
        self.visit("/es/", "www.linkedin.com", path="/es/wp-json/rosmarops/v1/visits")
        self.visit("/ca/", "t.co", path="/ca/wp-json/rosmarops/v1/visits")
        self.assertEqual(self.rows(), ["/\ten\tdirect\t1", "/ca/\tca\tx\t1", "/es/\tes\tlinkedin\t1"])

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
        self.assertEqual([line.split("\t")[0] for line in self.rows()], ["other", "other"])

    def test_language_of_other_comes_from_the_path_prefix(self):
        # GTM-118: /es/, /ca/ or none, from the path the browser sent; never from the word "other".
        for p in ["/es/no-such-page/", "/es/blog/no-such-post", "/ca/no-such-page/", "/ca", "/no-such-page/", "/fr/page/",
                  "/es/Mayusculas/", 12, None]:
            self.visit(p, "")
        self.assertEqual(self.rows(), ["other\tca\tdirect\t2", "other\ten\tdirect\t4", "other\tes\tdirect\t3"])


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

    def test_internal_cookie_not_counted(self):
        # GTM-126: a browser marked with ?rosmarops_internal=1 carries this cookie; only its presence counts.
        self.visit("/methodology/", "", headers={"Cookie": "rosmarops_internal=1"})
        self.assertEqual(self.rows(), [])
        self.visit("/methodology/", "", headers={"Cookie": "other=1"})
        self.assertEqual(len(self.rows()), 1)

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
        self.assertEqual(set(d), {"generated_at", "rows", "people"})  # GTM-125 adds people; the rest is as before
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


PRINTS = PREFIX + "rosmarops_visits_prints"
PEOPLE = PREFIX + "rosmarops_people"
OPTIONS = PREFIX + "stub_sitemeta"
UA2 = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"


@unittest.skipUnless(db_available(), "no MySQL/MariaDB reachable")
class People(unittest.TestCase):
    """GTM-125: different people per UTC day, from a daily-key HMAC of IP and user agent that is never stored."""

    def setUp(self):
        self.drop()
        self.tmp = tempfile.mkdtemp()
        for p in ["", "methodology", "es/metodologia"]:
            d = Path(self.tmp, p)
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text("<html></html>")
        self.srv = None
        self.day("2026-11-09")

    def tearDown(self):
        self.srv.stop()
        shutil.rmtree(self.tmp)
        self.drop()

    def drop(self):
        mysql(f"DROP TABLE IF EXISTS {TABLE}, {PRINTS}, {PEOPLE}, {OPTIONS}")

    def day(self, d):
        if self.srv:
            self.srv.stop()
        self.srv = Server(True, self.tmp, today=d)

    def visit(self, page, ref="", ua=UA, headers=None, cookie=None):
        h = {"Origin": ORIGIN, "User-Agent": ua, "Content-Type": "application/json"}
        h.update(headers or {})
        if cookie:
            h["Cookie"] = cookie
        return self.srv.req("/wp-json/rosmarops/v1/visits", "POST", json.dumps({"p": page, "r": ref}), h)

    def people(self):
        return mysql(f"SELECT day, lang, ref, count FROM {PEOPLE} ORDER BY day, lang, ref").splitlines()

    def visits_total(self):
        return int(mysql(f"SELECT COALESCE(SUM(count), 0) FROM {TABLE}").strip())

    def key(self):
        out = mysql(f"SELECT v FROM {OPTIONS} WHERE k = 'rosmarops_people_key'").strip()
        return out

    def test_same_ip_and_browser_twice_is_one_person_and_two_visits(self):
        self.visit("/", "www.google.com")
        self.visit("/methodology/", "")
        self.assertEqual(self.visits_total(), 2)
        # the person is counted with the language and referrer kind of the first visit of the day
        self.assertEqual(self.people(), ["2026-11-09\ten\tgoogle\t1"])

    def test_another_browser_is_another_person(self):
        self.visit("/")
        self.visit("/es/metodologia/", ua=UA2)
        self.assertEqual(self.people(), ["2026-11-09\ten\tdirect\t1", "2026-11-09\tes\tdirect\t1"])

    def test_new_day_new_key_and_empty_prints(self):
        self.visit("/")
        k1 = self.key()
        self.assertIn("2026-11-09", k1)
        self.assertEqual(int(mysql(f"SELECT COUNT(*) FROM {PRINTS}").strip()), 1)
        self.day("2026-11-10")
        self.srv.req("/wp-json/rosmarops/v1/visits")  # nothing changes on a read
        self.assertEqual(self.key(), k1)
        self.visit("/methodology/", ua=UA2)  # first counted visit of the new day, from someone else
        k2 = self.key()
        self.assertIn("2026-11-10", k2)
        self.assertNotEqual(k1, k2)
        old_hex = re.search(r"[0-9a-f]{64}", k1).group(0)
        everything = mysql(f"SELECT * FROM {OPTIONS}") + mysql(f"SELECT * FROM {PRINTS}") + mysql(f"SELECT * FROM {PEOPLE}")
        self.assertNotIn(old_hex, everything)  # the old key no longer exists
        self.assertEqual(int(mysql(f"SELECT COUNT(*) FROM {PRINTS}").strip()), 1)  # only today's fingerprint
        self.assertEqual(int(mysql(f"SELECT COUNT(*) FROM {OPTIONS}").strip()), 1)  # just the key, no lock left
        # the same person as yesterday counts again today
        self.visit("/")
        self.assertEqual(self.people(), ["2026-11-09\ten\tdirect\t1", "2026-11-10\ten\tdirect\t2"])

    def test_cron_rotation_without_visits(self):
        self.visit("/")
        k1 = self.key()
        code = ("require %s; do_action('rosmarops_people_rotate');" % json.dumps(str(TESTS / "wp-stub.php")))
        env = dict(os.environ, DB_PREFIX=PREFIX, VISITS_ON="1", VISITS_TODAY="2026-11-10", VISITS_DOCROOT=self.tmp)
        subprocess.run(["php", "-r", code], env=env, check=True, capture_output=True)
        self.assertNotEqual(self.key(), k1)
        self.assertEqual(mysql(f"SELECT COUNT(*) FROM {PRINTS}").strip(), "0")

    def test_ip_and_browser_appear_nowhere(self):
        self.visit("/", "www.google.com")
        self.visit("/methodology/", ua=UA2)
        dump = "".join(mysql(f"SELECT * FROM {t}") for t in (TABLE, PRINTS, PEOPLE, OPTIONS))
        for leak in ["127.0.0.1", "Mozilla", "Chrome", "Safari", "Macintosh", "Windows NT"]:
            self.assertNotIn(leak, dump, leak)
        self.assertEqual([c.split("\t")[0] for c in mysql(f"SHOW COLUMNS FROM {PRINTS}").splitlines()], ["h"])
        src = PLUGIN.read_text(encoding="utf-8")
        block = src[src.index("people per day (GTM-125)"):src.index("if (ROSMAROPS_VISITS_ON) {")]
        for w in ("error_log", "file_put_contents", "setcookie", "set_transient", "update_option(", "add_option("):
            self.assertNotIn(w, block, w)

    def test_robots_team_and_prefetch_count_no_people(self):
        self.visit("/", ua="Googlebot/2.1 (+http://www.google.com/bot.html)")
        self.visit("/", headers={"Sec-Purpose": "prefetch"})
        self.visit("/", cookie="wordpress_logged_in_abc=1")
        self.visit("/", headers={"Origin": "https://example.com"})
        for t in (TABLE, PRINTS, PEOPLE):
            if mysql(f"SHOW TABLES LIKE '{t}'").strip():
                self.assertEqual(mysql(f"SELECT COUNT(*) FROM {t}").strip(), "0", t)
        self.visit("/")  # and a person reading does count, so the four above were filtered, not broken
        self.assertEqual(self.people(), ["2026-11-09\ten\tdirect\t1"])

    def test_endpoint_adds_people_and_keeps_the_rest(self):
        self.visit("/", "www.google.com")
        self.visit("/")
        st, h, body = self.srv.req("/wp-json/rosmarops/v1/visits")
        d = json.loads(body)
        self.assertEqual(sorted(d), ["generated_at", "people", "rows"])
        self.assertEqual(d["rows"], [{"day": "2026-11-09", "page": "/", "lang": "en", "ref": "direct", "count": 1},
                                     {"day": "2026-11-09", "page": "/", "lang": "en", "ref": "google", "count": 1}])
        self.assertEqual(d["people"], [{"day": "2026-11-09", "lang": "en", "ref": "google", "count": 1}])


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
const [src, visible, referrer, path, on, search, stored] = process.argv.slice(2);
let code = fs.readFileSync(src, 'utf8');
code = code.replace(/var ON = (true|false);/, on === '1' ? 'var ON = true;' : 'var ON = false;');
const calls = []; const listeners = {};
const touched = [];
const doc = { visibilityState: visible, referrer,
  addEventListener: (ev, fn) => { listeners[ev] = fn; } };
Object.defineProperty(doc, 'cookie', { get() { touched.push('cookie'); return ''; }, set() { touched.push('cookie'); } });
const trap = (name) => new Proxy({}, { get() { touched.push(name); return () => null; } });
// GTM-126: localStorage may only be read, and only the key rosmarops_internal.
const reads = [];
const storage = new Proxy({}, { get(t, prop) {
  if (prop === 'getItem') return (k) => { reads.push(k); return k === 'rosmarops_internal' && stored ? stored : null; };
  touched.push('localStorage.' + String(prop)); return () => null; } });
const win = { fetch: (url, opts) => { calls.push({ url, opts }); return Promise.resolve(); } };
const fn = new Function('window', 'document', 'location', 'fetch', 'localStorage', 'sessionStorage', 'indexedDB', 'URL', code);
win.localStorage = storage;
const loc = { pathname: path, search: search || '' };
fn(win, doc, loc, win.fetch, storage, trap('sessionStorage'), trap('indexedDB'), URL);
fn(win, doc, loc, win.fetch, storage, trap('sessionStorage'), trap('indexedDB'), URL); // included twice
const before = calls.length;
doc.visibilityState = 'visible';
if (listeners.visibilitychange) listeners.visibilitychange();
if (listeners.visibilitychange) listeners.visibilitychange();
console.log(JSON.stringify({ before, calls, touched, reads }));
"""


class Script(unittest.TestCase):
    def run_js(self, visible, referrer, path, on=True, search="", stored=""):
        if not shutil.which("node"):
            self.skipTest("node not on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(NODE_HARNESS)
        try:
            p = subprocess.run(["node", f.name, str(SCRIPT), visible, referrer, path, "1" if on else "0", search, stored],
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
        for word in ["cookie", "sessionstorage", "indexeddb", "navigator", "screen", "useragent", "date", "setitem", "removeitem"]:
            self.assertNotIn(word, code, word)
        # GTM-126: the only use of localStorage is reading the team's mark.
        self.assertEqual(re.findall(r"localstorage\.\w+\([^)]*\)", code), ["localstorage.getitem('rosmarops_internal')"])

    def test_internal_mark_in_url_sends_nothing(self):
        r = self.run_js("visible", "", "/methodology/", search="?rosmarops_internal=1")
        self.assertEqual(r["calls"], [])

    def test_internal_mark_in_storage_sends_nothing(self):
        r = self.run_js("visible", "", "/methodology/", stored="1")
        self.assertEqual(r["calls"], [])
        self.assertEqual(r["touched"], [])

    def test_internal_zero_counts_even_if_marked(self):
        r = self.run_js("visible", "", "/methodology/", search="?rosmarops_internal=0", stored="1")
        self.assertEqual(len(r["calls"]), 1)

    def test_no_mark_counts_and_only_reads_the_mark(self):
        r = self.run_js("visible", "", "/methodology/")
        self.assertEqual(len(r["calls"]), 1)
        self.assertEqual(set(r["reads"]), {"rosmarops_internal"})


CONSENT = ROOT / "site" / "assets" / "consent" / "consent.js"
CONSENT_HARNESS = r"""
const fs = require('fs');
const [src, search, stored, cookie] = process.argv.slice(2);
const store = {}; if (stored) store.rosmarops_internal = stored;
let jar = cookie || ''; const sets = [];
const ls = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = v; }, removeItem: k => { delete store[k]; } };
const doc = { documentElement: { lang: 'en' } };
Object.defineProperty(doc, 'cookie', { get() { return jar; }, set(v) { sets.push(v); jar = /Max-Age=0/.test(v) ? '' : v.split(';')[0]; } });
new Function('window', 'document', 'location', 'localStorage', 'URLSearchParams', fs.readFileSync(src, 'utf8'))({}, doc, { search }, ls, URLSearchParams);
console.log(JSON.stringify({ sets, store }));
"""
COOKIE_ON = "rosmarops_internal=1; Path=/; SameSite=Lax; Secure; Max-Age=34560000"


class InternalMark(unittest.TestCase):
    """GTM-126: consent.js sets the cookie rosmarops_internal with the mark, and deletes it with =0."""

    def run_js(self, search="", stored="", cookie=""):
        if not shutil.which("node"):
            self.skipTest("node not on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(CONSENT_HARNESS)
        try:
            p = subprocess.run(["node", f.name, str(CONSENT), search, stored, cookie], capture_output=True, text=True, check=True)
        finally:
            os.unlink(f.name)
        return json.loads(p.stdout)

    def test_mark_sets_cookie(self):
        r = self.run_js("?rosmarops_internal=1")
        self.assertEqual(r["sets"], [COOKIE_ON])
        self.assertEqual(r["store"], {"rosmarops_internal": "1"})

    def test_marked_without_cookie_gets_it_once(self):
        self.assertEqual(self.run_js(stored="1")["sets"], [COOKIE_ON])
        self.assertEqual(self.run_js(stored="1", cookie="rosmarops_internal=1")["sets"], [])

    def test_zero_deletes_cookie_and_mark(self):
        r = self.run_js("?rosmarops_internal=0", stored="1", cookie="rosmarops_internal=1")
        self.assertEqual(r["sets"], ["rosmarops_internal=; Path=/; SameSite=Lax; Secure; Max-Age=0"])
        self.assertEqual(r["store"], {})

    def test_unmarked_browser_gets_no_cookie(self):
        self.assertEqual(self.run_js()["sets"], [])


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
