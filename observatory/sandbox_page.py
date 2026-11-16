#!/usr/bin/env python3
"""GTM-167: the Observatory page «Which AI coding agents have a sandbox», generated from the agent files.

Data: the optional "protections" field of each agent file (schema v1.11: sandbox and network cut-off per system, as
codes with their source), filled from qtorb/rosmarops-vigil docs/research/2026-11-15-gtm-164-protecciones.md (v2).
Texts: observatory/i18n/sandbox.json (signed, literal). Called by observatory/build.py; nothing is written by hand.
"""

import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import map_page

ROOT = Path(__file__).resolve().parent.parent
TEXTS = ROOT / "observatory" / "i18n" / "sandbox.json"
SANDBOX_PATH = {"en": "/observatory/ai-agents-with-sandbox/", "es": "/es/observatorio/agentes-ia-con-sandbox/",
                "ca": "/ca/observatori/agents-ia-amb-sandbox/"}
GLOSSARY_SANDBOX = {"en": "/glossary/#sandbox", "es": "/es/glosario/#sandbox", "ca": "/ca/glossari/#sandbox"}
SYSTEMS = ("windows", "macos", "linux")
LINES = ("sandbox", "network_cut")


def esc(s):
    return html.escape(str(s), quote=True)


def texts():
    return json.loads(TEXTS.read_text(encoding="utf-8"))["texts"]


def rows(agents):
    """The agent files that carry protections, in the order of their display name in English."""
    with_p = [a for a in agents if a.get("protections")]
    names = map_page.agent_names([a["agent"] for a in with_p], "en")
    return sorted(with_p, key=lambda a: names[a["agent"]["id"]].lower())


def read_date(agents):
    """The latest reading date of any protection value (the footer's {date})."""
    dates = [cell["source"]["accessed_at"] for a in rows(agents) for kind in LINES
             for cell in a["protections"][kind].values() if "source" in cell]
    return max(dates) if dates else None


def host(url):
    return urlsplit(url).hostname or url


def body(lang, agents, agent_href):
    """(texts, html) of the page. agent_href(id) is the path of a published agent page, or None."""
    import sandbox_section  # GTM-175: «All about sandboxes»
    T = texts()[lang]
    items = rows(agents)
    names = map_page.agent_names([a["agent"] for a in items], lang)

    def cell(a, system):
        out = []
        for kind in LINES:
            c = a["protections"][kind][system]
            value = esc(T["value." + c["value"]])
            if "source" in c:
                value = f'<a href="{esc(c["source"]["url"])}" rel="noopener">{value}</a>'
            out.append(f'<span class="sb-line">{esc(T["line." + kind])}: {value}</span>')
        return "<br>".join(out)

    def sources(a):
        seen = []
        for kind in LINES:
            for system in SYSTEMS:
                c = a["protections"][kind][system]
                if "source" in c and c["source"]["url"] not in seen:
                    seen.append(c["source"]["url"])
        return " · ".join(f'<a href="{esc(u)}" rel="noopener">{esc(host(u))}</a>' for u in seen) or "—"

    trs = []
    for a in items:
        aid = a["agent"]["id"]
        href = agent_href(aid)
        name = esc(names[aid])
        name_html = f'<a href="{esc(href)}">{name}</a>' if href else name
        trs.append(
            "<tr>"
            f'<th scope="row" id="{esc(aid)}">{name_html}</th>'
            + "".join(f'<td data-label="{esc(T["col." + s])}">{cell(a, s)}</td>' for s in SYSTEMS)
            + f'<td data-label="{esc(T["col.source"])}">{sources(a)}</td>'
            "</tr>"
        )
    head = ("<thead><tr>" + "".join(f'<th scope="col">{esc(T["col." + k])}</th>'
                                   for k in ("agent", "windows", "macos", "linux", "source")) + "</tr></thead>")
    date = read_date(agents)
    footer = re.sub(r"\{[a-z]+\}", map_page.fmt_date(date, lang), T["footer"]) if date else ""
    page = f"""<article>
<h1>{esc(T["title"])}</h1>
<p class="lead">{esc(T["lead"])}</p>
<p>{esc(T["notice"])}</p>
<div class="box tablebox"><table class="sandbox">
{head}
<tbody>
{chr(10).join(trs)}
</tbody>
</table></div>
<p class="note">{esc(footer)}</p>
<p class="note"><a href="{GLOSSARY_SANDBOX[lang]}">{esc(T["glossary_link"])}</a> · <a href="{sandbox_section.SECTION_PATH[lang]}">{esc(sandbox_section.texts()[lang]["all_about"])}</a></p>
</article>"""
    return T, page
