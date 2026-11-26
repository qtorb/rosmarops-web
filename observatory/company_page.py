#!/usr/bin/env python3
"""GTM-169: the Observatory by company, generated from the agent files.

- the company grid of the Observatory front page (companies with at least one product RosmarOps evaluates or
  detects; the rest in one block);
- the protections strip of each evaluated product (the "protections" field, schema v1.12);
- «RosmarOps recommends it to start with», computed with criterion v1.1 (never a name written by hand);
- «Try it in a test environment», on the page of each evaluated product.

Texts: observatory/i18n/company.json (signed, literal), plus the literals the web already uses (families, status,
last change, class phrases of the map). Called by observatory/build.py; nothing is written by hand.
"""

import html
import json
import re
from pathlib import Path

import map_page
import sandbox_page

ROOT = Path(__file__).resolve().parent.parent
TEXTS = ROOT / "observatory" / "i18n" / "company.json"
SYSTEMS = ("windows", "macos", "linux")
SYSTEM_NAME = {"windows": "Windows", "macos": "macOS", "linux": "Linux"}
# GitHub belongs to Microsoft: one company, shown as «Microsoft (GitHub)» (signed 15-11, GTM-169).
COMPANY = {"GitHub": "Microsoft", "Microsoft": "Microsoft"}
COMPANY_NAME = {"Microsoft": "Microsoft (GitHub)"}
GLOSSARY = {"en": "/glossary/", "es": "/es/glosario/", "ca": "/ca/glossari/"}
GLOSSARY_ANCHOR = {
    "sandbox": {"en": "sandbox", "es": "sandbox", "ca": "sandbox"},
    "read_only": {"en": "read-only", "es": "solo-lectura", "ca": "nomes-lectura"},
    "asks_first": {"en": "asks-first", "es": "te-pregunta-antes", "ca": "et-pregunta-abans"},
    "network_cut": {"en": "network-cut", "es": "corte-de-red", "ca": "tall-de-xarxa"},
}
METHOD = {"en": "/methodology/#recommendation", "es": "/es/metodologia/#recomendacion", "ca": "/ca/metodologia/#recomanacio"}
GUIDE_PATH = {"en": "/try-an-ai-agent/", "es": "/es/probar-un-agente-de-ia/", "ca": "/ca/provar-un-agent-dia/"}
FRAME = '<rect x="2" y="2" width="20" height="20" rx="5"/>'
ICON = {
    "sandbox": '<rect x="7" y="7" width="10" height="10" rx="1.5"/><circle cx="12" cy="12" r="1.2"/>',
    "read_only": '<path d="M6.5 12s2.2-3.5 5.5-3.5 5.5 3.5 5.5 3.5-2.2 3.5-5.5 3.5-5.5-3.5-5.5-3.5z"/><circle cx="12" cy="12" r="1.4"/>',
    "asks_first": '<path d="M9.8 9.6a2.3 2.3 0 1 1 3.2 2.1c-.6.3-1 .8-1 1.5v.4"/><circle cx="12" cy="16.6" r=".4"/>',
    "network_cut": '<circle cx="12" cy="12" r="4.5"/><path d="M7.5 16.5l9-9"/>',
}
CSS = """
.co-k{margin:0;font-size:14px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.co-hero h1{font-size:34px;line-height:1.15}
.co-hero .lead{font-size:17px;color:var(--ink2);max-width:65ch}
.co-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start}
@media (max-width:760px){.co-grid{grid-template-columns:minmax(0,1fr)}}
.co{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-width:0}
.co header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding:0 0 8px}
.co h3{margin:0;font-size:20px}.co-n{font-size:13px;color:var(--muted);white-space:nowrap}
.co-list{list-style:none;margin:0;padding:0}
.co-p{display:flex;flex-direction:column;gap:6px;padding:12px 0;border-bottom:1px solid var(--line)}
.co-p:last-child{border-bottom:0;padding-bottom:0}
.co-pn{font-size:16px;font-weight:700}
.co-tag{font-size:12px;color:var(--brand-on);background:var(--brand-tint);border-radius:999px;padding:1px 8px;width:max-content;max-width:100%}
.co-cl{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--ink2)}
.co-cls{min-width:26px;height:26px;display:inline-grid;place-items:center;font-weight:700;font-size:17px;border:1.5px dashed var(--ink);border-radius:7px;color:var(--ink);box-sizing:border-box}
.co-cls.co-none{border:1.5px solid var(--line);color:var(--muted)}
.co-meta{margin:0;font-size:12.5px;color:var(--muted)}
.pr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:4px 0 0}
.pr-i{display:flex;flex-direction:column;gap:2px;min-width:0}
.pr-n{display:flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:var(--ink2);text-decoration:none}
.pr-n:hover{color:var(--brand)}.pr-n svg{width:18px;height:18px;flex:none}
.pr-v{font-size:12.5px;color:var(--muted);line-height:1.4}
.pr-v a{color:var(--muted)}
.rec{background:var(--brand-tint);border-left:3px solid var(--brand);border-radius:10px;padding:10px 14px;display:flex;flex-direction:column;gap:4px}
.rec-t{margin:0;font-size:14px;font-weight:700;color:var(--ink)}
.rec-d,.rec-how{margin:0;font-size:12.5px;color:var(--muted)}
.rec ul{list-style:none;margin:0;padding:0;font-size:13px;color:var(--ink2);line-height:1.45}
.rec ul a{color:var(--ink2)}
.co-rest{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px 18px;display:flex;flex-direction:column;gap:6px}
.co-rest p{margin:0;font-size:15px;line-height:1.6;color:var(--ink2)}
.try ul{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:8px}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def texts():
    return json.loads(TEXTS.read_text(encoding="utf-8"))["texts"]


def fill(s, **kw):
    return re.sub(r"\{([a-z]+)\}", lambda m: str(kw[m.group(1)]), s)


def classes():
    """{agent file id: class letter} from the map data the release publishes."""
    ep = map_page.load()[0]
    return {map_page.AGENT_FILE.get(a["product"], a["product"]): a.get("class") for a in ep["agents"] if a.get("class")}


def evaluated(a):
    return a["agent"]["rosmarops"]["status"] == "evaluated" and bool(a.get("protections"))


def join_systems(T, systems):
    names = [SYSTEM_NAME[s] for s in systems]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + T["sys.and"] + names[-1]


def summary(T, cells):
    """The one-line value of sandbox or network cut, from its three systems (GTM-169 §3)."""
    v = {s: cells[s]["value"] for s in SYSTEMS}
    if all(x == "container_only" for x in v.values()):
        return T["sys.container_only"]
    known = [s for s in SYSTEMS if v[s] in ("on_by_default", "off_by_default", "container_only")]
    if not known:
        return T["sys.none"] if "none" in v.values() else "—"
    on = [s for s in known if v[s] == "on_by_default"]
    off = [s for s in known if v[s] != "on_by_default"]
    if not off:
        state = T["state.on"]
    elif not on:
        state = T["state.off"]
    else:
        state = fill(T["state.mix"], on=join_systems(T, on), off=join_systems(T, off))
    return f"{join_systems(T, known)} · {state}"


def af_value(T, cell):
    return "—" if cell["value"] == "unknown" else T["af." + cell["value"]]


def recommendation(a, cls):
    """1 (route 1), 2 (route 2) or None, with criterion v1.1. cls: the published factory class, or None."""
    p = a.get("protections")
    if not p or a["agent"]["rosmarops"]["status"] != "evaluated":
        return None
    if cls in ("A", "B") and p.get("read_only", {}).get("value") == "yes" \
            and p.get("asks_first", {}).get("commands", {}).get("value") == "by_default":
        return 1
    if all(p["sandbox"][s]["value"] == "on_by_default" for s in SYSTEMS) \
            and all(p["network_cut"][s]["value"] == "on_by_default" for s in SYSTEMS):
        return 2
    return None


def calc_date(agents):
    """The date of the last calculation: the latest of the map data and of every protection value read."""
    dates = [map_page.load()[0]["generated_at"][:10]]
    for a in agents:
        p = a.get("protections") or {}
        for kind in ("sandbox", "network_cut"):
            dates += [c["source"]["accessed_at"] for c in p.get(kind, {}).values() if "source" in c]
        if "source" in p.get("read_only", {}):
            dates.append(p["read_only"]["source"]["accessed_at"])
        dates += [c["source"]["accessed_at"] for c in p.get("asks_first", {}).values() if "source" in c]
    return max(dates)


def strip(lang, a):
    T = texts()[lang]
    p = a["protections"]
    aid = a["agent"]["id"]

    def item(kind, value_html):
        href = GLOSSARY[lang] + "#" + GLOSSARY_ANCHOR[kind][lang]
        svg = (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
               f'stroke-linejoin="round" aria-hidden="true">{FRAME}{ICON[kind]}</svg>')
        return (f'<div class="pr-i"><a class="pr-n" href="{href}">{svg}{esc(T["p." + kind])}</a>'
                f'<span class="pr-v">{value_html}</span></div>')

    by_system = f'<br><a href="{sandbox_page.SANDBOX_PATH[lang]}#{esc(aid)}">{esc(T["by_system"])}</a>'
    ro = p.get("read_only", {"value": "unknown"})["value"]
    ro_html = "—" if ro == "unknown" else esc(T["ro." + ro])
    af = p.get("asks_first", {"commands": {"value": "unknown"}})
    af_html = esc(af_value(T, af["commands"]))
    if "edits" in af:
        af_html += "<br>" + esc(fill(T["af.edits"], value=af_value(T, af["edits"]).lower()))
    return ('<div class="pr">'
            + item("sandbox", esc(summary(T, p["sandbox"])))
            + item("read_only", ro_html)
            + item("asks_first", af_html)
            + item("network_cut", esc(summary(T, p["network_cut"])) + by_system)
            + "</div>")


def rec_box(lang, a, cls, date, map_texts):
    route = recommendation(a, cls)
    if not route:
        return ""
    T = texts()[lang]
    p = a["protections"]
    aid = a["agent"]["id"]
    link = lambda url, text: f'<li><a href="{esc(url)}" rel="noopener">{esc(text)}</a></li>'
    if route == 1:
        phrase = map_texts[lang]["class." + cls]
        phrase = phrase[:1].lower() + phrase[1:]
        reasons = [
            link(map_page.MAP_PATH[lang] + "#" + aid, fill(T["rec.v1.class"], letter=cls, phrase=phrase)),
            link(p["read_only"]["source"]["url"], T["rec.v1.read_only"]),
            link(p["asks_first"]["commands"]["source"]["url"], T["rec.v1.asks"]),
        ]
    else:
        cmp = sandbox_page.SANDBOX_PATH[lang] + "#" + aid
        reasons = [link(cmp, T["rec.v2.sandbox"]), link(cmp, T["rec.v2.network"])]
    return (f'<div class="rec"><p class="rec-t">{esc(T["rec.title"])}</p>'
            f'<p class="rec-d">{esc(fill(T["rec.date"], date=map_page.fmt_date(date, lang)))}</p>'
            f'<ul>{"".join(reasons)}</ul>'
            f'<p class="rec-how"><a href="{METHOD[lang]}">{esc(T["rec.how"])}</a></p></div>')


def try_section(lang, a):
    """«Try it in a test environment», for the page of an evaluated product ("" otherwise)."""
    if not evaluated(a):
        return ""
    T = texts()[lang]
    ag = a["agent"]
    lines = []
    for s in SYSTEMS:
        c = a["protections"]["sandbox"][s]
        v = c["value"]
        system = SYSTEM_NAME[s]
        if v in ("off_by_default", "container_only"):
            doc = f'<a href="{esc(c["source"]["url"])}" rel="noopener">{esc(T["try.doc"])}</a>'
            key = "try.claude_code_sandbox" if ag["id"] == "claude-code" and v == "off_by_default" else "try." + v  # GTM-169 A2
            line = fill(esc(T[key]), system=esc(system), doc=doc)
        elif v == "on_by_default":
            line = esc(fill(T["try.on_by_default"], system=system))
        elif ag["id"] == "claude-code":
            line = esc(fill(T["try.claude_code"], system=system))
        else:
            line = esc(fill(T["try.other_account"], system=system))
        lines.append(f"<li>{line}</li>")
    return f"""<section id="try" class="box panel try" aria-labelledby="try-h">
<h2 id="try-h">{esc(T["try.title"])}</h2>
<p>{esc(fill(T["try.intro"], agent=ag["name"]))}</p>
<ul>{"".join(lines)}</ul>
<p>{esc(T["try.notice"])}</p>
<p>{esc(T["try.close"])}</p>
<p><a href="{GUIDE_PATH[lang]}">{esc(T["try.guide"])}</a>{template_link(lang, a)}</p>
</section>"""


def template_link(lang, a):
    """GTM-175: «Its sandbox template», next to the guide link, to the agent's card on /sandbox/."""
    if not a.get("templates"):
        return ""
    import sandbox_section
    label = sandbox_section.texts()[lang]["its_template"]
    return f' · <a href="{sandbox_section.SECTION_PATH[lang]}#{esc(a["agent"]["id"])}">{esc(label)}</a>'


def company_of(a):
    v = a["agent"]["vendor"].split(" (")[0]
    return COMPANY.get(v, v)


def grid(lang, agents, *, family_label, status_html, last_html, href, more_html=None):
    """The company grid and the block of the rest. family_label(a), status_html(a), last_html(a) give the literals
    the web already uses; href(a) is the path of the published agent page, or None. more_html(a), if given, adds lines
    at the end of a product's row (GTM-223: its Control Baseline results); products without a row do not change."""
    T = texts()[lang]
    map_texts = map_page.load()[2]["texts"]
    cls = classes()
    date = calc_date(agents)
    by = {}
    for a in agents:
        by.setdefault(company_of(a), []).append(a)
    covered = sorted((c for c, items in by.items()
                      if any(x["agent"]["rosmarops"]["status"] in ("evaluated", "detected") for x in items)),
                     key=lambda c: COMPANY_NAME.get(c, c).lower())
    cards = []
    for c in covered:
        items = sorted(by[c], key=lambda x: (x["agent"]["rosmarops"]["status"] != "evaluated", x["agent"]["name"].lower()))
        lis = []
        for a in items:
            ag = a["agent"]
            name = esc(ag["name"])
            h = href(a)
            if h:
                name = f'<a href="{h}">{name}</a>'
            k = cls.get(ag["id"])
            if k:
                cl = f'<span class="co-cls">{esc(k)}</span><span>{esc(map_texts[lang]["class." + k])}</span>'
            else:
                cl = f'<span class="co-cls co-none">—</span><span class="co-meta">{esc(map_texts[lang]["nodata"])}</span>'
            extra = ""
            if evaluated(a):
                extra = strip(lang, a) + rec_box(lang, a, k, date, map_texts)
            lis.append(
                f'<li class="co-p" id="p-{esc(ag["id"])}"><span class="co-pn">{name}</span>'
                f'<span class="co-tag">{esc(family_label(a))}</span>'
                f'<span class="co-cl">{cl}</span>'
                f'<p class="co-meta">{status_html(a)}</p>'
                f'<p class="co-meta" data-last="{esc(ag["id"])}">{last_html(a)}</p>{extra}{more_html(a) if more_html else ""}</li>'
            )
        n = len(items)
        count = T["count.one"] if n == 1 else fill(T["count.many"], n=n)
        cards.append(f'<article class="co"><header><h3>{esc(COMPANY_NAME.get(c, c))}</h3><span class="co-n">{esc(count)}</span></header>'
                     f'<ul class="co-list">{"".join(lis)}</ul></article>')
    rest = []
    for c in sorted((c for c in by if c not in covered), key=str.lower):
        items = sorted(by[c], key=lambda x: x["agent"]["name"].lower())

        def named(a, text):
            h = href(a)
            return f'<a href="{h}">{esc(text)}</a>' if h else esc(text)

        if len(items) == 1 and c.lower().startswith(items[0]["agent"]["name"].lower()):
            rest.append(named(items[0], c))
        else:
            rest.append(esc(c) + " (" + ", ".join(named(a, a["agent"]["name"]) for a in items) + ")")
    rest_html = ""
    if rest:
        rest_html = (f'\n<div class="co-rest"><p class="co-k">{esc(T["rest_label"])}</p>'
                     f'<p>{" · ".join(rest)}</p></div>')
    return (f'<p class="co-k">{esc(T["grid_label"])}</p>\n<div class="co-grid">\n' + "\n".join(cards) + "\n</div>" + rest_html)
