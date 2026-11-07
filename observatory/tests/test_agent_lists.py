"""Tests for observatory/agent_lists.py (GTM-99): one source for the agent lists and the checks a-d that block the deploy.

Run from the repository root:  python3 -m unittest observatory/tests/test_agent_lists.py
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

OBS = Path(__file__).resolve().parents[1]
ROOT = OBS.parent
sys.path.insert(0, str(OBS))
import agent_lists as al  # noqa: E402
import daily_alert  # noqa: E402


def agent(i, name, status="not_supported", since=None):
    r = {"status": status}
    if since:
        r["since_version"] = since
    return {"id": i, "name": name, "rosmarops": r}


AGENTS = [agent("claude-code", "Claude Code", "evaluated", "0.1.0"), agent("cursor", "Cursor", "evaluated", "0.1.0"),
          agent("hermes-agent", "Hermes Agent", "evaluated", "0.5.2"), agent("codex", "Codex", "detected", "0.3.0"),
          agent("cline", "Cline", "detected", "0.1.0"), agent("aider", "Aider")]
PROGRAM = {"knowledge_to_file": {"claude-code": "claude-code", "cursor": "cursor", "hermes": "hermes-agent", "codex": "codex"},
           "not_agents": ["mcp_catalog"]}


def page_with(text):
    return f"<html><head><meta name=\"description\" content=\"{text}\"></head><body>{text}</body></html>"


class Lists(unittest.TestCase):
    def test_order_and_join(self):
        self.assertEqual(al.names(AGENTS, "scored"), ["Claude Code", "Cursor", "Hermes Agent"])
        self.assertEqual(al.names(AGENTS, "detected"), ["Cline", "Codex"])
        self.assertEqual(al.join(["A", "B", "C"], "en"), "A, B and C")
        self.assertEqual(al.join(["A", "B", "C"], "es"), "A, B y C")
        self.assertEqual(al.join(["A", "B"], "ca"), "A i B")
        with self.assertRaises(ValueError):  # a singular sentence is a wording change: not generated
            al.join(["A"], "en")

    def test_scored_list_names_per_language(self):
        agents = AGENTS + [agent("github-copilot", "GitHub Copilot", "evaluated", "0.9.0")]
        names = {"github-copilot": {"en": "GitHub Copilot in VS Code", "es": "GitHub Copilot en VS Code", "ca": "GitHub Copilot a VS Code"}}
        self.assertEqual(al.names(agents, "scored", "es", names)[-1], "GitHub Copilot en VS Code")
        self.assertEqual(al.names(agents, "scored", "ca", names)[-1], "GitHub Copilot a VS Code")
        self.assertEqual(al.names(agents, "scored", "en", {})[-1], "GitHub Copilot")
        detected = [agent("github-copilot", "GitHub Copilot", "detected", "0.1.0"), agent("cline", "Cline", "detected", "0.1.0")]
        self.assertEqual(al.names(detected, "detected", "es", names), ["Cline", "GitHub Copilot"])  # only the scored list
        signed = al.list_names()["github-copilot"]
        self.assertEqual(signed, names["github-copilot"])

    def test_render_sentence_chips_and_mirrors(self):
        old = ("<html><head><meta name=\"description\" content=\"today Claude Code and Cursor\">"
               "<script type=\"application/ld+json\">{\"description\": \"(today Claude Code and Cursor)\"}</script></head><body>"
               "<p>Today it evaluates <!-- agents:scored -->Claude Code and Cursor<!-- /agents:scored --> on Windows.</p>"
               "<div class=\"row\"><span class=\"lab\">Detects</span><!-- agents:detected chips --><span class=\"chip\">Cline</span>"
               "<!-- /agents:detected --></div></body></html>")
        new = al.render_text(old, "en", AGENTS, "site/x.html")
        self.assertIn("Today it evaluates <!-- agents:scored -->Claude Code, Cursor and Hermes Agent<!-- /agents:scored --> on Windows.", new)
        self.assertIn('<!-- agents:detected chips --><span class="chip">Cline</span><span class="chip">Codex</span><!-- /agents:detected -->', new)
        self.assertIn('content="today Claude Code, Cursor and Hermes Agent"', new)  # mirrors change with the list
        self.assertIn('(today Claude Code, Cursor and Hermes Agent)', new)
        self.assertEqual(al.render_text(new, "en", AGENTS, "site/x.html"), new)  # idempotent


class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    # a
    def test_a_candidates(self):
        self.assertEqual(al.check_candidates(AGENTS, [{"name": "Manus", "vendor": "Manus AI", "reason": "no_source"}]), [])
        errs = al.check_candidates(AGENTS, [{"name": "aider", "vendor": "x", "reason": "next_batch"}])
        self.assertEqual(errs, ["candidates.json: aider has an agent file"])

    # b
    def test_b_scored_equals_release(self):
        self.assertEqual(al.check_scored(AGENTS, ["claude-code", "cursor", "hermes", "mcp_catalog"], PROGRAM), [])

    def test_b_new_knowledge_file(self):
        errs = al.check_scored(AGENTS, ["claude-code", "cursor", "hermes", "codex", "grok-build"], PROGRAM)
        self.assertIn("codex is scored in the program's release but not evaluated in its agent file", errs)
        self.assertIn("knowledge file grok-build.json has no entry in program-agents.json", errs)

    def test_b_no_longer_scored(self):
        errs = al.check_scored(AGENTS, ["claude-code", "cursor"], PROGRAM)
        self.assertEqual(errs, ["hermes-agent is evaluated in its agent file but has no knowledge file in the program's release"])

    # c
    def sample(self, version, en=b"en", es=b"es"):
        d = self.tmp / "sample"
        d.mkdir(exist_ok=True)
        (d / "VERSION").write_text(version + "\n")
        (d / "sample-report.en.html").write_bytes(en)
        (d / "sample-report.es.html").write_bytes(es)
        return d

    def test_c_sample_is_the_release(self):
        d = self.sample("v0.8.0")
        dig = {"sample-report.en.html": hashlib.sha256(b"en").hexdigest(), "sample-report.es.html": hashlib.sha256(b"es").hexdigest()}
        self.assertEqual(al.check_sample("v0.8.0", dig, d), [])

    def test_c_sample_is_old(self):
        d = self.sample("v0.7.0", en=b"old")
        dig = {"sample-report.en.html": hashlib.sha256(b"en").hexdigest()}
        errs = al.check_sample("v0.8.0", dig, d)
        self.assertEqual(errs, ["site/sample-report/VERSION is v0.7.0, the latest release is v0.8.0",
                                "site/sample-report/sample-report.en.html is not the one in release v0.8.0",
                                "release v0.8.0 has no sample-report.es.html"])

    # d
    def pages(self, body):
        for page in al.PAGES:
            f = self.tmp / page
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body.get(page, "<html><body><p>Nothing.</p></body></html>"), encoding="utf-8")

    def test_d_generated_mirror_and_exclusion_pass(self):
        self.pages({
            "site/faq/index.html": page_with("Today it evaluates <!-- agents:scored -->Claude Code, Cursor and Hermes Agent"
                                             "<!-- /agents:scored -->.").replace(
                'content="Today it evaluates <!-- agents:scored -->Claude Code, Cursor and Hermes Agent<!-- /agents:scored -->."',
                'content="Today it evaluates Claude Code, Cursor and Hermes Agent."'),
            "site/llms.txt": "- [RosmarOps 0.3.0](x): detects Codex and Cline\n",
        })
        excl = [{"page": "site/llms.txt", "contains": "[RosmarOps 0.3.0](", "reason": "post title"}]
        self.assertEqual(al.check_pages(AGENTS, excl, self.tmp), [])

    def test_d_list_outside_markers_fails(self):
        self.pages({"site/es/index.html": "<html><body><p>Hoy evalúa Claude Code y Cursor.</p>"
                                          "<div class=\"row\"><span class=\"chip\">Cline</span><span class=\"chip\">Codex</span></div></body></html>",
                    "site/llms.txt": "- [RosmarOps 0.3.0](x): detects Codex and Cline\n"})
        errs = al.check_pages(AGENTS, [], self.tmp)
        self.assertEqual([e.split(":")[0] for e in errs], ["site/es/index.html", "site/es/index.html", "site/llms.txt"], errs)

    def test_d_same_list_without_markers_fails_in_the_body(self):
        # Even the right list counts: visible lists live between markers, only the meta and JSON-LD hold copies.
        self.pages({"site/es/index.html": "<html><body><p>Hoy evalúa Claude Code, Cursor y Hermes Agent.</p></body></html>"})
        self.assertEqual(len(al.check_pages(AGENTS, [], self.tmp)), 1)

    def test_d_stale_mirror_fails(self):
        self.pages({"site/index.html": "<html><head><meta name=\"description\" content=\"today Claude Code and Cursor\"></head>"
                                       "<body><p><!-- agents:scored -->Claude Code, Cursor and Hermes Agent<!-- /agents:scored --></p></body></html>"})
        self.assertEqual(len(al.check_pages(AGENTS, [], self.tmp)), 1)

    # release
    def test_release_sets_scored_and_reports(self):
        folder = self.tmp / "observatory" / "data" / "agents"
        folder.mkdir(parents=True)
        for a in AGENTS:
            (folder / f"{a['id']}.json").write_text(json.dumps({"schema_version": 1, "agent": a}), encoding="utf-8")
        (self.tmp / "observatory" / "data" / "program-agents.json").write_text(json.dumps(PROGRAM), encoding="utf-8")
        notes = al.release("v0.8.0", ["claude-code", "codex", "cursor", "grok-build", "mcp_catalog"], self.tmp)
        self.assertIn("codex: now evaluated since 0.8.0", notes)
        self.assertIn("needs Albert: knowledge file grok-build.json has no agent file mapped in program-agents.json", notes)
        self.assertIn("needs Albert: hermes-agent is evaluated but has no knowledge file in v0.8.0; left as it is", notes)
        codex = json.loads((folder / "codex.json").read_text())["agent"]["rosmarops"]
        self.assertEqual(codex, {"status": "evaluated", "since_version": "0.8.0"})


class Repository(unittest.TestCase):
    """The repository as committed: lists rendered, no list outside the markers, candidates and scored set right."""

    def test_pages_are_rendered(self):
        agents = al.load_agents()
        for page, lang in al.PAGES.items():
            text = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn("<!-- agents:scored", text, page)
            self.assertEqual(al.render_text(text, lang, agents, page), text, f"{page}: run python3 observatory/build.py")

    def test_no_list_outside_markers(self):
        excl = json.loads((OBS / "data" / "agent-list-exclusions.json").read_text(encoding="utf-8"))
        self.assertEqual(al.check_pages(al.load_agents(), excl), [])
        for e in excl:
            self.assertIn(e["contains"], (ROOT / e["page"]).read_text(encoding="utf-8"), e)
            self.assertTrue(e["reason"])

    def test_candidates_and_program_map(self):
        agents = al.load_agents()
        self.assertEqual(al.check_candidates(agents, json.loads((OBS / "data" / "candidates.json").read_text(encoding="utf-8"))), [])
        program = json.loads((OBS / "data" / "program-agents.json").read_text(encoding="utf-8"))
        # v0.8.0 (07-11): internal/knowledge/ has claude-code, codex, cursor, grok-build, hermes and mcp_catalog.
        self.assertEqual(al.check_scored(agents, ["antigravity-cli", "claude-code", "codex", "cursor", "github-copilot", "grok-build", "hermes", "mcp_catalog"], program), [])


class FocoAlert(unittest.TestCase):
    def test_problems_give_one_foco_message(self):
        report = "::error::site/faq/index.html: list of agents outside the markers: «x»\nagent lists: 1 problem(s) against qtorb/rosmarops v0.8.0\n"
        msgs = daily_alert.for_consistency("2026-11-07", report)
        self.assertEqual(len(msgs), 1)
        body = msgs[0]["TextBody"].splitlines()
        self.assertTrue(body[0].startswith("FOCO: "))
        self.assertIn("- site/faq/index.html: list of agents outside the markers: «x»", body)
        self.assertEqual(msgs[0]["To"], "albert@rosmarops.com")

    def test_clean_report_gives_none(self):
        self.assertEqual(daily_alert.for_consistency("2026-11-07", "agent lists: 0 problem(s) against qtorb/rosmarops v0.8.0\n"), [])

    def test_unreadable_release_alerts(self):
        msgs = daily_alert.for_consistency("2026-11-07", "FAIL cannot read the latest release of qtorb/rosmarops: HTTP 403\n")
        self.assertEqual(len(msgs), 1)


if __name__ == "__main__":
    unittest.main()
