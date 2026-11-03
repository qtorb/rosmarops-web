#!/usr/bin/env python3
"""GTM-78: chart «De fábrica» (ES and EN) from observatory/data/agents/{claude-code,cursor,hermes-agent}.json.

Writes chart.svg / chart.en.svg next to this file, and cells.json with the cell -> capability -> source mapping.
PNGs at 1200x675 are rendered from the SVGs with Playwright:  python3 make_chart.py --png
"""

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AGENTS = [("claude-code", "Claude Code"), ("cursor", "Cursor"), ("hermes-agent", "Hermes Agent")]
ACTIONS = ["read_files", "write_files", "execute_commands", "network", "use_mcp_tools"]
RANK = {"allow": 3, "ask": 2, "deny": 1}
# Breadth of a scope, to pick one when several scopes share the most permissive default.
BREADTH = ["whole_system", "any_path", "any_destination", "all_commands", "all_mcp_tools", "outside_working_directories",
           "other_agents_credentials", "working_directories", "preapproved_domains", "read_only_commands",
           "protected_paths", "ignored_credential_files"]

# Design tokens of rosmarops.com (light theme): site/index.html and the sample report's grade colours.
T = {"bg": "#F6F5F2", "card": "#FFFFFF", "ink": "#1B1A18", "muted": "#66635D", "line": "#E3E0D8",
     "red": "#94200B", "red_bg": "#FDECE7", "amb": "#6B4700", "amb_bg": "#FDF5DF", "grey": "#4D4A45", "grey_bg": "#F0EEE8"}
FONT = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

TEXT = {
    "es": {
        "title": "Qué deja hacer cada agente sin preguntarte, de fábrica",
        "cols": ["Lee tus ficheros", "Escribe ficheros", "Ejecuta comandos", "Saca datos fuera", "Usa herramientas MCP"],
        "word": {"allow": "sin preguntar", "ask": "pregunta", "deny": "bloqueado"},
        "footer": "En los tres, lo que “pregunta” lo decide de fábrica otro modelo de IA, no tú. "
                  "Fuente: documentación oficial de cada agente · rosmarops.com/es/metodologia/",
    },
    "en": {
        "title": "What each agent does without asking you, out of the box",
        "cols": ["Reads your files", "Writes files", "Runs commands", "Sends data out", "Uses MCP tools"],
        "word": {"allow": "without asking", "ask": "asks", "deny": "blocked"},
        "footer": "In all three, what “asks” is decided out of the box by another AI model, not by you. "
                  "Source: each agent's official documentation · rosmarops.com/methodology/",
    },
}


def scope_label(lang, scope):
    """The Observatory's own published label for a scope (observatory/i18n), without its parenthesis."""
    i18n = json.loads((ROOT / "observatory" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
    return i18n[f"scope.{scope}"].split(" (")[0]


def cells():
    out = []
    for slug, name in AGENTS:
        d = json.loads((ROOT / "observatory" / "data" / "agents" / f"{slug}.json").read_text(encoding="utf-8"))
        assert d["default_mode"]["who_decides"] == "another_model", slug
        row = {"agent": name, "file": f"observatory/data/agents/{slug}.json", "mode": d["default_mode"]["name"],
               "who_decides": d["default_mode"]["who_decides"], "cells": []}
        for action in ACTIONS:
            caps = [c for c in d["capabilities"] if c["action"] == action]
            if not caps:
                row["cells"].append({"action": action, "default": None, "scope": None, "capability": None, "url": None})
                continue
            best = max(caps, key=lambda c: (RANK[c["default"]], -BREADTH.index(c["scope"])))
            row["cells"].append({"action": action, "default": best["default"], "scope": best["scope"],
                                 "capability": best["id"], "url": best["source"]["url"],
                                 "all": [f"{c['id']}: {c['scope']}={c['default']}" for c in caps]})
        out.append(row)
    return out


def wrap(text, n):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur] if cur else lines


def svg(lang, rows):
    t = TEXT[lang]
    W, H = 1200, 675
    left, top, label_w = 48, 150, 210
    col_w = (W - 2 * left - label_w) / 5
    row_h = 128
    e = html.escape
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="{T["bg"]}"/>',
         f'<text x="{left}" y="78" font-size="36" font-weight="700" fill="{T["ink"]}">{e(t["title"])}</text>']
    for k, col in enumerate(t["cols"]):
        x = left + label_w + k * col_w + col_w / 2
        s.append(f'<text x="{x:.1f}" y="{top - 18}" font-size="16" font-weight="600" fill="{T["muted"]}" '
                 f'text-anchor="middle">{e(col)}</text>')
    for r, row in enumerate(rows):
        y = top + r * row_h
        s.append(f'<line x1="{left}" y1="{y}" x2="{W - left}" y2="{y}" stroke="{T["line"]}" stroke-width="1.5"/>')
        s.append(f'<text x="{left}" y="{y + row_h / 2 + 9}" font-size="26" font-weight="700" fill="{T["ink"]}">'
                 f'{e(row["agent"])}</text>')
        for k, c in enumerate(row["cells"]):
            x0 = left + label_w + k * col_w + 8
            cx = x0 + (col_w - 16) / 2
            if c["default"] is None:
                s.append(f'<text x="{cx:.1f}" y="{y + row_h / 2 + 10}" font-size="28" fill="{T["muted"]}" '
                         f'text-anchor="middle">—</text>')
                continue
            fg, bg = {"allow": (T["red"], T["red_bg"]), "ask": (T["amb"], T["amb_bg"]),
                      "deny": (T["grey"], T["grey_bg"])}[c["default"]]
            s.append(f'<rect x="{x0:.1f}" y="{y + 12}" width="{col_w - 16:.1f}" height="{row_h - 24}" rx="10" fill="{bg}"/>')
            label = scope_label(lang, c["scope"])
            scope = wrap(label[0].lower() + label[1:], 22)
            y_word = y + row_h / 2 - 6 * len(scope) + 2
            s.append(f'<text x="{cx:.1f}" y="{y_word:.1f}" font-size="21" font-weight="700" fill="{fg}" '
                     f'text-anchor="middle">{e(t["word"][c["default"]])}</text>')
            for n, line in enumerate(scope):
                s.append(f'<text x="{cx:.1f}" y="{y_word + 24 + n * 18:.1f}" font-size="15" fill="{T["ink"]}" '
                         f'text-anchor="middle">{e(line)}</text>')
    yb = top + len(rows) * row_h
    s.append(f'<line x1="{left}" y1="{yb}" x2="{W - left}" y2="{yb}" stroke="{T["line"]}" stroke-width="1.5"/>')
    s.append(f'<text x="{left}" y="{H - 40}" font-size="15" fill="{T["muted"]}" textLength="{W - 2 * left}" '
             f'lengthAdjust="spacingAndGlyphs">{e(t["footer"])}</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


def main():
    rows = cells()
    (HERE / "cells.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lang, name in (("es", "chart"), ("en", "chart.en")):
        (HERE / f"{name}.svg").write_text(svg(lang, rows), encoding="utf-8")
    if "--png" in sys.argv:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=1)
            for name in ("chart", "chart.en"):
                pg.set_content(f'<html><body style="margin:0">{(HERE / f"{name}.svg").read_text(encoding="utf-8")}</body></html>')
                pg.screenshot(path=str(HERE / f"{name}.png"), clip={"x": 0, "y": 0, "width": 1200, "height": 675})
            b.close()


if __name__ == "__main__":
    main()
