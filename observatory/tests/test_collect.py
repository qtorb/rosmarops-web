"""Tests for observatory/collect.py (GTM-75 §5): every method with simulated responses, never the network.

For each method: opened, failure and retry, nothing new, new entries, ids that match scope_terms and ids that do not.
The whole output validates against observatory/schema/raw.v1.schema.json.

Run from the repository root:  python3 -m unittest observatory/tests/test_collect.py
"""

import copy
import datetime
import io
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
import daily_check  # noqa: E402

SOURCES = json.loads((ROOT / "observatory" / "sources.json").read_text(encoding="utf-8"))
TERMS = SOURCES["scope_terms"]
IDS = [s["id"] for s in SOURCES["sources"]]
L = "2026-01-12"
TODAY = "2026-01-15"


def src(sid):
    return copy.deepcopy(next(s for s in SOURCES["sources"] if s["id"] == sid))


class _Resp:
    status = 200

    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Base(unittest.TestCase):
    def setUp(self):
        self.pauses = []
        self.clients = []
        patches = [
            mock.patch.object(collect, "sleep", self.pauses.append),
            mock.patch.object(collect, "TODAY", TODAY),
            mock.patch.object(collect, "_releases", {}),
            mock.patch.object(collect, "API_ERRORS", []),
        ]
        self.api_requests = []
        self.releases = {}  # repo "owner/name" -> {tag: body}; anything else answers like an empty release list
        p = mock.patch("urllib.request.urlopen", side_effect=self.fake_api)
        patches.append(p)
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def fake_api(self, req, timeout):
        url = req.full_url
        if not url.startswith("https://api.github.com/repos/"):
            raise AssertionError(f"unexpected network call: {url}")
        repo = url.split("/repos/", 1)[1].split("/releases", 1)[0]
        if callable(self.releases.get(repo)):
            raise self.releases[repo]()  # a fresh error per attempt, as the network would give
        self.api_requests.append(req)
        return _Resp(json.dumps([{"tag_name": k, "body": v} for k, v in self.releases.get(repo, {}).items()]).encode())

    def web(self, pages):
        """Serve http_get from a dict url -> body (or an Exception to raise)."""
        def get(url, client=None):
            self.clients.append(client)
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

    def test_git_failure_reason_has_subcommand_code_and_stderr_tail(self):
        stderr = "x" * 500 + "fatal: could not read from remote repository: shallow boundary missing"
        bad = mock.Mock(returncode=128, stderr=stderr, stdout="")
        with mock.patch("subprocess.run", return_value=bad):
            with self.assertRaises(collect.ReadError) as cm:
                collect.run_git(["-c", "fetch.negotiationAlgorithm=noop", "log", "--format=", "--raw", "refs/remotes/origin/main"])
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("git log: exit 128: "), msg)
        self.assertTrue(msg.endswith("shallow boundary missing"), msg)
        self.assertEqual(len(msg), len("git log: exit 128: ") + 200)
        self.assertNotIn("core.hooksPath", msg)
        self.assertNotIn("--format", msg)

    def test_git_timeout_reason(self):
        to = collect.subprocess.TimeoutExpired(["git", "log"], 180, stderr=b"remote: counting objects")
        with mock.patch("subprocess.run", side_effect=to):
            with self.assertRaises(collect.ReadError) as cm:
                collect.run_git(["log", "--raw"])
        self.assertEqual(str(cm.exception), "git log: exit timeout (180 s): remote: counting objects")
        self.assertEqual(self.pauses, [10, 10])

    def test_ossf_reason_from_a_failing_git(self):
        bad = mock.Mock(returncode=128, stderr="fatal: protocol error: bad pack header", stdout="")
        with mock.patch("subprocess.run", return_value=bad):
            r = collect.read_ossf(src("F10"), L, TERMS)
        self.assertFalse(r["opened"])
        self.assertEqual(r["reason"], "git init: exit 128: fatal: protocol error: bad pack header")
        self.assertLessEqual(len(r["reason"]), 300)


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


# ------------------------------------------------------------------------------------- GTM-76: notes, F5, F13, F21

class GithubApiNotes(Base):
    def run_src(self, s, by_repo, info, pages):
        a, b = self.tags(by_repo, info)
        with a, b, self.web(pages):
            return collect.read_git_tags(s, L, TERMS)

    def test_release_body_comes_first(self):
        self.releases["cline/cline"] = {"v4.2.0": "## What's changed\n- MCP marketplace approvals"}
        with mock.patch.dict(collect.os.environ, {"GH_TOKEN": "t0ken"}):
            r = self.run_src(src("F7"), {CLINE: ["v4.2.0"]}, {(CLINE, "v4.2.0"): ("2026-01-14", "")}, {})  # no raw served
        self.assertTrue(r["opened"])
        self.assertIn("MCP marketplace approvals", r["new"][0]["text"])
        req = self.api_requests[0]
        self.assertEqual(req.full_url, "https://api.github.com/repos/cline/cline/releases?per_page=10")
        self.assertEqual(req.get_header("Accept"), "application/vnd.github+json")
        self.assertEqual(req.get_header("Authorization"), "Bearer t0ken")
        self.assertEqual(req.get_header("User-agent"), collect.UA)

    def test_empty_release_body_falls_back_to_raw(self):
        self.releases["cline/cline"] = {"v4.2.0": "  "}
        r = self.run_src(src("F7"), {CLINE: ["v4.2.0"]}, {(CLINE, "v4.2.0"): ("2026-01-14", "")}, {CLINE_LOG: CLINE_MD})
        self.assertTrue(r["opened"])
        self.assertIn("Cloud tasks toggle", r["new"][0]["text"])

    def test_one_api_read_per_repository(self):
        self.releases["cline/cline"] = {"v4.2.0": "a", "v4.1.9": "b"}
        self.run_src(src("F7"), {CLINE: ["v4.2.0", "v4.1.9"]},
                     {(CLINE, "v4.2.0"): ("2026-01-14", ""), (CLINE, "v4.1.9"): ("2026-01-13", "")}, {})
        self.assertEqual(len(self.api_requests), 1)

    def test_api_403_is_reported_with_its_answer(self):
        self.releases["langchain-ai/langgraph"] = lambda: collect.urllib.error.HTTPError(
            "https://api.github.com/x", 403, "Forbidden", {"x-ratelimit-remaining": "0"},
            io.BytesIO(b'{"message":"API rate limit exceeded"}'))
        lg = "https://github.com/langchain-ai/langgraph.git"
        r = self.run_src(src("F23"), {lg: ["1.3.0"]}, {(lg, "1.3.0"): ("2026-01-14", "")}, {})
        self.assertFalse(r["opened"])
        self.assertIn("HTTP 403 (rate limit left 0)", r["reason"])
        self.assertIn("API rate limit exceeded", r["reason"])
        self.assertEqual(self.pauses, [10, 10])

    def test_fragile_source_with_api_notes(self):
        self.releases["aaif-goose/goose"] = {"v1.58.0": "Recipes can no longer run shell without approval"}
        goose = "https://github.com/aaif-goose/goose.git"
        r = self.run_src(src("F19"), {goose: ["v1.58.0"]}, {(goose, "v1.58.0"): ("2026-01-14", "open release branch")}, {})
        self.assertEqual(r["new"][0]["text"], "Recipes can no longer run shell without approval")

    def test_gemini_api_first_web_last(self):
        gem = "https://github.com/google-gemini/gemini-cli.git"
        web = "https://geminicli.com/docs/changelogs/"
        page = "<html><body><h2>Announcements: v0.70.0 - 2026-01-14</h2><p>From the web.</p></body></html>"
        self.releases["google-gemini/gemini-cli"] = {"v0.70.0": "From the API."}
        r = self.run_src(src("F11"), {gem: ["v0.70.0", "v0.71.0-nightly.1"]}, {(gem, "v0.70.0"): ("2026-01-14", "")}, {web: page})
        self.assertEqual((r["latest"], r["new"][0]["text"]), ("v0.70.0", "From the API."))
        self.releases["google-gemini/gemini-cli"] = {}
        collect._releases.clear()
        r = self.run_src(src("F11"), {gem: ["v0.70.0"]}, {(gem, "v0.70.0"): ("2026-01-14", "")}, {web: page})
        self.assertEqual(r["new"][0]["text"], "From the web.")

    def test_every_tag_source_asks_the_api_first(self):
        for s in SOURCES["sources"]:
            if s["method"] == "git-tags":
                self.assertEqual(s["read"]["notes"][0], "github-api", s["id"])


class N8nSource(Base):
    N8N = "https://github.com/n8n-io/n8n.git"

    def test_prefixed_pattern(self):
        ok = collect.tag_matcher("n8n@N.N.N", None)
        self.assertEqual([t for t in ["n8n@3.1.0", "n8n@0.189.1", "release/1.37.2", "stable", "v1", "n8n@3.1.0-rc.1",
                                      "n8n@3.1", "@n8n/api-types@1.0.0"] if ok(t)], ["n8n@3.1.0", "n8n@0.189.1"])
        self.assertTrue(collect.tag_matcher("N.N.N", None)("1.2.19"))
        self.assertFalse(collect.tag_matcher("N.N.N", None)("v1.2.19"))

    def test_version_number(self):
        for tag, num in (("n8n@3.1.0", "3.1.0"), ("rust-v0.166.0", "0.166.0"), ("python-1.24.0", "1.24.0"),
                         ("v2026.10.10", "2026.10.10"), ("2026-07-28", "2026-07-28")):
            self.assertEqual(collect.version_number(tag), num)

    def test_notes_from_release_then_from_the_web_heading(self):
        page = ("<html><body><h2>n8n 3.1.0 Agent nodes ask before running tools</h2><p>Released 2026-01-14.</p>"
                "<p>MCP Client node asks for approval.</p><h2>n8n 3.0.2 Older</h2><p>Older notes.</p></body></html>")
        a, b = self.tags({self.N8N: ["n8n@3.1.0", "n8n@3.0.2", "stable"]},
                         {(self.N8N, "n8n@3.1.0"): ("2026-01-14", ""), (self.N8N, "n8n@3.0.2"): ("2026-01-02", "")})
        with a, b, self.web({"https://docs.n8n.io/release-notes/": page}):
            r = collect.read_git_tags(src("F31"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("n8n@3.1.0", "2026-01-14"))
        self.assertIn("MCP Client node asks for approval", r["new"][0]["text"])
        self.assertNotIn("Older notes", r["new"][0]["text"])
        self.releases["n8n-io/n8n"] = {"n8n@3.1.0": "From the GitHub release."}
        collect._releases.clear()
        with a, b, self.web({"https://docs.n8n.io/release-notes/": page}):
            r = collect.read_git_tags(src("F31"), L, TERMS)
        self.assertEqual(r["new"][0]["text"], "From the GitHub release.")


class Gtm76Sources(Base):
    def test_hermes_pattern_v0(self):
        hermes = "https://github.com/NousResearch/hermes-agent.git"
        a, b = self.tags({hermes: ["v2026.9.24", "v0.22.6", "v0.22.6+canary.20261103T064339Z", "v0.22.5"]},
                         {(hermes, "v0.22.6"): ("2026-01-10", "")})
        with a, b:
            r = collect.read_git_tags(src("F5"), L, TERMS)
        self.assertEqual((r["latest"], r["latest_date"]), ("v0.22.6", "2026-01-10"))

    def test_claude_desktop_ignores_the_updated_date(self):
        page = ('<html><body><header><h1>Release notes</h1><time datetime="2026-01-14T21:51:46Z" title="January 14, 2026">'
                'Updated this week</time></header><h2>January 2026</h2><h3>January 11, 2026</h3>'
                '<p>Desktop extensions ask before reading files.</p><h3>January 13, 2026</h3><p>Connectors directory.</p>'
                '</body></html>')
        with self.web({"https://support.claude.com/en/articles/12138966-release-notes": page}):
            r = collect.read_changelog_web(src("F13"), L, TERMS)
        self.assertEqual(r["latest_date"], "2026-01-13")
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-13"])
        self.assertNotIn("Updated", " ".join(e["text"] for e in r["new"]))

    def test_codex_cloud_title_or_label_only_and_since_l(self):
        page = ("<html><body>"
                "<time>2026-01-14</time><h3>Codex app 26.114</h3><p>Hand off a task to Codex Cloud from the app.</p>"
                "<time>2026-01-13</time><h3>Faster environments</h3><p>Codex Cloud</p><p>Setup scripts are cached.</p>"
                "<time>2026-01-02</time><h3>Codex Cloud tasks in Slack</h3><p>Older.</p>"
                "</body></html>")
        with self.web({"https://developers.openai.com/codex/changelog": page}):
            r = collect.read_changelog_web(src("F21"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-13"])
        self.assertEqual(r["latest_date"], "2026-01-13")


# ---------------------------------------------------------------------------- changelog-versions (F29, GTM-77)

MUSE_URL = "https://dev.meta.ai/docs/muse-code/changelog"
MUSE_PAGE = """<html><body><nav>Changelog</nav><h1>Changelog</h1><p>What's new, improved, and fixed in each release.</p>
<h2 id="v1-4-13"><a href="#v1-4-13"><span>1.4.13</span></a></h2>
<h3>New</h3><ul><li>Permission profiles extending :ask-me now enforce filesystem deny rules</li></ul>
<h3>Improvements</h3><ul><li>muse usage shows your allowance</li></ul>
<h3>Fixes</h3><ul><li>Fixed CVE-2026-4242 in the MCP bridge</li></ul>
<h3>Performance</h3><ul><li>Faster startup</li></ul>
<h2 id="v1-4-12"><span>1.4.12</span></h2>
<h3>New</h3><ul><li>Older feature</li></ul>
</body></html>"""


class ChineseChangelogs(Base):
    """GTM-93: Chinese dates (TRAE CN, Qoder CN), «last updated» footers and a version index with one page per version
    (CodeBuddy CLI)."""

    def test_trae_cn_dates(self):
        page = ("<html><body><h2>2026 年 01 月 14 日（功能发布）</h2><p>TRAE v3.4.15 版本正式发布。</p><p>新增功能 支持登录。</p>"
                "<h2>2026 年 01 月 02 日（Hotfix）</h2><p>TRAE v3.4.14 版本正式发布。</p></body></html>")
        with self.web({"https://docs.trae.cn/ide/changelog": page}):
            r = collect.read_changelog_web(src("F32"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("v3.4.15", "2026-01-14"))
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-14"])

    def test_qoder_dates_and_version_line(self):
        page = "<html><body><p>2026年1月14日</p><h3>CLI 1.1.83</h3><p>修复 /resume。</p></body></html>"
        pages = {"https://changelog.qoder.cn/ide": "<html><body><p>moved</p></body></html>",
                 "https://changelog.qoder.cn/jetbrains": "<html><body><p>moved</p></body></html>",
                 "https://changelog.qoder.cn/cli": page}
        with self.web(pages):
            r = collect.read_changelog_web(src("F36"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("1.1.83", "2026-01-14"))

    def test_last_updated_footer_is_not_an_entry(self):
        lines = ["### 4.12.3 (2026-01-10)", "新增功能", "最后更新:", "2026-01-14", "Pager"]
        self.assertEqual([(e["date"], e["version"]) for e in collect.entries(lines)], [("2026-01-10", "4.12.3")])

    def test_codebuddy_cli_index_reads_version_pages(self):
        index = "<html><body><ul><li><p>v2.179.3 - 2026-01-14</p></li><li><p>v2.179.2 - 2026-01-02</p></li></ul></body></html>"
        ver = ("<html><body><p>Skip to content</p><p>CLI</p><h1>CodeBuddy Code v2.179.3 发布</h1><p>修复会话问题。</p>"
               "<p>最后更新:</p><p>2026-01-14</p><p>Pager</p></body></html>")
        ide = "<html><body><h3>4.12.3 (2026-01-13)</h3><p>新增功能 插件市场。</p><p>最后更新:</p><p>2026-01-14</p></body></html>"
        pages = {"https://www.codebuddy.cn/docs/cli/release-notes/README": index,
                 "https://www.codebuddy.cn/docs/cli/release-notes/v2.179.3": ver,
                 "https://www.codebuddy.cn/docs/ide/release-notes/release-notes": ide}
        with self.web(pages):
            r = collect.read_changelog_web(src("F35"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("v2.179.3", "2026-01-14"))
        self.assertEqual([(e["date"], e["version"]) for e in r["new"]], [("2026-01-14", "v2.179.3"), ("2026-01-13", "4.12.3")])
        self.assertTrue(r["new"][0]["text"].startswith("# CodeBuddy Code v2.179.3"))
        self.assertNotIn("Skip to content", r["new"][0]["text"])
        self.assertNotIn("Pager", r["new"][0]["text"])


class Gtm98Sources(Base):
    """GTM-98: Warp's calendar headings with a build in brackets, Perplexity's changelog filtered by «Comet» (title or
    the line under it) and read with curl."""

    def test_warp_calver_heading_with_build(self):
        page = ("# Changelog — 2026\n\n### 2026.01.14 (v0.2026.01.13.08.25)\n\n**Improvements**\n\n- Agents can read MCP prompts.\n\n"
                "### 2026.01.07 (v0.2026.01.06.08.29)\n\n**Bug fixes**\n\n- Fixed a crash.\n")
        with self.web({"https://docs.warp.dev/changelog/2026.md": page}):
            r = collect.read_changelog_web(src("F40"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"]), ("2026.01.14", "2026-01-14"))
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-14"])
        self.assertIn("MCP prompts", r["new"][0]["text"])

    PPLX = ("<html><body><p>What's new</p>"
            "<time datetime=\"2026-01-14\">01/14/26</time><time datetime=\"2026-01-14\">01/14/26</time>"
            "<h2>Teammates and Voice mode</h2><p>Hand off jobs to teammates and set Comet as the default browser.</p><p>See changes</p>"
            "<time datetime=\"2026-01-13\">01/13/26</time><h2>Comet for Android</h2><p>New mobile app.</p><p>See changes</p>"
            "<time datetime=\"2026-01-12\">01/12/26</time><h2>Decisions API</h2><p>Classify content.</p><p>See changes</p>"
            "<h3>Products</h3><p>Search</p><p>Comet</p><p>API</p></body></html>")

    def test_comet_entries_by_title_or_summary(self):
        with self.web({"https://www.perplexity.ai/changelog": self.PPLX}):
            r = collect.read_changelog_web(src("F43"), L, TERMS)
        self.assertTrue(r["opened"])
        self.assertEqual(self.clients, ["curl"])
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-14", "2026-01-13"])
        self.assertTrue(r["new"][0]["text"].startswith("## Teammates and Voice mode"))  # no "01/14/26" line
        self.assertNotIn("01/14/26", r["new"][0]["text"])

    def test_comet_footer_does_not_count(self):
        page = self.PPLX.replace("set Comet as the default browser", "share files").replace("Comet for Android", "Android app")
        with self.web({"https://www.perplexity.ai/changelog": page}):
            r = collect.read_changelog_web(src("F43"), L, TERMS)
        self.assertTrue(r["opened"])  # the page was read; nothing in it is about Comet
        self.assertEqual((r["new"], r["latest"], r["latest_date"]), ([], None, None))

    def test_codex_cloud_still_matches_only_title_and_labels(self):
        lines = ["2026-01-14", "## Codex app 26.114", "Codex Cloud tasks now resume after the app restarts on any computer.", "2026-01-13", "## Codex Cloud",
                 "Environments."]
        es = collect.entries(lines)
        self.assertEqual(es[0]["summary"], "Codex Cloud tasks now resume after the app restarts on any computer.")
        with self.web({"https://developers.openai.com/codex/changelog": "\n".join(lines)}):
            r = collect.read_changelog_web(src("F21"), L, TERMS)
        self.assertEqual([e["date"] for e in r["new"]], ["2026-01-13"])

    def test_curl_client(self):
        ok = mock.Mock(returncode=0, stdout=b"<html>ok</html>\n200")
        with mock.patch.object(collect.subprocess, "run", return_value=ok) as run:
            self.assertEqual(collect.http_get("https://www.perplexity.ai/changelog", "curl"), "<html>ok</html>")
        self.assertEqual(run.call_args[0][0][:2], ["curl", "-sS"])
        self.assertIn(collect.UA, run.call_args[0][0])
        bad = mock.Mock(returncode=0, stdout=b"denied\n403")
        with mock.patch.object(collect.subprocess, "run", return_value=bad), self.assertRaises(collect.ReadError):
            collect.http_get("https://www.perplexity.ai/changelog", "curl")


class ChangelogVersions(Base):
    def run_f29(self, previous, page=MUSE_PAGE):
        with mock.patch.dict(collect.PREVIOUS, previous, clear=True), self.web({MUSE_URL: page}):
            return collect.read_changelog_versions(src("F29"), L, TERMS)

    def test_first_time_only_notes_the_version(self):
        r = self.run_f29({})
        self.assertTrue(r["opened"])
        self.assertEqual((r["latest"], r["latest_date"], r["new"], r["ids"]), ("1.4.13", TODAY, [], []))
        self.assertIs(r["date_is_detection"], True)

    def test_nothing_new(self):
        r = self.run_f29({"F29": "1.4.13"})
        self.assertEqual((r["latest"], r["new"]), ("1.4.13", []))

    def test_new_version_with_its_notes(self):
        r = self.run_f29({"F29": "1.4.12"})
        self.assertEqual(len(r["new"]), 1)
        e = r["new"][0]
        self.assertEqual((e["date"], e["version"]), (TODAY, "1.4.13"))
        for part in ("New", "deny rules", "Improvements", "Fixes", "Performance", "Faster startup"):
            self.assertIn(part, e["text"])
        self.assertNotIn("Older feature", e["text"])
        self.assertEqual(r["ids"], ["CVE-2026-4242"])

    def test_highest_version_wins_wherever_it_is(self):
        page = MUSE_PAGE.replace("<span>1.4.12</span>", "<span>1.10.0</span>")
        r = self.run_f29({"F29": "1.4.13"}, page)
        self.assertEqual(r["latest"], "1.10.0")
        self.assertIn("Older feature", r["new"][0]["text"])

    def test_text_trimmed_to_600(self):
        r = self.run_f29({"F29": "1.4.12"}, MUSE_PAGE.replace("Faster startup", "x " * 700))
        self.assertLessEqual(len(r["new"][0]["text"]), 600)

    def test_page_without_versions_or_unreachable(self):
        self.assertFalse(self.run_f29({}, "<html><body><h1>Changelog</h1></body></html>")["opened"])
        with mock.patch.dict(collect.PREVIOUS, {}, clear=True), self.web({}):
            r = collect.read_changelog_versions(src("F29"), L, TERMS)
        self.assertFalse(r["opened"])
        self.assertIn("404", r["reason"])

    def test_previous_version_comes_from_the_newest_raw_file_with_f29(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "2026-01-12.json").write_text(json.dumps({"sources": [{"id": "F29", "latest": "1.4.11"}]}), encoding="utf-8")
            Path(d, "2026-01-13.json").write_text(json.dumps({"sources": [{"id": "F1", "latest": "2.1.0"}]}), encoding="utf-8")
            Path(d, "2026-01-15.json").write_text(json.dumps({"sources": [{"id": "F29", "latest": "9.9.9"}]}), encoding="utf-8")
            prev = collect.previous_versions(d, "2026-01-15")
        self.assertEqual(prev, {"F29": "1.4.11", "F1": "2.1.0"})


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

    def test_agent_platforms_match_and_generic_words_do_not(self):
        body = kev(("CVE-2026-11", "Langflow", "Langflow", "2026-01-13"),
                   ("CVE-2026-12", "IBM", "Langflow", "2026-01-13"),
                   ("CVE-2026-13", "n8n", "n8n", "2026-01-13"),
                   ("CVE-2026-14", "Ray-Project", "Ray", "2026-01-13"),
                   ("CVE-2026-21", "Veritas", "Backup Exec Agent", "2026-01-13"),
                   ("CVE-2026-22", "Exim", "Mail Transfer Agent (MTA)", "2026-01-13"),
                   ("CVE-2026-23", "Array Networks", "ArrayOS AG", "2026-01-13"),
                   ("CVE-2026-24", "DrayTek", "Vigor Routers", "2026-01-13"))
        with self.web({KEV_URL: body}):
            r = collect.read_kev(src("F28"), L, TERMS)
        self.assertEqual(r["ids"], ["CVE-2026-11", "CVE-2026-12", "CVE-2026-13", "CVE-2026-14"])
        self.assertEqual(src("F28")["read"]["products"],
                         ["MCP", "Langflow", "n8n", "Ray", "Dify", "Flowise", "Ollama", "LangChain"])

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
                         ("2026-01-15", "2026-01-15T05:30:00Z", len(IDS) - 1, len(IDS)))
        self.assertEqual([s["id"] for s in out["sources"]], IDS)
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

    def test_date_is_detection_in_schema(self):
        base = collect.blank(src("F1"), "curl") | {"opened": True}
        out = {"date": "2026-01-15", "collected_at": "2026-01-15T05:30:00Z", "opened": 29, "total": 29,
               "sources": [dict(base, id=f"F{i}") for i in range(1, 30)]}
        out["sources"][28]["date_is_detection"] = True
        self.assertEqual(errors(out), [])
        out["sources"][28]["date_is_detection"] = "yes"
        self.assertTrue(errors(out))

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
        self.assertEqual(ids, IDS)
        self.assertEqual(IDS[:29], [f"F{i}" for i in range(1, 30)])
        self.assertEqual(IDS[29:], ["F31", "F32", "F33", "F34", "F35", "F36", "F37", "F38", "F39", "F40", "F41", "F42", "F43"])
        for s in SOURCES["sources"]:
            self.assertEqual(set(s), {"id", "name", "scope", "method", "read", "public_url", "fragile", "notes"}, s["id"])
            self.assertIn(s["method"], collect.METHODS, s["id"])
            self.assertEqual(s["fragile"], s["id"] in ("F8", "F19", "F43"), s["id"])
            self.assertNotIn("raw.githubusercontent.com", s["public_url"], s["id"])
            if s["name"] not in ("Hermes Agent", "Muse Code", "n8n", "TRAE", "Qwen Code", "Kimi Code", "CodeBuddy", "Qoder CN",
                                 "Aider", "OpenHands", "Amp", "Warp", "Junie", "Kilo Code", "Comet"):
                self.assertEqual(s["public_url"], checked[s["name"]], s["id"])
        self.assertEqual(len(set(SOURCES["scope_terms"])), len(SOURCES["scope_terms"]))
        self.assertTrue({"muse", "n8n"} <= set(SOURCES["scope_terms"]))
        f31 = src("F31")
        self.assertEqual((f31["name"], f31["method"], f31["read"]["tags"], f31["fragile"]), ("n8n", "git-tags", "n8n@N.N.N", False))
        self.assertEqual(f31["read"]["notes"], ["github-api", {"web": "https://docs.n8n.io/release-notes/"}])
        self.assertIn("muse", SOURCES["scope_terms"])
        new = {s["id"]: s for s in SOURCES["sources"] if s["id"] in ("F32", "F33", "F34", "F35", "F36")}
        self.assertEqual({k: (v["name"], v["scope"], v["method"]) for k, v in new.items()}, {
            "F32": ("TRAE", "trae", "changelog-web"), "F33": ("Qwen Code", "qwen-code", "git-tags"),
            "F34": ("Kimi Code", "kimi-code", "git-tags"), "F35": ("CodeBuddy", "codebuddy", "changelog-web"),
            "F36": ("Qoder CN", "qoder-cn", "changelog-web")})
        self.assertEqual(new["F33"]["read"]["tags"], "v*")
        self.assertEqual(new["F34"]["read"]["tags"], "@moonshot-ai/kimi-code@N.N.N")
        for s in new.values():
            self.assertTrue((ROOT / "observatory" / "data" / "agents" / f"{s['scope']}.json").is_file(), s["id"])
            self.assertTrue(daily_check.host_allowed(s["public_url"]), s["id"])
        gtm98 = {s["id"]: s for s in SOURCES["sources"] if s["id"] in [f"F{i}" for i in range(37, 44)]}
        self.assertEqual({k: (v["name"], v["scope"], v["method"]) for k, v in gtm98.items()}, {
            "F37": ("Aider", "aider", "git-tags"), "F38": ("OpenHands", "openhands", "git-tags"),
            "F39": ("Amp", "amp", "changelog-web"), "F40": ("Warp", "warp", "changelog-web"),
            "F41": ("Junie", "junie", "changelog-web"), "F42": ("Kilo Code", "kilo-code", "git-tags"),
            "F43": ("Comet", "comet", "changelog-web")})
        f43 = gtm98["F43"]["read"]
        self.assertEqual((f43["only_entries_with"], f43["match_summary"], f43["client"]), ("Comet", True, "curl"))
        self.assertIn("only entries whose title, or the line under the title, contains «Comet»", gtm98["F43"]["notes"])
        for s in gtm98.values():
            self.assertTrue((ROOT / "observatory" / "data" / "agents" / f"{s['scope']}.json").is_file(), s["id"])
            self.assertTrue(daily_check.host_allowed(s["public_url"]), s["id"])
        f29 = SOURCES["sources"][28]
        self.assertEqual((f29["name"], f29["method"], f29["fragile"]), ("Muse Code", "changelog-versions", False))
        self.assertEqual(f29["public_url"], f29["read"]["url"])


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
