"""GTM-175: the «Sandbox» section (/sandbox/), its templates (schema v1.13) and the watch of their pages."""
import html
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import collect  # noqa: E402
import daily_alert  # noqa: E402
import sandbox_section  # noqa: E402

AGENTS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "observatory/data/agents").glob("*.json"))]
BY_ID = {a["agent"]["id"]: a for a in AGENTS}
SOURCES = json.loads((ROOT / "observatory/sources.json").read_text(encoding="utf-8"))["sources"]
T = sandbox_section.texts()
LANGS = ("en", "es", "ca")
SYSTEMS = ("windows", "macos", "linux")
FORBIDDEN = re.compile(r"\b(seguro|segura|protege|a salvo|sin riesgo|safe|safely|protects|risk-free|segur|protegeix|sense risc)\b", re.I)
EVALUATED = {"claude-code", "cursor", "codex", "grok-build", "hermes-agent", "github-copilot", "gemini-cli",
             "antigravity-cli", "cline"}
# GTM-175 §1: the session command only here.
SESSION = {("claude-code", "macos"), ("claude-code", "linux"), ("codex", "windows"), ("codex", "macos"), ("codex", "linux"),
           ("grok-build", "macos"), ("grok-build", "linux"), ("antigravity-cli", "macos"), ("antigravity-cli", "linux")}
SEPARATE = {("cline", s) for s in SYSTEMS} | {(a, "windows") for a in ("claude-code", "cursor", "grok-build")}


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S)))


def page(lang, review=frozenset()):
    return sandbox_section.page(lang, AGENTS, set(review))


class Data(unittest.TestCase):
    def test_the_nine_evaluated_agents_have_templates(self):
        self.assertEqual({a["agent"]["id"] for a in AGENTS if a.get("templates")}, EVALUATED)

    def test_kinds_and_measure(self):
        for a in AGENTS:
            for s, t in (a.get("templates") or {}).items():
                key = (a["agent"]["id"], s)
                self.assertEqual(t["kind"] == "separate_account", key in SEPARATE, key)
                self.assertEqual(t["kind"] == "container", key[0] == "hermes-agent", key)
                self.assertEqual(t["measure"], "guided", key)  # GTM-175 §4: until profile-scores.json brings P2
                if t["kind"] == "separate_account":
                    self.assertEqual((t["blocks"], t["uncovered"], t["covers"]),
                                     ([], [], {"sandbox": False, "read_limit": "unknown", "network_cut": "no"}), key)

    def test_session_only_where_signed(self):
        got = {(a["agent"]["id"], s) for a in AGENTS for s, t in (a.get("templates") or {}).items() if "session" in t}
        self.assertEqual(got, SESSION)
        cc = BY_ID["claude-code"]["templates"]["linux"]["session"]
        self.assertIn("/RUTA/DEL/PROYECTO", cc["command"])
        self.assertEqual(cc["requires"], ["bubblewrap_socat"])
        self.assertEqual(BY_ID["codex"]["templates"]["windows"]["session"]["requires"], ["windows_11_24h2_25h2"])
        self.assertEqual(BY_ID["grok-build"]["templates"]["linux"]["session"]["requires"], ["linux_5_13"])
        requires = {c for a in AGENTS for t in (a.get("templates") or {}).values() if "session" in t for c in t["session"]["requires"]}
        self.assertEqual(requires, {"bubblewrap_socat", "windows_11_24h2_25h2", "linux_5_13"})  # GTM-175 §5

    def test_every_code_has_its_three_texts_and_every_text_is_used(self):
        used = {c for a in AGENTS for t in (a.get("templates") or {}).values() for c in t["uncovered"]}
        for lang in LANGS:
            have = {k.split(".", 1)[1] for k in T[lang] if k.startswith("uncovered.") and k != "uncovered.h"}
            self.assertEqual(have, used, lang)
        self.assertEqual(len(used), 31)
        self.assertNotIn("project_edits_without_asking", used)  # GTM-175 §6
        self.assertNotIn("mcp_read_url_browser_by_rules", used)
        self.assertEqual(set(T["en"]), set(T["es"]))
        self.assertEqual(set(T["en"]), set(T["ca"]))

    def test_uncovered_per_system(self):
        u = lambda a, s: BY_ID[a]["templates"][s]["uncovered"]
        self.assertNotIn("deny_read_fixed_at_start", u("codex", "macos"))
        self.assertIn("deny_read_fixed_at_start", u("codex", "linux"))
        self.assertIn("network_cut_noop_macos", u("grok-build", "macos"))
        self.assertNotIn("network_cut_noop_macos", u("grok-build", "linux"))
        self.assertEqual(u("cursor", "linux")[-1], "linux_needs_landlock_v3")
        self.assertIn("windows_outside_profile_readable", u("antigravity-cli", "windows"))
        self.assertIn("needs_docker", u("gemini-cli", "linux"))
        self.assertIn("macos_proxy_undocumented", u("gemini-cli", "macos"))

    def test_covers_from_the_advisor_table(self):
        c = lambda a, s: tuple(BY_ID[a]["templates"][s]["covers"].values())
        self.assertEqual(c("claude-code", "macos"), (True, "workspace", "allowlist"))
        self.assertEqual(c("grok-build", "macos"), (True, "workspace", "no"))
        self.assertEqual(c("grok-build", "linux"), (True, "workspace", "yes"))
        self.assertEqual(c("antigravity-cli", "windows"), (True, "listed_paths", "yes"))
        self.assertEqual(c("gemini-cli", "windows"), (True, "unknown", "unknown"))
        self.assertEqual(c("hermes-agent", "linux"), (True, "unknown", "yes"))

    def test_sources_json_watches_every_template_page(self):
        want = sandbox_section.watch_map(AGENTS)
        got = {s["read"]["url"]: s["read"]["watch"] for s in SOURCES if "watch" in s.get("read", {})}
        self.assertEqual(got, want)
        for s in SOURCES:
            if "watch" in s.get("read", {}):
                self.assertEqual(s["method"], "page-watch", s["id"])


class Page(unittest.TestCase):
    def test_one_card_per_agent_in_the_observatory_order(self):
        for lang in LANGS:
            p = page(lang)
            ids = re.findall(r'<section class="tb" id="([a-z-]+)"', p)
            self.assertEqual(ids, [a["agent"]["id"] for a in sandbox_section.with_templates(AGENTS)], lang)
            self.assertEqual(len(ids), 9)

    def test_signed_texts_and_no_forbidden_word(self):
        for lang in LANGS:
            p = page(lang)
            body = text(p[p.index("<main"):p.index("</main>")])
            self.assertFalse(FORBIDDEN.search(body), lang)
            for k in ("title", "lead", "which.h", "which.p", "on.h", "on.p", "apart.h", "apart.p", "then.h", "then.p", "note"):
                self.assertIn(T[lang][k], body, (lang, k))
            self.assertNotIn(T[lang]["example.h"], body)  # §2.3: no sandbox-example.json in any release yet
            self.assertIn(f'href="/{"" if lang == "en" else lang + "/"}sandbox/" aria-current="page">Sandbox</a>', p)
            self.assertIn("from=sandbox&amp;os=store", p)
        for lang in LANGS:
            for k, v in T[lang].items():
                self.assertFalse(FORBIDDEN.search(v), (lang, k))

    def test_claude_code_card(self):
        p = page("es")
        card = p[p.index('id="claude-code"'):p.index("</section>", p.index('id="claude-code"'))]
        self.assertIn("// ~/.claude/settings.json", card)
        self.assertIn("// .claude/settings.json", card)
        self.assertIn(html.escape(T["es"]["paste.many"].replace("{agent}", "Claude Code"), quote=True), card)
        self.assertIn("<summary>Probar solo esta vez</summary>", card)
        self.assertIn("Linux:</span> Necesita: bubblewrap y socat.", card)
        self.assertIn(T["es"]["session.path"], card)
        self.assertIn("<code>excludedCommands</code>", card)
        self.assertIn("En Windows, Claude Code no tiene sandbox", card)

    def test_cline_is_the_other_account_in_both_blocks(self):
        for lang in LANGS:
            p = page(lang)
            card = p[p.index('id="cline"'):p.index("</section>", p.index('id="cline"'))]
            self.assertEqual(card.count("<pre"), 0)
            self.assertNotIn(T[lang]["uncovered.h"], card)
            self.assertEqual(text(card).count(T[lang]["separate_account"].split("{agent}")[1].split(":")[0]), 2)

    def test_copilot_cursor_gemini_and_codex(self):
        p = page("en")
        card = lambda aid: p[p.index(f'id="{aid}"'):p.index("</section>", p.index(f'id="{aid}"'))]
        self.assertIn(T["en"]["paste.vscode"], card("github-copilot"))
        self.assertIn(html.escape(T["en"]["ui.cursor_allowlist_sandbox"], quote=True), card("cursor"))
        self.assertIn(html.escape(T["en"]["env.gemini_macos"], quote=True), card("gemini-cli"))
        self.assertIn("SEATBELT_PROFILE=strict-proxied gemini", card("gemini-cli"))
        self.assertIn("Linux:</span> " + html.escape(T["en"]["uncovered.deny_read_fixed_at_start"], quote=True), card("codex"))
        self.assertIn('sandbox = &quot;mxc&quot;', card("codex"))
        self.assertIn("Needs: Windows 11 24H2 or 25H2.", card("codex"))
        self.assertNotIn("macOS:</span> On macOS", card("grok-build"))  # the text already says its system

    def test_to_review_shows_on_the_cards_of_that_page(self):
        url = "https://docs.x.ai/build/features/sandbox.md"
        p = page("es", {url})
        self.assertEqual(p.count(T["es"]["review"]), 2)  # Grok Build: macOS and Linux block, and Windows (other account)
        self.assertNotIn(T["es"]["review"], page("es"))

    def test_review_from_the_latest_raw_file(self):
        fid = next(s["id"] for s in SOURCES if s.get("read", {}).get("url") == "https://cursor.com/docs/reference/sandbox.md")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "2026-11-16.json").write_text(json.dumps({"sources": [{"id": fid, "missing": ["networkPolicy"]}]}))
            (Path(d) / "2026-11-15.json").write_text(json.dumps({"sources": [{"id": "F48", "missing": ["x"]}]}))
            self.assertEqual(sandbox_section.to_review(d), {"https://cursor.com/docs/reference/sandbox.md"})
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sandbox_section.to_review(d), set())

    def test_links_to_the_section(self):
        site = ROOT / "site"
        for lang, guide, gloss, cmp_ in (("es", "es/probar-un-agente-de-ia", "es/glosario", "es/observatorio/agentes-ia-con-sandbox"),
                                         ("en", "try-an-ai-agent", "glossary", "observatory/ai-agents-with-sandbox"),
                                         ("ca", "ca/provar-un-agent-dia", "ca/glossari", "ca/observatori/agents-ia-amb-sandbox")):
            link = f'<a href="{sandbox_section.SECTION_PATH[lang]}">{html.escape(T[lang]["all_about"], quote=False)}</a>'
            for f in (guide, gloss, cmp_, {"es": "es/observatorio", "en": "observatory", "ca": "ca/observatori"}[lang]):
                self.assertIn(link, (site / f / "index.html").read_text(encoding="utf-8"), (lang, f))
            ficha = (site / {"es": "es/observatorio", "en": "observatory", "ca": "ca/observatori"}[lang] / "claude-code" / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'<a href="{sandbox_section.SECTION_PATH[lang]}#claude-code">{html.escape(T[lang]["its_template"], quote=False)}</a>', ficha)


class Watch(unittest.TestCase):
    def src(self, url):
        return next(s for s in SOURCES if s.get("read", {}).get("url") == url)

    def test_strings_found_through_markup_and_markdown(self):
        body = ("<html><body><p>The sandbox covers <b>shell</b> commands only.</p><p>start Claude Code with "
                "<code>--settings</code></p><p>It doesn&#x27;t stop the Read tool</p></body></html>")
        self.assertEqual(collect.missing_strings(body, ["The sandbox covers shell commands only", "start Claude Code with --settings",
                                                        "doesn't stop the Read tool", "socat"]), ["socat"])
        md = "Domains allowed under `read_url` are added to the sandbox’s outbound allowlist. Set `default_permissions`."
        self.assertEqual(collect.missing_strings(md, ["are added to the sandbox's outbound allowlist", "default_permissions"]), [])

    def test_a_template_source_reports_missing_not_watched(self):
        s = self.src("https://cursor.com/docs/reference/sandbox.md")
        with mock.patch.object(collect, "http_get", return_value="# Sandbox\n\nreadBoundary: workspace\n"):
            r = collect.collect_source(s, "2026-11-15", [])
        self.assertTrue(r["opened"])
        self.assertEqual(r["missing"], ["networkPolicy"])
        self.assertNotIn("watched", r)
        self.assertEqual(r["new"], [])

    def test_raw_schema_takes_missing(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema not installed (CI installs it)")
        schema = json.loads((ROOT / "observatory/schema/raw.v1.schema.json").read_text(encoding="utf-8"))
        src = {"id": "F61", "opened": True, "reason": None, "latest": None, "latest_date": None, "new": [], "ids": [],
               "read_with": "curl", "missing": ["docker_network"]}
        base = dict(src, missing=[])
        raw = {"date": "2026-11-17", "collected_at": "2026-11-17T05:30:00Z", "opened": 60, "total": 60,
               "sources": [dict(base, id=f"F{i}") for i in range(1, 61) if i != 43] + [src]}
        self.assertEqual([e.message for e in Draft202012Validator(schema).iter_errors(raw)], [])

    def test_alert_names_the_page_and_the_strings(self):
        fid = self.src("https://code.claude.com/docs/en/sandboxing")["id"]
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "2026-11-17.json").write_text(json.dumps({"sources": [{"id": fid, "missing": ["socat"]}, {"id": "F1"}]}))
            msgs = daily_alert.for_templates("2026-11-17", d)
            self.assertEqual(len(msgs), 1)
            self.assertIn("https://code.claude.com/docs/en/sandboxing", msgs[0]["TextBody"])
            self.assertIn("«socat»", msgs[0]["TextBody"])
            (Path(d) / "2026-11-17.json").write_text(json.dumps({"sources": [{"id": fid, "missing": []}]}))
            self.assertEqual(daily_alert.for_templates("2026-11-17", d), [])


if __name__ == "__main__":
    unittest.main()
