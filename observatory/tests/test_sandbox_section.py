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


G = sandbox_section.gtexts()
# GTM-182: Claude Code's read test on macOS and Linux, the command the lab checked (release lab-20261118-2).
CC_READ = "python3 -c \"import os; print(sorted(os.listdir(os.path.expanduser('~'))))\""
LAB = [  # a test manifest (GTM-176 §5): never published; the real one comes from BV-250
    {"agent": "claude-code", "system": "macos", "step": 1, "test": "read", "when": "antes", "command": CC_READ, "result": "concluyente",
     "agent_version": "2.1.330", "os_version": "26.1", "date": "2026-11-20", "file": "claude-code-macos-1-read-antes.png", "sha256": "0" * 64},
    {"agent": "claude-code", "system": "macos", "step": 3, "test": "read", "when": "despues", "command": CC_READ, "result": "no_concluyente",
     "agent_version": "2.1.330", "os_version": "26.1", "date": "2026-11-20", "file": "x.png", "sha256": "0" * 64},
    {"agent": "codex", "system": "macos", "step": 3, "test": "read", "when": "despues", "command": "ls ~", "result": "concluyente",
     "agent_version": "0.140.0", "os_version": "26.1", "date": "2026-11-21", "file": "codex-macos-3-read-despues.png", "sha256": "0" * 64},
]


def combo(p, cid):
    i = p.index(f'id="{cid}"')
    return p[i:p.index("</section>", i)]


class Page(unittest.TestCase):
    def test_every_combination_once_in_the_observatory_order(self):
        for lang in LANGS:
            p = page(lang)
            ids = re.findall(r'<section class="sg-combo" id="([a-z-]+)"', p)
            want = [f'{a["agent"]["id"]}-{s}' for a in sandbox_section.with_templates(AGENTS) for s in SYSTEMS]
            self.assertEqual(ids, want, lang)
            for a in sandbox_section.with_templates(AGENTS):  # «Su plantilla de sandbox» of each agent page lands here
                self.assertIn(f'<span class="sg-anchor" id="{a["agent"]["id"]}"></span>', p)

    def test_signed_texts_and_no_forbidden_word(self):
        for lang in LANGS:
            p = page(lang)
            body = text(p[p.index("<main"):p.index("</main>")])
            self.assertFalse(FORBIDDEN.search(body), lang)
            # GTM-194: the lead is the catalog's sandbox.lead; «¿Qué es un sandbox?» became «Por qué encenderlo».
            for k in ("h1", "sel.agent", "sel.system", "sel.picked", "sel.choose", "pick_line", "none.1", "none.2", "none.3",
                      "side.which.link", "side.try.link"):
                self.assertIn(G[lang][k], body, (lang, k))
            self.assertIn(sandbox_section.ctexts(lang)["lead"], body)
            self.assertNotIn(G[lang]["side.what.h"], body)
            self.assertIn(T[lang]["note"], body)
            self.assertIn(f'href="/{"" if lang == "en" else lang + "/"}sandbox/" aria-current="page">Sandbox</a>', p)
            self.assertIn('<div class="sg-sel" hidden>', p)  # without JavaScript the selector does not show
        for lang in LANGS:
            for k, v in G[lang].items():
                self.assertFalse(FORBIDDEN.search(v), (lang, k))

    def test_texts_in_three_languages(self):
        self.assertEqual(set(G["en"]), set(G["ca"]))
        self.assertEqual(set(G["es"]), set(G["en"]))
        used = {c for a in AGENTS for t in (a.get("templates") or {}).values() for c in t.get("checks", {}).get("troubleshoot", [])}
        self.assertEqual({k[3:] for k in G["es"] if k.startswith("ts.")}, used)

    def test_checks_from_cto_61(self):
        c = lambda a, s: BY_ID[a]["templates"][s].get("checks")
        self.assertEqual(c("claude-code", "macos")["network"], {"kind": "cmd", "cmd": "git ls-remote https://example.com", "status": "confirmed"})
        self.assertEqual(c("codex", "windows")["read"]["cmd"], "dir ~")
        self.assertEqual(c("codex", "linux")["network"]["status"], "before_also_fails")
        self.assertEqual(c("grok-build", "macos")["network"]["status"], "works_by_design")
        self.assertEqual(c("github-copilot", "linux")["read"]["kind"], "copilot_policy")
        self.assertEqual(c("gemini-cli", "linux")["read"]["kind"], "hostname")
        self.assertEqual((c("gemini-cli", "windows")["read"]["kind"], c("gemini-cli", "windows")["network"]["kind"]), ("none", "none"))
        self.assertEqual(c("antigravity-cli", "windows")["read"]["cmd"], "dir ~")
        self.assertIsNone(c("cline", "macos"))
        self.assertIsNone(c("claude-code", "windows"))
        self.assertEqual(c("claude-code", "linux")["troubleshoot"], ["cc_version", "cc_linux_deps", "cc_sandbox_cmd", "cc_status"])
        self.assertEqual(c("claude-code", "macos")["troubleshoot"], ["cc_version", "cc_sandbox_cmd", "cc_status"])
        self.assertEqual(c("github-copilot", "windows")["troubleshoot"], ["copilot_new_session", "copilot_toggle", "copilot_windows"])

    def test_claude_code_macos(self):
        cc = combo(page("es"), "claude-code-macos")
        self.assertIn("<strong>Claude Code en macOS</strong> tiene sandbox, pero viene apagado. La plantilla lo enciende.", cc)
        self.assertIn("<code>Ejecuta git ls-remote https://example.com</code>", cc)
        self.assertIn(G["es"]["now.network_git"], cc)
        self.assertIn(G["es"]["note.cc_allowlist_open"], cc)
        self.assertIn("Copiar la plantilla", cc)
        self.assertIn("(~/.claude/settings.json)", cc)  # GTM-179: one text, paste.one
        self.assertIn(G["es"]["fold.session"], cc)
        self.assertIn("Lo que el sandbox no cubre en Claude Code (5)", cc)
        self.assertIn("<code>claude --version</code>", cc)
        self.assertNotIn("bubblewrap y socat instalados", cc)  # cc_linux_deps is Linux only
        self.assertIn("bubblewrap y socat instalados", combo(page("es"), "claude-code-linux"))
        self.assertNotIn(G["es"]["after.unconfirmed"], cc)

    def test_variants(self):
        p = page("es")
        cx = combo(p, "codex-windows")
        self.assertIn(G["es"]["now.before_also_fails"].replace("{agent}", "Codex"), cx)
        self.assertIn(G["es"]["after.before_also_fails"].replace("{agent}", "Codex"), cx)
        self.assertIn(G["es"]["after.unconfirmed"], cx)
        self.assertIn("<code>Ejecuta dir ~</code>", cx)
        gk = combo(p, "grok-build-macos")
        self.assertIn(G["es"]["after.works_by_design"].replace("{system}", "macOS"), gk)
        gw = combo(p, "gemini-cli-windows")
        self.assertEqual(gw.count(G["es"]["no_test"].replace("{agent}", "Gemini CLI").replace("{system}", "Windows")), 2)  # step 1 and 3
        self.assertIn(G["es"]["status.gemini_replaced"], gw)
        cp = combo(p, "github-copilot-macos")
        self.assertIn("<code>/sandbox policy</code>", cp)
        self.assertIn(html.escape(T["es"]["paste.vscode"], quote=True), cp)
        self.assertNotIn("Copiar la plantilla", cp)
        ag = combo(p, "antigravity-cli-linux")
        self.assertIn(f'<p>{G["es"]["s3.p_agy"]}</p>', ag)
        self.assertIn(G["es"]["note.agy_ask_means_off"], ag)
        cu = combo(p, "cursor-linux")
        self.assertIn(html.escape(T["es"]["ui.cursor_allowlist_sandbox"], quote=True), cu)
        gm = combo(p, "gemini-cli-macos")
        self.assertIn(html.escape(T["es"]["env.gemini_macos"], quote=True), gm)
        he = combo(p, "hermes-agent-linux")
        self.assertIn("puede trabajar dentro de un contenedor (Docker)", he)
        self.assertIn(G["es"]["now.read_hostname"], he)
        en = combo(page("en"), "github-copilot-linux")
        self.assertIn(html.escape(G["en"]["after.read_copilot_policy"], quote=True), en)
        self.assertIn(html.escape(G["en"]["after.unconfirmed"], quote=True), en)

    def test_account_variant(self):
        """GTM-176 §4: no sandbox on that system, another user account."""
        for lang in LANGS:
            p = page(lang)
            for cid in ("cline-macos", "cline-windows", "cline-linux", "claude-code-windows", "cursor-windows", "grok-build-windows"):
                c = combo(p, cid)
                system = cid.rsplit("-", 1)[1]
                self.assertIn(html.escape(G[lang]["side.why.h"], quote=True), c, (lang, cid))
                self.assertIn(sandbox_section.code(G[lang]["acc.s1." + system]), c, (lang, cid))
                self.assertIn(html.escape(G[lang]["acc.net"], quote=True), c)
                self.assertEqual(c.count('class="sg-step"'), 4)
                self.assertNotIn(html.escape(G[lang]["fold.session"], quote=True), c)
                self.assertEqual(c.count("<details"), 1 if system in ("macos", "windows") else 0, (lang, cid))  # §7.4
                unconfirmed = html.escape(G[lang]["after.unconfirmed"], quote=True)
                self.assertEqual(unconfirmed in c, system in ("macos", "windows"), (lang, cid))
        es = page("es")
        self.assertIn("<code>Ejecuta dir C:\\Users\\tu-usuario</code>", combo(es, "cline-windows"))
        self.assertIn("<code>Ejecuta ls /home/tu-usuario</code>", combo(es, "cline-linux"))
        self.assertIn("<code>Ejecuta ls /Users/tu-usuario/Documents</code>", combo(es, "cline-macos"))
        self.assertIn("<code>ms-settings:otherusers</code>", combo(page("ca"), "cline-windows"))
        self.assertIn("Agregar un usuario sin una cuenta de Microsoft", combo(es, "cline-windows"))

    def test_lab_screenshots_from_a_test_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "manifest.json"
            m.write_text(json.dumps({"entries": LAB}))
            lab = sandbox_section.lab_entries(m)
        self.assertEqual(len(lab), 2)  # only concluyente
        p = sandbox_section.article("es", AGENTS, set(), lab)
        cc = combo(p, "claude-code-macos")
        self.assertIn('src="/assets/sandbox-lab/claude-code-macos-1-read-antes.png"', cc)
        self.assertIn(f'alt="Claude Code: {html.escape(CC_READ, quote=True)} antes de la plantilla"', cc)
        self.assertIn("Captura de nuestro laboratorio: Claude Code 2.1.330, macOS 26.1, 20 de noviembre de 2026.", cc)
        self.assertNotIn("x.png", cc)
        cx = combo(p, "codex-macos")
        self.assertIn("Comprobado en nuestro laboratorio el 21 de noviembre de 2026.", cx)
        self.assertEqual(cx.count(G["es"]["after.unconfirmed"]), 0)
        self.assertNotIn("<figure", combo(p, "cursor-macos"))  # without a capture, no gap
        self.assertEqual(sandbox_section.lab_entries(Path("/nonexistent/manifest.json")), [])

    def test_clarity_s7(self):
        """GTM-176 §7 (signed by Albert 17-11): summary without an agent, «Escríbele:», examples, one fold per step."""
        esc = lambda t: html.escape(t, quote=True)
        ex = esc(G["es"]["ex.label"])
        p = page("es")
        none = p[p.index('<div class="sg-none">'):p.index('<section class="sg-combo"', p.index('<div class="sg-none">'))]
        self.assertEqual(re.findall(r"<li><b>(\d)\.</b>", none), ["1", "2", "3"])
        sel = p[p.index('<div class="sg-sel"'):p.index('<p class="sg-status"')]
        self.assertNotIn('aria-pressed="true"', sel)  # no agent marked
        self.assertNotIn(" selected", sel)
        self.assertLess(p.index(G["es"]["h1"]), p.index(G["es"]["pick_line"]))
        self.assertLess(p.index(G["es"]["pick_line"]), p.index('<div class="sg-sel"'))
        cc = combo(p, "claude-code-macos")
        run = esc("Ejecuta " + CC_READ)
        self.assertIn(f'Escríbele: <code>{run}</code></span><span hidden id="claude-code-macos-c1">{run}</span>', cc)
        self.assertIn(esc(G["es"]["s1.p"].replace("{agent}", "Claude Code")), cc)
        self.assertIn(esc(G["es"]["s1.after"]), cc)
        self.assertIn(esc(G["es"]["s2.p"].replace("{agent}", "Claude Code")), cc)
        self.assertIn(esc(G["es"]["s3.p"]), cc)
        # Claude Code on macOS has the lab's screenshots (GTM-182), which replace the examples: they are checked without them.
        bare = combo(sandbox_section.article("es", AGENTS, set(), []), "claude-code-macos")
        self.assertIn(f"{ex}</p><pre>Desktop  Documents  Downloads  proyecto</pre>", bare)
        self.assertIn("<pre>ls: /Users/tu-usuario: Operation not permitted</pre>", bare)
        self.assertIn(f"<pre>{esc(sandbox_section.EX_NETWORK['git'][0])}</pre>", bare)
        self.assertIn(f"<pre>{esc(sandbox_section.EX_NETWORK['git'][1])}</pre>", bare)
        self.assertEqual(cc.count('<details class="sg-if">'), 2)  # step 1 (the note) and step 3
        self.assertNotIn("¿Alguna ha funcionado?", p)
        s3 = cc[cc.index(esc(G["es"]["s3.p"])):]
        fold3 = s3[s3.index('<details class="sg-if">'):]
        for t in (G["es"]["note.cc_allowlist_open"], G["es"]["s3.fixed"], G["es"]["s3.worked_p"]):
            self.assertIn(esc(t), fold3)
        self.assertIn("<code>claude --version</code>", fold3)
        self.assertNotIn(esc(G["es"]["s3.fixed"]), s3[:s3.index('<details class="sg-if">')])
        # Windows: the PowerShell table before, the denial after
        cx = combo(p, "codex-windows")
        self.assertIn(f"<pre>{esc(sandbox_section.WIN_TABLE)}</pre>", cx)
        self.assertIn(f"<pre>{esc(sandbox_section.EX_READ_AFTER['windows'])}</pre>", cx)
        self.assertNotIn("HTTP/2 200", cx)  # before_also_fails: no example
        self.assertEqual(cx.count(esc(G["es"]["after.unconfirmed"])), 2)  # in the folds of steps 1 and 3
        self.assertNotIn('class="sg-muted"', cx[:cx.index("<details")])
        # Linux, hostname, works_by_design, copilot_policy, kind none
        self.assertIn("<pre>ls: cannot open directory &#x27;/home/tu-usuario&#x27;: Permission denied</pre>", combo(p, "claude-code-linux"))
        he = combo(p, "hermes-agent-macos")
        self.assertIn("<pre>mi-portatil</pre>", he)
        self.assertIn("<pre>3f2a9c1b7e04</pre>", he)
        self.assertIn("<code>Ejecuta hostname</code>", he)
        gk = combo(p, "grok-build-macos")
        self.assertNotIn("HTTP/2 200", gk)
        self.assertNotIn("Could not resolve host", gk)
        self.assertIn("<pre>Desktop  Documents  Downloads  proyecto</pre>", gk)
        cp = combo(p, "github-copilot-macos")
        self.assertIn('<span hidden id="github-copilot-macos-c1">/sandbox policy</span>', cp)
        self.assertEqual(cp.count(ex), 2)  # network only, before and after
        gw = combo(p, "gemini-cli-windows")
        self.assertNotIn(ex, gw)
        self.assertNotIn(esc(G["es"]["s1.after"]), gw)
        # Antigravity: no «si te pide permiso» in step 3, its note visible
        ag = combo(p, "antigravity-cli-windows")
        self.assertIn(f'<p>{esc(G["es"]["s3.p_agy"])}</p><p class="sg-small">{esc(G["es"]["note.agy_ask_means_off"])}</p>', ag)
        self.assertEqual(ag.count(esc(G["es"]["note.agy_ask_means_off"])), 1)
        # §4
        cm = combo(p, "cline-macos")
        self.assertIn("<pre>Desktop  Documents  Downloads</pre>", cm)
        self.assertIn("<pre>ls: /Users/tu-usuario/Documents: Permission denied</pre>", cm)
        self.assertIn(esc(G["es"]["after.unconfirmed"]), cm[cm.index('<details class="sg-if">'):])
        cw = combo(p, "cline-windows")
        self.assertIn(f"<pre>{esc(sandbox_section.WIN_TABLE.replace('tu-usuario', 'cuenta-nueva'))}</pre>", cw)
        self.assertIn("    Directory: C:\\Users\\cuenta-nueva\n", sandbox_section.EX_ACC_HOME["windows"])
        self.assertIn(f"<pre>{esc(sandbox_section.EX_READ_AFTER['windows'])}</pre>", cw)
        self.assertIn("<pre>ls: cannot open directory", combo(p, "cline-linux"))
        for lang in ("en", "ca"):
            q = page(lang)
            self.assertIn(f'{esc(G[lang]["run"]).replace("{cmd}", "")}<code>{esc(G[lang]["run_cmd"].replace("{cmd}", CC_READ))}</code>',
                          combo(q, "claude-code-macos"))
            self.assertIn(esc(G[lang]["fold.if"]), q)

    def test_a_capture_replaces_the_example_of_its_box(self):
        p = sandbox_section.article("es", AGENTS, set(), [e for e in LAB if e["result"] == "concluyente"])
        cc = combo(p, "claude-code-macos")
        box = cc[cc.index('id="claude-code-macos-c1"'):cc.index('id="claude-code-macos-c2"')]
        self.assertIn("claude-code-macos-1-read-antes.png", box)
        self.assertNotIn("<pre>Desktop", box)
        self.assertIn("<pre>ls: /Users/tu-usuario: Operation not permitted</pre>", cc)  # the after box has no concluyente capture
        cx = combo(p, "codex-macos")
        self.assertIn("codex-macos-3-read-despues.png", cx)
        self.assertNotIn("Operation not permitted", cx)
        self.assertIn("<pre>Desktop  Documents  Downloads  proyecto</pre>", cx)

    def test_to_review_shows_on_that_page_combinations(self):
        url = "https://docs.x.ai/build/features/sandbox.md"
        p = page("es", {url})
        self.assertEqual(p.count(T["es"]["review"]), 3)  # Grok Build on the three systems
        self.assertNotIn(T["es"]["review"], page("es"))

    def test_review_from_the_latest_raw_file(self):
        fid = next(s["id"] for s in SOURCES if s.get("read", {}).get("url") == "https://cursor.com/docs/reference/sandbox.md")
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "2026-11-16.json").write_text(json.dumps({"sources": [{"id": fid, "missing": ["networkPolicy"]}]}))
            (Path(d) / "2026-11-15.json").write_text(json.dumps({"sources": [{"id": "F48", "missing": ["x"]}]}))
            self.assertEqual(sandbox_section.to_review(d), {"https://cursor.com/docs/reference/sandbox.md"})
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(sandbox_section.to_review(d), set())

    def test_a_replaced_watch_string_no_longer_marks_review(self):
        """F49 (Albert, 17-11): the string the page dropped was replaced; the raw of that day still lists it."""
        url = "https://code.claude.com/docs/en/sandboxing"
        watch = next(s for s in SOURCES if s["id"] == "F49")["read"]["watch"]
        self.assertNotIn("Set it to false to prompt for sandboxed commands", watch)
        self.assertIn("For auto-allow mode, also set sandbox.autoAllowBashIfSandboxed to true", watch)
        self.assertEqual(len(watch), 17)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "2026-11-17.json"
            f.write_text(json.dumps({"sources": [{"id": "F49", "missing": ["Set it to false to prompt for sandboxed commands"]}]}))
            self.assertEqual(sandbox_section.to_review(d), set())
            f.write_text(json.dumps({"sources": [{"id": "F49", "missing": ["socat"]}]}))
            self.assertEqual(sandbox_section.to_review(d), {url})

    def test_claude_code_second_source(self):
        """F62 (Albert, 17-11): the settings reference, for the default of sandbox.autoAllowBashIfSandboxed."""
        ref = "https://code.claude.com/docs/en/settings-reference"
        f62 = next(s for s in SOURCES if s["id"] == "F62")
        self.assertEqual((f62["read"]["url"], f62["scope"], f62["method"]), (ref, "claude-code", "page-watch"))
        self.assertEqual(f62["read"]["watch"], ["sandbox.autoAllowBashIfSandboxed", "Default: false. Before v2.1.324, the default was true"])
        for s in ("macos", "linux"):
            self.assertEqual([x["url"] for x in BY_ID["claude-code"]["templates"][s]["extra_sources"]], [ref])
        self.assertIn(ref, sandbox_section.template_urls(BY_ID["claude-code"]["templates"]["macos"]))

    def test_links_to_the_section(self):  # noqa: the agent anchors stay #{agent}
        site = ROOT / "site"
        for lang, guide, gloss, cmp_ in (("es", "es/probar-un-agente-de-ia", "es/glosario", "es/observatorio/agentes-ia-con-sandbox"),
                                         ("en", "try-an-ai-agent", "glossary", "observatory/ai-agents-with-sandbox"),
                                         ("ca", "ca/provar-un-agent-dia", "ca/glossari", "ca/observatori/agents-ia-amb-sandbox")):
            link = f'<a href="{sandbox_section.SECTION_PATH[lang]}">{html.escape(T[lang]["all_about"], quote=False)}</a>'
            for f in (guide, gloss, cmp_, {"es": "es/observatorio", "en": "observatory", "ca": "ca/observatori"}[lang]):
                self.assertIn(link, (site / f / "index.html").read_text(encoding="utf-8"), (lang, f))
            ficha = (site / {"es": "es/observatorio", "en": "observatory", "ca": "ca/observatori"}[lang] / "claude-code" / "index.html").read_text(encoding="utf-8")
            self.assertIn(f'<a href="{sandbox_section.SECTION_PATH[lang]}#claude-code">{html.escape(T[lang]["its_template"], quote=False)}</a>', ficha)


# GTM-179: P2's user block, copied literally from qtorb/rosmarops internal/profiles/profiles.go, const p2JSON, v0.14.0
# (master after #133, BV-254). The web's Claude Code template must be this text, byte for byte.
P2_JSON = """{
  "permissions": {
    "defaultMode": "acceptEdits",
    "disableAutoMode": "disable",
    "disableBypassPermissionsMode": "disable",
    "blockReadsOutsideWorkingDirectories": true,
    "allow": [
      "Bash(npm run lint)", "Bash(npm run test *)",
      "Bash(git status)", "Bash(git diff)"
    ],
    "ask": [
      "Edit(~/.codex/**)", "Edit(**/.codex/**)",
      "Edit(~/.cursor/**)", "Edit(**/.cursor/**)",
      "Edit(~/.cline/**)", "Edit(**/.clinerules/**)",
      "Edit(~/.gemini/**)", "Edit(**/.gemini/**)",
      "Edit(~/.grok/**)", "Edit(**/.grok/**)", "Edit(~/.hermes/**)",
      "Edit(~/AppData/Roaming/**)",
      "Edit(**/AGENTS.md)", "Edit(**/CLAUDE.md)", "Edit(**/GEMINI.md)",
      "Edit(**/.github/copilot-instructions.md)"
    ],
    "deny": ["WebFetch", "WebSearch", "Bash(curl *)", "Bash(wget *)"]
  },
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "autoAllowBashIfSandboxed": false,
    "network": { "allowedDomains": ["registry.npmjs.org", "github.com"], "strictAllowlist": true },
    "filesystem": { "denyRead": ["~/.ssh", "~/.aws"] },
    "credentials": { "files": [ { "path": "~/.aws/credentials", "mode": "deny" }, { "path": "~/.ssh", "mode": "deny" } ] }
  }
}"""


class ClaudeCodeOneText(unittest.TestCase):
    """GTM-179 (CTO-68): on macOS and Linux the Claude Code template is one text, the user block, as in program 0.14.0."""

    def copied(self, lang, system):
        cc = combo(page(lang), f"claude-code-{system}")
        m = re.search(rf'<pre id="claude-code-{system}-c3">(.*?)</pre>', cc, re.S)
        return html.unescape(m.group(1))

    def test_one_block_and_intro_paste_one(self):
        for system in ("macos", "linux"):
            t = BY_ID["claude-code"]["templates"][system]
            self.assertEqual(t["intro"], "paste_one", system)
            self.assertEqual([b["file"] for b in t["blocks"]], ["~/.claude/settings.json"], system)

    def test_copied_text_has_no_project_block(self):
        for lang in LANGS:
            for system in ("macos", "linux"):
                txt = self.copied(lang, system)
                self.assertIn("~/.claude/settings.json", txt, (lang, system))
                self.assertNotIn("// .claude/settings.json", txt, (lang, system))
                self.assertNotIn('allowRead": ["."]', txt, (lang, system))
                want = sandbox_section.fill(T[lang]["paste.one"], agent="Claude Code", file="~/.claude/settings.json")
                self.assertEqual(txt, want + "\n\n" + P2_JSON, (lang, system))

    def test_paste_one_sentence(self):
        self.assertTrue(self.copied("es", "macos").startswith(
            "Añade estos ajustes a mi configuración de Claude Code (~/.claude/settings.json), sin cambiar nada más. "
            "Enséñame el cambio antes de guardarlo."))

    def test_user_block_is_the_program_p2json(self):
        for system in ("macos", "linux"):
            self.assertEqual(BY_ID["claude-code"]["templates"][system]["blocks"][0]["value"], P2_JSON, system)


class LabRelease(unittest.TestCase):
    """GTM-182: the lab release brought in (observatory/data/lab/manifest.json and site/assets/sandbox-lab/)."""

    MANIFEST = sandbox_section.LAB_MANIFEST
    IMG = ROOT / "site" / "assets" / "sandbox-lab"
    # Where each concluyente capture goes: (combo, step, the box's command or None for step 2, file).
    WANT = {
        ("claude-code-macos", 1, CC_READ, "claude-code-macos-3-ls-antes.png"),
        ("claude-code-macos", 1, "git ls-remote https://example.com", "claude-code-macos-3-red-antes.png"),
        ("claude-code-macos", 2, None, "claude-code-macos-1-fichero1-despues.png"),
        ("claude-code-macos", 3, CC_READ, "claude-code-macos-3-ls-despues.png"),
        ("claude-code-macos", 3, "git ls-remote https://example.com", "claude-code-macos-3-red-despues.png"),
        ("codex-macos", 1, "ls ~", "codex-macos-3-ls-antes.png"),
        ("codex-macos", 2, None, "codex-macos-1-fichero1-despues.png"),
        ("codex-macos", 3, "ls ~", "codex-macos-3-ls-despues.png"),
        ("codex-macos", 3, "curl -I https://example.com", "codex-macos-3-red-despues.png"),
    }

    def placed(self, lang):
        out = set()
        p = page(lang)
        for m in re.finditer(r'<section class="sg-combo" id="([^"]+)"(.*?)</section>', p, re.S):
            for n, step in enumerate(m.group(2).split('<li class="sg-step">')[1:], 1):
                for box in step.split('<div class="sg-test">'):
                    for f in re.findall(r'<img src="/assets/sandbox-lab/([^"]+)"', box):
                        c = re.search(r'<span hidden id="[^"]+">(.*?)</span>', box)
                        cmd = html.unescape(c.group(1)).split(" ", 1)[1] if c and n != 2 else None
                        out.add((m.group(1), n, cmd, f))
        return out

    def test_each_capture_in_its_box_and_nowhere_else(self):
        for lang in LANGS:
            self.assertEqual(self.placed(lang), self.WANT, lang)

    def test_only_concluyente_pngs_published_and_their_sha256(self):
        import hashlib
        m = json.loads(self.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(m["release"], "lab-20261118-2")
        want = {n: h for e in m["entries"] if e["result"] == "concluyente" for n, h in e["files"].items() if n.endswith(".png")}
        got = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in self.IMG.iterdir()}
        self.assertEqual(got, want)
        self.assertEqual(len(want), 9)
        self.assertFalse(any(f.suffix == ".txt" for f in self.IMG.iterdir()))

    def test_a_capture_of_another_command_or_file_is_not_shown(self):
        e = dict(sandbox_section.lab_entries()[0])
        moved = []
        for x in sandbox_section.lab_entries():
            x = dict(x)
            if x["step"] != 2:
                x["command"] = "ls ~/otra-cosa"
            else:
                x["path"] = "~/.otro/settings.json"
            moved.append(x)
        p = sandbox_section.article("es", AGENTS, set(), moved)
        self.assertNotIn("<figure", p)
        self.assertNotIn("Comprobado en nuestro laboratorio", p)
        self.assertEqual(e["agent"], "claude-code")

    def test_each_capture_links_to_its_png_with_its_size(self):
        # GTM-183: a link to the full-size PNG around each capture, no new visible text, real width and height, lazy.
        for lang in LANGS:
            figs = re.findall(r"<figure>(.*?)<figcaption>", page(lang), re.S)
            self.assertEqual(len(figs), 9, lang)
            for f in figs:
                m = re.fullmatch(r'<a href="(/assets/sandbox-lab/[^"]+\.png)"><img src="([^"]+)" alt="([^"]+)" '
                                 r'width="(\d+)" height="(\d+)" loading="lazy" decoding="async"></a>', f)
                self.assertIsNotNone(m, f)
                self.assertEqual(m.group(1), m.group(2))
                w, h = sandbox_section.png_size(ROOT / "site" / m.group(1).lstrip("/"))
                self.assertEqual((int(m.group(4)), int(m.group(5))), (w, h))
        self.assertIn(".sg figure a{display:block}", page("es"))

    def test_png_size(self):
        self.assertEqual(sandbox_section.png_size(self.IMG / "codex-macos-3-ls-antes.png")[0] > 1000, True)
        self.assertIsNone(sandbox_section.png_size(self.MANIFEST))
        self.assertIsNone(sandbox_section.png_size(self.IMG / "nope.png"))
        # Without the file (a test manifest), no width or height, and still a link.
        p = sandbox_section.article("es", AGENTS, set(), [e for e in LAB if e["result"] == "concluyente"])
        self.assertIn('<a href="/assets/sandbox-lab/claude-code-macos-1-read-antes.png"><img src="/assets/sandbox-lab/claude-code-macos-1-read-antes.png" alt=', p)
        self.assertNotIn('width="', p[p.index("claude-code-macos-1-read-antes.png"):p.index("</figure>", p.index("claude-code-macos-1-read-antes.png"))])

    def test_caption_from_the_release(self):
        cc = combo(page("es"), "claude-code-macos")
        self.assertIn("Captura de nuestro laboratorio: Claude Code 2.1.327, macOS 26.7.2, 18 de noviembre de 2026.", cc)
        cx = combo(page("es"), "codex-macos")
        self.assertIn("Captura de nuestro laboratorio: Codex 0.170.0, macOS 26.7.2, 18 de noviembre de 2026.", cx)


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


class PageOrder(unittest.TestCase):
    """GTM-194 (order and texts signed by Albert, 20-11): the order of §2 and the texts of §3 in the three languages."""

    def test_sections_in_order(self):
        for lang in LANGS:
            p = page(lang)
            C = sandbox_section.ctexts(lang)
            esc = lambda t: html.escape(t, quote=True)
            h2 = lambda k: f"<h2>{esc(C[k])}</h2>"
            marks = [esc(G[lang]["h1"]), esc(C["lead"]), h2("why.h"), h2("day.h"), h2("level.h"),
                     '<div class="sg-sel"', '<section class="sg-combo"', esc(G[lang]["side.which.h"]),
                     esc(G[lang]["side.try.h"]), h2("wt.h"), h2("faq.h")]
            pos = [p.index(m) for m in marks]
            self.assertEqual(pos, sorted(pos), lang)
            # the two link boxes, once, after the last panel; the side column only in another-account panels
            self.assertEqual(p.count(esc(G[lang]["side.which.h"])), 1, lang)
            self.assertEqual(p.count(esc(G[lang]["side.try.h"])), 1, lang)
            self.assertGreater(p.index(esc(G[lang]["side.which.h"])), p.rindex('<section class="sg-combo"'))
            self.assertEqual(p.count('<aside class="sg-side">'), p.count(esc(G[lang]["side.why.h"])), lang)
            # §3.5 before the boxes of step 1; §3.6 links to the Observatory's home
            self.assertIn(esc(C["test_line"]), p)
            self.assertIn(f'<a href="{sandbox_section.OBS_PATH[lang]}">{esc(C["wt.link"])}</a>', p)
            for i in range(1, 6):
                self.assertIn(f'<summary>{esc(C[f"faq.q{i}"])}</summary>', p)

    def test_all_keys_in_the_three_languages(self):
        keys = [set(sandbox_section.ctexts(l)) for l in LANGS]
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[0], keys[2])
        self.assertEqual(len(keys[0]), 37)  # GTM-198: wt.orch, wt.orch.link, faq.a4.mcp, faq.a4.mcp.link
        for l in LANGS:
            for k, v in sandbox_section.ctexts(l).items():
                self.assertTrue(v.strip(), (l, k))
                self.assertFalse(FORBIDDEN.search(v), (l, k))

    def test_level_sentence_only_with_the_templates_page(self):
        import tempfile
        for lang in LANGS:
            with tempfile.TemporaryDirectory() as d:
                without = sandbox_section.sections(lang, site=d)["level"]
                self.assertNotIn(sandbox_section.TEMPLATES_PAGE[lang], without)
                f = Path(d) / sandbox_section.TEMPLATES_PAGE[lang].strip("/") / "index.html"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("x")
                withp = sandbox_section.sections(lang, site=d)["level"]
                self.assertIn(f'<a href="{sandbox_section.TEMPLATES_PAGE[lang]}">', withp)
