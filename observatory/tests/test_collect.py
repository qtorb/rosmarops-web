"""Tests for observatory/collect.py (GTM-75 §5): every method with simulated responses, never the network.

For each method: opened, failure and retry, nothing new, new entries, ids that match scope_terms and ids that do not.
The whole output validates against observatory/schema/raw.v1.schema.json.

Run from the repository root:  python3 -m unittest observatory/tests/test_collect.py
"""

import copy
import datetime
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import collect  # noqa: E402

SOURCES = json.loads((ROOT / "observatory" / "sources.json").read_text(encoding="utf-8"))
TERMS = SOURCES["scope_terms"]
L = "2026-01-12"
TODAY = "2026-01-15"


def src(sid):
    return copy.deepcopy(next(s for s in SOURCES["sources"] if s["id"] == sid))


class Base(unittest.TestCase):
    def setUp(self):
        self.pauses = []
        patches = [
            mock.patch.object(collect, "sleep", self.pauses.append),
            mock.patch.object(collect, "TODAY", TODAY),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def web(self, pages):
        """Serve http_get from a dict url -> body (or an Exception to raise)."""
        def get(url):
            body = pages.get(url)
            if body is None:
                raise collect.ReadError(f"{url}: HTTP 404")
            if isinstance(body, Exception):
                raise body
            return body
        return mock.patch.object(collect, "http_get", side_effect=get)

    def tags(self, by_repo, info):
        """ls_remote_tags from by_repo[url]; tag_info from info[(url, tag)] = (date, text)."""
        return (mock.patch.object(collect, "ls_remote_tags", side_effect=lambda u: by_repo[u]),
                mock.patch.object(collect, "tag_info", side_effect=lambda u, t: info[(u, t)]))


# ----------------------------------------------------------------------------------------------------- retries

class Retry(Base):
    def test_retries_twice_with_ten_second_pauses_then_succeeds(self):
        calls = []

        class Resp:
            status = 200

            def read(self):
                return b"ok"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def urlopen(req, timeout):
            calls.append(req.get_header("User-agent"))
            if len(calls) < 3:
                raise urllib.error.URLError("reset")
            return Resp()

        with mock.patch("urllib.request.urlopen", side_effect=urlopen):
            self.assertEqual(collect.http_get("https://example.test/"), "ok")
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.pauses, [10, 10])
        self.assertEqual(set(calls), {"RosmarOps-Observatory/1 (+https://rosmarops.com)"})

    def test_gives_up_after_three_attempts(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")) as m:
            with self.assertRaises(collect.ReadError):
                collect.http_get("https://example.test/")
        self.assertEqual(m.call_count, 3)
        self.assertEqual(self.pauses, [10, 10])

    def test_git_is_retried_too(self):
        bad = mock.Mock(returncode=128, stderr="fatal: unable to access", stdout="")
        good = mock.Mock(returncode=0, stderr="", stdout="abc\trefs/tags/v1.0.0\n")
        with mock.patch("subprocess.run", side_effect=[bad, good]) as run:
            self.assertEqual(collect.ls_remote_tags("https://github.com/x/y.git"), ["v1.0.0"])
        self.assertEqual(run.call_count, 2)
        args = run.call_args.args[0]
        self.assertIn("core.hooksPath=" + collect.os.devnull, args)
        self.assertIn("http.userAgent=" + collect.UA, args)
        self.assertEqual(self.pauses, [10])


# --------------------------------------------------------------------------------------------- changelog-web

CLAUDE_PAGE = """<html><body><nav>Changelog</nav>
<div><p>2.1.12</p><p>January 14, 2026</p><ul><li>Added a check before sending the account email</li>
<li>Fixed CVE-2026-1111 in the MCP client</li></ul></div>
<div><p>2.1.11</p><p>January 13, 2026</p><ul><li>Fixed a crash</li></ul></div>
<div><p>2.1.10</p><p>January 9, 2026</p><ul><li>Older entry</li></ul></div>
</body></html>"""


class ChangelogWeb(Base):
    def run_f1(self, pages, since=L):
        with self.web(pages):
            return collect.read_changelog_web(src("F1"), since, TERMS)

    def test_opened_with_new_entries(self):
        r = self.run_f1({"https://code.claude.com/docs/en/changelog": CLAUDE_PAGE})
        self.assertTrue(r["opened"])
        self.assertIsNone(r["reason"])
        self.assertEqual((r["latest"], r["latest_date"]), ("2.1.12", "2026-01-14"))
        self.assertEqual([(e["date"], e["version"]) for e in r["new"]], [("2026-01-14", "2.1.12"), ("2026-01-13", "2.1.11")])
        self.assertIn("account email", r["new"][0]["text"])
        self.assertEqual(r["ids"], ["CVE-2026-1111"])
        self.assertEqual(r["read_with"], "curl")

    def test_nothing_new(self):
        r = self.run_f1({"https://code.claude.com/docs/en/changelog": CLAUDE_PAGE}, since="2026-01-15")
        self.assertTrue(r["opened"])
        self.assertEqual((r["new"], r["ids"]), ([], []))
        self.assertEqual(r["latest_date"], "2026-01-14")

    def test_text_is_trimmed_to_600(self):
        page = CLAUDE_PAGE.replace("Fixed a crash", "x " * 800)
        r = self.run_f1({"https://code.claude.com/docs/en/changelog": page})
        self.assertTrue(all(len(e["text"]) <= 600 for e in r["new"]))

    def test_page_without_dates_is_not_opened(self):
        r = self.run_f1({"https://code.claude.com/docs/en/changelog": "<html><body><p>Moved</p></body></html>"})
        self.assertFalse(r["opened"])
        self.assertIn("no dated entries", r["reason"])

    def test_failure_falls_back_to_git_tags_without_new_version(self):
        url = "https://github.com/anthropics/claude-code.git"
        a, b = self.tags({url: ["v2.1.12", "v2.1.11"]}, {(url, "v2.1.12"): ("2026-01-10", "")})
        with self.web({"https://code.claude.com/docs/en/changelog": collect.ReadError("HTTP 503")}), a, b:
            r = collect.read_changelog_web(src("F1"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual(r["read_with"], "git")
        self.assertEqual((r["latest"], r["latest_date"], r["new"]), ("v2.1.12", "2026-01-10", []))
        self.assertIn("changelog page failed", r["reason"])

    def test_two_pages_and_calendar_versions(self):
        pages = {
            "https://cursor.com/changelog": "<html><body><p>Jan 13, 2026</p><h1>Agent SDK</h1><p>Agents as code.</p></body></html>",
            "https://cursor.com/docs/cli/changelog": "<html><body><h2>v2026.01.14</h2><h3>Hooks</h3><p>Hooks fire for subagents.</p>"
                                                     "<h2>v2026.01.02</h2><p>Old.</p></body></html>",
        }
        with self.web(pages):
            r = collect.read_changelog_web(src("F2"), L, TERMS)
        self.assertEqual((r["latest"], r["latest_date"]), ("v2026.01.14", "2026-01-14"))
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-14", "2026-01-13"])

    def test_time_datetime_attribute(self):
        page = ('<html><body><article><time datetime="2026-01-14T10:00:00Z">Jan.14</time><h3>Copilot agent hooks</h3>'
                '<p>Release</p></article></body></html>')
        with self.web({"https://github.blog/changelog/label/copilot/": page}):
            r = collect.read_changelog_web(src("F6"), L, TERMS)
        self.assertEqual(r["latest_date"], "2026-01-14")
        self.assertEqual(len(r["new"]), 1)

    def test_future_dates_are_ignored(self):
        page = CLAUDE_PAGE.replace("January 14, 2026", "January 20, 2026")
        r = self.run_f1({"https://code.claude.com/docs/en/changelog": page})
        self.assertEqual(r["latest_date"], "2026-01-13")

    def test_only_entries_with_filter(self):
        page = ("<html><body><time>2026-01-14</time><h3>Codex CLI 0.170.0</h3><p>CLI.</p>"
                "<time>2026-01-13</time><h3>Codex Cloud environments</h3><p>Cloud tasks.</p></body></html>")
        with self.web({"https://developers.openai.com/codex/changelog": page}):
            r = collect.read_changelog_web(src("F21"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-13"])
        with self.web({"https://developers.openai.com/codex/changelog": page.replace("Codex Cloud", "Codex app")}):
            r = collect.read_changelog_web(src("F21"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["new"], r["latest"], r["latest_date"]), ([], None, None))


# -------------------------------------------------------------------------------------------------- git-tags

CLINE = "https://github.com/cline/cline.git"
CLINE_LOG = "https://raw.githubusercontent.com/cline/cline/main/CHANGELOG.md"
CLINE_MD = "# Changelog\n\n## [4.2.0]\n\n### Added\n\n- Cloud tasks toggle\n- Fix for GHSA-abcd-efgh-ijkl\n\n## [4.1.0]\n\n- Older\n"


class GitTags(Base):
    def run_src(self, s, by_repo, info, pages):
        a, b = self.tags(by_repo, info)
        with a, b, self.web(pages):
            return collect.read_git_tags(s, L, TERMS)

    def test_new_version_with_notes_from_raw_changelog(self):
        r = self.run_src(src("F7"), {CLINE: ["v4.1.0", "v4.2.0", "v4.2.0-rc.1", "vscode-v9.0.0"]},
                         {(CLINE, "v4.2.0"): ("2026-01-14", ""), (CLINE, "v4.1.0"): ("2026-01-02", "")},
                         {CLINE_LOG: CLINE_MD})
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("v4.2.0", "2026-01-14"))
        self.assertEqual(len(r["new"]), 1)
        self.assertIn("Cloud tasks toggle", r["new"][0]["text"])
        self.assertNotIn("Older", r["new"][0]["text"])
        self.assertEqual(r["ids"], ["GHSA-abcd-efgh-ijkl"])
        self.assertEqual(r["read_with"], "git")

    def test_nothing_new(self):
        r = self.run_src(src("F7"), {CLINE: ["v4.1.0"]}, {(CLINE, "v4.1.0"): ("2026-01-02", "")}, {})
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["new"], r["ids"]), ("v4.1.0", [], []))

    def test_new_version_without_notes_is_not_opened(self):
        r = self.run_src(src("F7"), {CLINE: ["v4.3.0"]}, {(CLINE, "v4.3.0"): ("2026-01-14", "")}, {CLINE_LOG: CLINE_MD})
        self.assertFalse(r["opened"])
        self.assertIn("new version without notes: v4.3.0", r["reason"])
        self.assertEqual(r["latest"], "v4.3.0")

    def test_fragile_source_opens_without_notes(self):
        goose = "https://github.com/aaif-goose/goose.git"
        r = self.run_src(src("F19"), {goose: ["v1.58.0"]}, {(goose, "v1.58.0"): ("2026-01-14", "")}, {})
        self.assertTrue(r["opened"])
        self.assertIsNone(r["reason"])
        self.assertEqual(r["new"], [{"date": "2026-01-14", "version": "v1.58.0", "text": "notes not available"}])

    def test_annotated_tag_text_is_the_notes(self):
        hermes = "https://github.com/NousResearch/hermes-agent.git"
        r = self.run_src(src("F5"), {hermes: ["v0.22.6"]}, {(hermes, "v0.22.6"): ("2026-01-14", "Rollup patch: MCP fixes")}, {})
        self.assertTrue(r["opened"])
        self.assertEqual(r["new"][0]["text"], "Rollup patch: MCP fixes")

    def test_notes_from_web_changelog(self):
        codex = "https://github.com/openai/codex.git"
        page = ("<html><body><time>2026-01-14</time><h3>Codex CLI 0.170.0</h3><p>Approval presets.</p>"
                "<time>2026-01-13</time><h3>Codex CLI 0.169.0</h3><p>Older.</p></body></html>")
        r = self.run_src(src("F3"), {codex: ["rust-v0.170.0", "rust-v0.169.0", "rust-v.0.0.2504291954", "voice-x"]},
                         {(codex, "rust-v0.170.0"): ("2026-01-14", ""), (codex, "rust-v0.169.0"): ("2026-01-11", "")},
                         {"https://developers.openai.com/codex/changelog": page})
        self.assertTrue(r["opened"])
        self.assertEqual(r["latest"], "rust-v0.170.0")
        self.assertIn("Approval presets", r["new"][0]["text"])

    def test_split_changelog_follows_the_version_file(self):
        oc = "https://github.com/openclaw/openclaw.git"
        index = ("# Changelog\n\n- [2026.1.14](CHANGELOG/2026.1.14.md) · [Raw](https://github.com/openclaw/openclaw/raw/refs/heads/main/"
                 "CHANGELOG/2026.1.14.md)\n- [2026.1.9](CHANGELOG/2026.1.9.md)\n")
        r = self.run_src(src("F22"), {oc: ["v2026.1.14"]}, {(oc, "v2026.1.14"): ("2026-01-14", "")},
                         {"https://raw.githubusercontent.com/openclaw/openclaw/main/CHANGELOG.md": index,
                          "https://raw.githubusercontent.com/openclaw/openclaw/main/CHANGELOG/2026.1.14.md":
                              "# 2026.1.14\n\n- Adds MCP Relay, off by default"})
        self.assertTrue(r["opened"])
        self.assertIn("MCP Relay", r["new"][0]["text"])

    def test_n_n_n_pattern_and_ignores(self):
        lg = "https://github.com/langchain-ai/langgraph.git"
        r = self.run_src(src("F23"), {lg: ["1.2.19", "1.3.0", "cli==0.9.9", "sdk==9.0.0", "v0.0.8", "1.3.0rc1"]},
                         {(lg, "1.3.0"): ("2026-01-10", "")}, {})
        self.assertEqual(r["latest"], "1.3.0")

    def test_also_repository_is_noted_when_new(self):
        af, ag = "https://github.com/microsoft/agent-framework.git", "https://github.com/microsoft/autogen.git"
        r = self.run_src(src("F25"), {af: ["python-1.24.0", "dotnet-1.0.0"], ag: ["python-v0.7.6", "v0.4.4"]},
                         {(af, "python-1.24.0"): ("2026-01-02", ""), (ag, "python-v0.7.6"): ("2026-01-14", "AutoGen 0.7.6")}, {})
        self.assertTrue(r["opened"])
        self.assertEqual(r["latest"], "python-1.24.0")
        self.assertEqual(r["new"], [{"date": "2026-01-14", "version": "autogen python-v0.7.6", "text": "AutoGen 0.7.6"}])

    def test_git_failure_is_not_opened(self):
        with mock.patch.object(collect, "ls_remote_tags", side_effect=collect.ReadError("git ls-remote: timeout")):
            r = collect.read_git_tags(src("F26"), L, TERMS)
        self.assertFalse(r["opened"])
        self.assertIn("timeout", r["reason"])

    def test_version_order_is_like_sort_v(self):
        self.assertEqual(sorted(["v1.10.0", "v1.9.2", "v1.10.0-vscode", "v2.0.0"], key=collect.version_key)[-1], "v2.0.0")
        self.assertEqual(sorted(["2025-11-25", "2026-07-28", "2025-03-26"], key=collect.version_key)[-1], "2026-07-28")


# ------------------------------------------------------------------------------------------------------ ossf

def mal(rid, name, published):
    return {"id": rid, "published": published + "T08:00:00Z", "summary": f"Malicious code in {name} (npm)",
            "affected": [{"package": {"ecosystem": "npm", "name": name}}]}


class Ossf(Base):
    def test_ids_that_match_and_that_do_not(self):
        found = [("osv/malicious/npm/@ifasn/md-doc-mcp/MAL-2026-1.json", mal("MAL-2026-1", "@ifasn/md-doc-mcp", "2026-01-13")),
                 ("osv/malicious/npm/left-pad-x/MAL-2026-2.json", mal("MAL-2026-2", "left-pad-x", "2026-01-13")),
                 ("osv/malicious/npm/claude-helper/MAL-2025-9.json", mal("MAL-2025-9", "claude-helper", "2025-12-01"))]
        with mock.patch.object(collect, "ossf_read", return_value=found) as m:
            r = collect.read_ossf(src("F10"), L, TERMS)
        self.assertEqual(m.call_args.args, ("https://github.com/ossf/malicious-packages.git", "main", L,
                                            ["osv/malicious/npm/*/MAL-*.json", "osv/malicious/pypi/*/MAL-*.json"]))
        self.assertTrue(r["opened"])
        self.assertEqual(r["ids"], ["MAL-2026-1"])
        self.assertEqual(len(r["new"]), 1)
        self.assertEqual(r["latest_date"], "2026-01-13")
        self.assertEqual(r["read_with"], "git")

    def test_reserved_mal_ids_are_kept(self):
        found = [("osv/malicious/npm/x-mcp/MAL-0000-amazon-inspector-0a89.json",
                  mal("MAL-0000-amazon-inspector-0a89", "x-mcp", "2026-01-13"))]
        with mock.patch.object(collect, "ossf_read", return_value=found):
            r = collect.read_ossf(src("F10"), L, TERMS)
        self.assertEqual(r["ids"], ["MAL-0000-amazon-inspector-0a89"])

    def test_nothing_new(self):
        with mock.patch.object(collect, "ossf_read", return_value=[]):
            r = collect.read_ossf(src("F10"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["ids"], r["new"], r["latest_date"]), ([], [], None))

    def test_failure(self):
        with mock.patch.object(collect, "ossf_read", side_effect=collect.ReadError("git fetch: reset")):
            r = collect.read_ossf(src("F10"), L, TERMS)
        self.assertFalse(r["opened"])


# --------------------------------------------------------------------------------------------------- osv-csv

NPM_CSV = "https://osv-vulnerabilities.storage.googleapis.com/npm/modified_id.csv"
PYPI_CSV = "https://osv-vulnerabilities.storage.googleapis.com/PyPI/modified_id.csv"


def osv_rec(rid, name, published):
    return json.dumps({"id": rid, "published": published + "T00:00:00Z", "summary": "x",
                       "affected": [{"package": {"name": name}}]})


class Osv(Base):
    def test_ids_that_match_and_that_do_not(self):
        pages = {
            NPM_CSV: "2026-01-14T10:00:00Z,GHSA-aaaa-bbbb-cccc\n2026-01-13T10:00:00Z,GHSA-dddd-eeee-ffff\n"
                     "2026-01-01T10:00:00Z,GHSA-old0-old0-old0\n",
            PYPI_CSV: "2026-01-14T09:00:00Z,PYSEC-2026-1\n",
            "https://api.osv.dev/v1/vulns/GHSA-aaaa-bbbb-cccc": osv_rec("GHSA-aaaa-bbbb-cccc", "mcp-remote", "2026-01-14"),
            "https://api.osv.dev/v1/vulns/GHSA-dddd-eeee-ffff": osv_rec("GHSA-dddd-eeee-ffff", "lodash", "2026-01-13"),
            "https://api.osv.dev/v1/vulns/PYSEC-2026-1": osv_rec("PYSEC-2026-1", "langgraph-old", "2025-06-01"),
        }
        with self.web(pages):
            r = collect.read_osv(src("F14"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual(r["ids"], ["GHSA-aaaa-bbbb-cccc"])
        self.assertEqual(r["latest_date"], "2026-01-14")

    def test_nothing_new(self):
        with self.web({NPM_CSV: "2026-01-01T10:00:00Z,GHSA-old0-old0-old0\n", PYPI_CSV: ""}):
            r = collect.read_osv(src("F14"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["ids"], r["new"]), ([], []))

    def test_failure(self):
        with self.web({NPM_CSV: "", PYPI_CSV: collect.ReadError("HTTP 500")}):
            r = collect.read_osv(src("F14"), L, TERMS)
        self.assertFalse(r["opened"])
        self.assertIn("HTTP 500", r["reason"])


# ------------------------------------------------------------------------------------------------------- nvd

def nvd_page(*cves):
    return json.dumps({"vulnerabilities": [{"cve": {"id": c, "published": p + "T10:00:00.000",
                                                    "descriptions": [{"lang": "en", "value": d}]}} for c, p, d in cves]})


class Nvd(Base):
    def test_terms_pause_seven_seconds_and_ids(self):
        urls = []

        def get(url):
            urls.append(url)
            if "keywordSearch=MCP&" in url:
                return nvd_page(("CVE-2026-0001", "2026-01-13", "Path traversal in an MCP server"))
            if "keywordSearch=Cursor&" in url:
                return nvd_page(("CVE-2026-0002", "2026-01-14", "psqlODBC fetch with a server-side buffer overflow"))
            return nvd_page()
        with mock.patch.object(collect, "http_get", side_effect=get):
            r = collect.read_nvd(src("F15"), L, TERMS)
        self.assertEqual(len(urls), 9)
        self.assertIn("keywordSearch=Claude%20Code&pubStartDate=2026-01-12T00:00:00.000&pubEndDate=2026-01-15T23:59:59.999", urls[1])
        self.assertEqual(self.pauses, [7] * 8)
        self.assertTrue(r["opened"])
        self.assertEqual(r["ids"], ["CVE-2026-0001"])
        self.assertEqual(r["latest_date"], "2026-01-14")

    def test_nothing_new(self):
        with mock.patch.object(collect, "http_get", return_value=nvd_page()):
            r = collect.read_nvd(src("F15"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["ids"], r["new"], r["latest_date"]), ([], [], None))

    def test_failure(self):
        with mock.patch.object(collect, "http_get", side_effect=collect.ReadError("HTTP 403")):
            r = collect.read_nvd(src("F15"), L, TERMS)
        self.assertFalse(r["opened"])


# ------------------------------------------------------------------------------------------------------- kev

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def kev(*rows):
    return json.dumps({"catalogVersion": "2026.01.14", "dateReleased": "2026-01-14T17:00:00Z", "vulnerabilities": [
        {"cveID": c, "vendorProject": v, "product": p, "dateAdded": d, "vulnerabilityName": "n", "shortDescription": "s"}
        for c, v, p, d in rows]})


class Kev(Base):
    def test_ids_that_match_and_that_do_not(self):
        body = kev(("CVE-2026-1", "Microsoft", "Visual Studio Code", "2026-01-13"),
                   ("CVE-2026-2", "Microsoft", "Windows", "2026-01-13"),
                   ("CVE-2026-3", "Zyxel", "Firewall", "2026-01-14"),
                   ("CVE-2026-4", "Acme", "Acme MCP Server", "2026-01-14"),
                   ("CVE-2025-5", "Anthropic", "Claude Code", "2025-12-01"))
        with self.web({KEV_URL: body}):
            r = collect.read_kev(src("F28"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("2026.01.14", "2026-01-14"))
        self.assertEqual(r["ids"], ["CVE-2026-1", "CVE-2026-4"])

    def test_nothing_new(self):
        with self.web({KEV_URL: kev(("CVE-2025-5", "Anthropic", "Claude Code", "2025-12-01"))}):
            r = collect.read_kev(src("F28"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["ids"], r["new"]), ([], []))

    def test_failure(self):
        with self.web({KEV_URL: "<html>maintenance</html>"}):
            r = collect.read_kev(src("F28"), L, TERMS)
        self.assertFalse(r["opened"])


# ------------------------------------------------------------------------------------------- whole run + schema

class WholeRun(Base):
    def test_output_validates_against_raw_v1_and_counts(self):
        def fake(s, since, terms):
            r = collect.blank(s, "curl")
            if s["id"] != "F5":
                r.update(opened=True, latest="1.0.0", latest_date="2026-01-14",
                         new=[{"date": "2026-01-14", "version": "1.0.0", "text": "x"}],
                         ids=["MAL-2026-18486", "MAL-0000-amazon-inspector-0a89", "GHSA-abcd-efgh-ijkl", "CVE-2026-116635"])
            else:
                r["reason"] = "new version without notes: v0.22.7"
            return r
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-01-12.json").write_text("{}", encoding="utf-8")
            Path(d, "2026-01-15.json").write_text("{}", encoding="utf-8")  # today's own file never sets L
            seen = []
            with mock.patch.dict(collect.METHODS, {m: (lambda s, since, terms: (seen.append(since), fake(s, since, terms))[1])
                                                   for m in collect.METHODS}):
                out = collect.collect(raw_dir=d, now=datetime.datetime(2026, 1, 15, 5, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(set(seen), {"2026-01-12"})
        self.assertEqual((out["date"], out["collected_at"], out["opened"], out["total"]),
                         ("2026-01-15", "2026-01-15T05:30:00Z", 27, 28))
        self.assertEqual([s["id"] for s in out["sources"]], [f"F{i}" for i in range(1, 29)])
        validate(self, out)

    def test_l_defaults_to_seven_days(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(collect.last_raw_date(d, "2026-01-15"), "2026-01-08")

    def test_madrid_date(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(collect.METHODS, {m: lambda s, *a: collect.blank(s, "git") | {"reason": "x"}
                                                                                    for m in collect.METHODS}):
            out = collect.collect(raw_dir=d, now=datetime.datetime(2026, 1, 14, 23, 30, tzinfo=datetime.timezone.utc))
        self.assertEqual(out["date"], "2026-01-15")
        self.assertEqual(out["opened"], 0)

    def test_unexpected_error_closes_one_source(self):
        with mock.patch.dict(collect.METHODS, {"kev": mock.Mock(side_effect=KeyError("vulnerabilities"))}):
            r = collect.collect_source(src("F28"), L, TERMS)
        self.assertFalse(r["opened"])
        self.assertIn("collector error", r["reason"])

    def test_broken_output_fails_schema(self):
        out = {"date": "2026-01-15", "collected_at": "2026-01-15T05:30:00Z", "sources": [], "opened": 0, "total": 28}
        self.assertTrue(errors(out))
        s = collect.blank(src("F1"), "curl")  # not opened and no reason
        out["sources"] = [dict(s, id=f"F{i}") for i in range(1, 29)]
        self.assertTrue(errors(out))


class SourcesFile(unittest.TestCase):
    def test_sources_file(self):
        daily = json.loads((ROOT / "observatory" / "daily" / "2026-11-03.json").read_text(encoding="utf-8"))
        checked = {c["name"]: c["url"] for c in daily["checked"]}
        ids = [s["id"] for s in SOURCES["sources"]]
        self.assertEqual(ids, [f"F{i}" for i in range(1, 29)])
        for s in SOURCES["sources"]:
            self.assertEqual(set(s), {"id", "name", "scope", "method", "read", "public_url", "fragile", "notes"}, s["id"])
            self.assertIn(s["method"], collect.METHODS, s["id"])
            self.assertEqual(s["fragile"], s["id"] in ("F8", "F19"), s["id"])
            self.assertNotIn("raw.githubusercontent.com", s["public_url"], s["id"])
            if s["name"] != "Hermes Agent":
                self.assertEqual(s["public_url"], checked[s["name"]], s["id"])
        self.assertEqual(len(SOURCES["scope_terms"]), 21)


def errors(data):
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        raise unittest.SkipTest("jsonschema not installed (CI installs it)")
    schema = json.loads((ROOT / "observatory" / "schema" / "raw.v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return [e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data)]


def validate(test, data):
    test.assertEqual(errors(data), [])


if __name__ == "__main__":
    unittest.main()
