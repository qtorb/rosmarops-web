#!/usr/bin/env python3
"""GTM-138: the Observatory map page, hidden (noindex, out of the sitemap, linked from nowhere).

Data: observatory/data/map/exposure-potential.json and factory-scores.json, the assets of the latest release of
qtorb/rosmarops, copied by the release workflow (sample-captures.yml) and checked against the release by
agent_lists.py check. Texts: observatory/i18n/map.json (signed). Called by observatory/build.py; nothing is written
by hand from the data.

  python3 observatory/map_page.py fetch [TAG]   copy the two assets of TAG (default: the latest release)
  python3 observatory/map_page.py check         every inputs code has a phrase in the three languages
"""

import html
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_DATA = ROOT / "observatory" / "data" / "map"
MAP_TEXTS = ROOT / "observatory" / "i18n" / "map.json"
ASSETS = ("exposure-potential.json", "factory-scores.json")
MAP_PATH = {"en": "/observatory/ai-agent-map/", "es": "/es/observatorio/mapa-agentes-ia/", "ca": "/ca/observatori/mapa-agents-ia/"}
DOWNLOAD = {"en": "/download", "es": "/es/descargar", "ca": "/ca/descarregar"}
AXES = ["autonomy", "reach", "contagion", "delegation", "opacity", "complexity"]
TIE = ["autonomy", "reach", "contagion", "delegation", "opacity"]  # vigil 2026-11-12-mapa-paso-3-en-ca-y-frases.md §A
# Card «Who decides» (GTM-138, rule 13): action -> codes that mean it does it (autonomy, or contagion for changing
# other agents) and its delegation code.
ACTIONS = [
    ("reads_files", ("autonomy", ("reads_files:machine",)), "reads_files:model"),
    ("writes_files", ("autonomy", ("writes_files",)), "writes_files:model"),
    ("runs_commands", ("autonomy", ("runs_commands",)), "runs_commands:model"),
    ("sends_out", ("autonomy", ("sends_out",)), "sends_out:model"),
    ("changes_other_agents", ("contagion", ("C3:config", "C3:instructions")), "changes_other_agents:model"),
]
# Product id in the release JSON -> agent file in observatory/data/agents (program-agents.json says the same).
AGENT_FILE = {"hermes": "hermes-agent"}
MONTHS = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "ca": ["de gener", "de febrer", "de març", "d'abril", "de maig", "de juny", "de juliol", "d'agost", "de setembre", "d'octubre", "de novembre", "de desembre"],
}


def esc(s):
    return html.escape(str(s), quote=True)


def load():
    data = {name: json.loads((MAP_DATA / name).read_text(encoding="utf-8")) for name in ASSETS}
    texts = json.loads(MAP_TEXTS.read_text(encoding="utf-8"))
    return data["exposure-potential.json"], data["factory-scores.json"], texts


def fmt_date(iso, lang):
    y, m, d = (int(x) for x in iso[:10].split("-"))
    if lang == "en":
        return f"{d} {MONTHS['en'][m - 1]} {y}"
    if lang == "ca":
        return f"{d} {MONTHS['ca'][m - 1]} de {y}"
    return f"{d} de {MONTHS['es'][m - 1]} de {y}"


def missing_phrases(ep, phrases):
    """Codes in inputs with no phrase in some language (the page shows no phrase; the test fails)."""
    out = set()
    for a in ep["agents"]:
        for ax in (a.get("axes") or {}).values():
            for c in ax.get("inputs") or []:
                if any(not (phrases.get(c) or {}).get(l) for l in ("es", "en", "ca")):
                    out.add(c)
    return sorted(out)


def phrase(code, lang, phrases):
    return (phrases.get(code) or {}).get(lang)


def top_phrase(agent, weights, lang, phrases):
    """The phrase that weighs most: axes with data by weight x level, ties by TIE; the first code of the first axis
    with level > 0. None if no axis is above 0 (or the code has no phrase yet)."""
    axes = [(k, v) for k, v in (agent.get("axes") or {}).items() if v.get("level") is not None]
    axes.sort(key=lambda kv: (-weights.get(kv[0], 1) * kv[1]["level"], TIE.index(kv[0]) if kv[0] in TIE else len(TIE)))
    for _, v in axes:
        if v["level"] > 0 and v.get("inputs"):
            return phrase(v["inputs"][0], lang, phrases)
    return None


def axis_example(agents, axis, names, lang, phrases):
    """The agent with the highest level on that axis (ties: product name, alphabetically), with its first code."""
    best = [a for a in agents if a.get("evaluated") and ((a.get("axes") or {}).get(axis) or {}).get("level")]
    best.sort(key=lambda a: (-a["axes"][axis]["level"], names[a["product"]].lower()))
    for a in best:
        codes = a["axes"][axis].get("inputs") or []
        if codes and phrase(codes[0], lang, phrases):
            return names[a["product"]], phrase(codes[0], lang, phrases)
    return None


def decider(agent, action):
    """'model', 'nobody' or 'you' for one action of the card (rule 13)."""
    _, (axis, codes), model = action
    axes = agent.get("axes") or {}
    if model in ((axes.get("delegation") or {}).get("inputs") or []):
        return "model"
    if any(c in ((axes.get(axis) or {}).get("inputs") or []) for c in codes):
        return "nobody"
    return "you"


def agent_names(agents_files, lang):
    """Display names from the agent files, with the scored-list names of program-agents.json in that language."""
    prog = json.loads((ROOT / "observatory" / "data" / "program-agents.json").read_text(encoding="utf-8"))
    over = prog.get("scored_list_names", {})
    out = {}
    for a in agents_files:
        out[a["id"]] = over.get(a["id"], {}).get(lang, a["name"])
    return out


def ordered(ep, scores):
    """Rows: class D to A, then factory score (most exposed first), then name."""
    rank = {"D": 0, "C": 1, "B": 2, "A": 3}
    return sorted([a for a in ep["agents"] if a.get("evaluated")],
                  key=lambda a: (rank.get(a.get("class"), 9), scores.get(a["product"], {}).get("score", 101), a["product"]))


def i_help(uid, text, label):
    return (f'<button class="mi" type="button" aria-expanded="false" aria-controls="{uid}" aria-label="{esc(label)}">'
            f'<span aria-hidden="true">i</span></button><span class="mi-t" id="{uid}" hidden>{esc(text)}</span>')


def body(lang, t_site, agents_files):
    ep, fs, cat = load()
    T = cat["texts"][lang]
    phrases = cat["phrases"]
    scores = {a["product"]: a for a in fs["agents"]}
    files = {a["id"]: a for a in agents_files}
    names_by_file = agent_names(agents_files, lang)
    names = {a["product"]: names_by_file.get(AGENT_FILE.get(a["product"], a["product"]), a["product"]) for a in ep["agents"]}
    version = ep["rosmarops_version"].lstrip("v")
    kv = dict(x.split("@", 1) for x in ep.get("knowledge_version", "").split(";") if "@" in x)
    il = T["i.label"]

    def t(key, **kw):
        s = T[key]
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    out = []
    data_line = esc(t("b1.data", version=version, date=fmt_date(ep["generated_at"], lang)))
    uses = "".join(f'<li><b>{esc(T[f"for.{n}.h"])}</b> {esc(T[f"for.{n}"])}</li>' for n in (1, 2, 3))
    case = f'''<section class="m-band m-alt" aria-labelledby="m-case-h"><div class="m-wrap">
<figure class="m-case">
<span class="m-eyebrow" id="m-case-h">{esc(T["b2.eyebrow"])}</span>
<div class="m-turn"><span class="m-who m-you" aria-label="{esc(T["b2.who.you"])}">{esc(T["b2.who.you"][:2])}</span><p>{esc(T["b2.you"])}</p></div>
<div class="m-turn"><span class="m-who m-ai" aria-label="{esc(T["b2.who.agent"])}">IA</span><p>{esc(T["b2.agent1"])}</p></div>
<div class="m-turn"><span class="m-who m-judge" aria-label="{esc(T["b2.who.agent"])}">IA</span><p>{esc(T["b2.agent2"])} {i_help("mi-cls", T["b2.agent2.i"], il)}</p></div>
<p class="m-fine">{esc(t("b2.caption", date=fmt_date(kv.get("claude-code", ep["generated_at"]), lang)))}</p>
<p class="m-closing">{esc(T["b2.closing"])}</p>
</figure>
</div></section>'''
    # 3: the ranking.
    legend = "".join(f'<span class="m-lg"><span class="m-cls m-{c}" aria-hidden="true">{c}</span>{esc(T["class." + c])}</span>' for c in "ABCD")
    rows = []
    for i, a in enumerate(ordered(ep, scores)):
        p = a["product"]
        n = names[p]
        c = a.get("class", "")
        sc = scores.get(p, {}).get("score")
        axes = a.get("axes") or {}
        bars = []
        for k in AXES:
            lv = (axes.get(k) or {}).get("level")
            an = T["axis_name." + k]
            if lv is None:
                bars.append(f'<span class="m-ax"><small>{esc(an)}</small><span class="m-bar m-nd" role="img" aria-label="{esc(an)}: {esc(T["nodata"])}"></span></span>')
            else:
                bars.append(f'<span class="m-ax"><small>{esc(an)}</small><span class="m-bar" role="img" aria-label="{esc(an)}: {lv}/3"><i style="width:{round(lv / 3 * 100)}%"></i></span></span>')
        top = top_phrase(a, ep.get("weights", {}), lang, phrases)
        why = f'<span class="m-why">{esc(top[0].upper() + top[1:])}.</span>' if top else ""
        prov = ""
        if a.get("class_status") == "provisional" and a.get("missing_axes"):
            miss = ", ".join(T["axis_name." + m].lower() for m in a["missing_axes"])
            prov = f'<span class="m-prov">{esc(t("b3.provisional", axes=miss))}</span>'
        score = f'<span class="m-score"><small>{esc(t("b3.score", score="").split("/")[0].strip())}</small>{sc}<small>/100</small></span>' if sc is not None else '<span class="m-score"></span>'
        # Card.
        does = "".join(f"<li>{esc(phrase(code, lang, phrases)[0].upper() + phrase(code, lang, phrases)[1:])}</li>"
                       for code in ((axes.get("autonomy") or {}).get("inputs") or []) if phrase(code, lang, phrases))
        who = "".join(f'<li><span>{esc(T["action." + act[0]])}</span><span class="m-pill m-p-{decider(a, act)}">{esc(T["decider." + decider(a, act)])}</span></li>' for act in ACTIONS)
        card = f'''<div class="m-detail" id="m-d{i}" hidden>
<h3>{esc(t("b5.title", agent=n, **{"class": c}))}</h3>
<h4>{esc(T["b5.does"])}</h4><ul class="m-does">{does}</ul>
<h4>{esc(T["b5.who"])}</h4><ul class="m-whol">{who}</ul>
<!-- GTM-138: b5.shares, b5.fix*, the reserve line and b5.sources wait for the engine (texts in observatory/i18n/map.json). -->
</div>'''
        rows.append(f'''<button class="m-row" type="button" aria-expanded="false" aria-controls="m-d{i}"><span class="m-cls m-{c}" aria-label="{esc(t("b3.class", **{"class": c}))}">{c}</span><span class="m-name"><b>{esc(n)}</b>{why}{prov}</span><span class="m-axes">{"".join(bars)}</span>{score}</button>
{card}''')
    # 1-5 (GTM-138, second block): what it measures, what it's for, the notice, the data line and the map, then the case.
    out.append(f'''<section class="m-wrap m-top" aria-labelledby="m-h1">
<div class="m-stack">
<span class="m-eyebrow">{esc(T["b1.eyebrow"])}</span>
<h1 id="m-h1">{esc(T["b1.h1"])}</h1>
<p class="m-lead">{esc(T["b1.lead"])}</p>
</div>
<div class="m-for"><span class="m-eyebrow">{esc(T["for.eyebrow"])}</span><ul class="m-uses">{uses}</ul></div>
<p class="m-notice">{esc(T["b1.notice"])}</p>
<p class="m-fine">{data_line} {i_help("mi-ref", T["b1.data.i"], il)}</p>
<div class="m-stack m-map" aria-label="{esc(T["b3.h2"])}">
<div class="m-legend">{legend}</div>
<div class="m-list">
{chr(10).join(rows)}
</div>
<p class="m-fine">{esc(T["b3.footnote"])} {i_help("mi-foot", T["b3.footnote.i"], il)}</p>
</div>
</section>''')
    out.append(case)

    # 4: the six axes.
    cards = []
    for k in AXES:
        ex = axis_example(ep["agents"], k, names, lang, phrases)
        exl = f'<span class="m-ex">{esc(t("b4.example", agent=ex[0], phrase=ex[1]))}</span>' if ex else ""
        cards.append(f'<div class="m-card"><h3>{esc(T["axis_name." + k])}</h3><p>{esc(T["axis." + k])}</p>{exl}</div>')
    out.append(f'''<section class="m-band" aria-labelledby="m-h4"><div class="m-wrap m-stack">
<span class="m-eyebrow">{esc(T["b4.eyebrow"])}</span>
<h2 id="m-h4">{esc(T["b4.h2"])}</h2>
<div class="m-grid3">{"".join(cards)}</div>
<p class="m-fine">{esc(T["b4.caption"])}</p>
</div></section>''')

    # 6: patterns, without links until each article exists.
    pats = "".join(f'<div class="m-card"><h3>{esc(T[f"b6.p{n}.h"])}</h3><p>{esc(T[f"b6.p{n}"])}</p></div>' for n in (1, 2, 3))
    out.append(f'''<section class="m-band m-alt" aria-labelledby="m-h6"><div class="m-wrap m-stack">
<span class="m-eyebrow">{esc(T["b6.eyebrow"])}</span>
<h2 id="m-h6">{esc(T["b6.h2"])}</h2>
<div class="m-grid3">{pats}</div>
</div></section>''')

    # 7: check yours.
    out.append(f'''<section class="m-band" aria-labelledby="m-h7"><div class="m-wrap">
<div class="m-cta"><div class="m-stack"><h2 id="m-h7">{esc(T["b7.h2"])}</h2><p>{esc(T["b7.text"])}</p></div>
<div class="m-ctab"><a class="m-btn" href="{DOWNLOAD[lang]}?from=observatory-map" target="_blank" rel="nofollow noopener">{esc(T["b7.button"])}</a><small>{esc(T["b7.line"])}</small></div></div>
</div></section>''')

    # 8: method and limits. «Detected but not measured» only when the JSON has agents that were not evaluated.
    not_eval = [a for a in ep["agents"] if not a.get("evaluated")]
    ne = ""
    if not_eval:
        lst = ", ".join(names.get(a["product"], a["product"]) for a in not_eval)
        ne = f'<p class="m-fine">{esc(t("b8.notevaluated", list=lst))}</p>'
    data_url = f'https://github.com/qtorb/rosmarops/releases/download/{esc(ep["rosmarops_version"])}/exposure-potential.json'
    out.append(f'''<section class="m-band m-alt" aria-labelledby="m-h8"><div class="m-wrap m-stack">
<h2 id="m-h8">{esc(T["b8.h2"])}</h2>
<p class="m-lead">{esc(T["b8.text"])}</p>
{ne}<p class="m-fine">{esc(T["b8.complexity"])}</p>
<p class="m-fine m-links"><a href="{esc(t_site.text("site.nav.methodology_url"))}">{esc(T["b8.method"])}</a> · <a href="{data_url}">{esc(T["b8.data"])}</a></p>
</div></section>''')
    return T, "\n".join(out)


CSS = """
/* GTM-138: the map page. Measures of vigil docs/research/2026-11-09-mapa-boceto-paso-2.html, light mode only. */
main>.wrap{max-width:none;padding:0}
.m-top,.m-band{line-height:1.55}
.m-wrap{max-width:1080px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.m-band{padding-block:64px}.m-alt{background:#EEECE7}
.m-eyebrow{font-size:13px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:#66635D}
main h1,main h2,main h3{margin:0;text-wrap:balance;letter-spacing:-.01em}
main .m-band h2{font-size:clamp(24px,3.2vw,34px);line-height:1.15;font-weight:800}
main h3{font-size:19px;line-height:1.3}
main p{margin:0}
.m-lead{font-size:clamp(18px,2vw,20px);color:#3A3833;max-width:62ch}
.m-stack{display:flex;flex-direction:column;gap:16px}
.m-fine{font-size:14px;color:#66635D}
.m-notice{background:#FFFFFF;border:1px solid #E3E0D8;border-radius:12px;padding:16px;font-size:15px;color:#3A3833}
.m-top{display:flex;flex-direction:column;gap:24px;padding-top:40px;padding-bottom:64px}
.m-top h1{font-size:clamp(32px,5vw,52px);line-height:1.06;font-weight:800}
.m-for{display:flex;flex-direction:column;gap:12px}
.m-uses{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:0;padding:0;list-style:none}
.m-uses li{background:#FFFFFF;border:1px solid #E3E0D8;border-radius:14px;padding:18px;font-size:16px;color:#3A3833}
.m-uses b{display:block;color:#1B1A18;font-size:17px;margin-bottom:4px}
.m-map{margin-top:8px}
.m-case{max-width:720px}
.m-case{margin:0;background:#FFFFFF;border:1px solid #E3E0D8;border-radius:16px;padding:22px;display:flex;flex-direction:column;gap:14px}
.m-turn{display:grid;grid-template-columns:28px minmax(0,1fr);gap:12px;align-items:start}
.m-turn p{font-size:16px;color:#3A3833}
.m-who{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:800}
.m-you{background:#E9E6DF;color:#1B1A18}.m-ai{background:#2346B8;color:#FFFFFF}.m-judge{background:#FBF0D9;color:#8A5A00}
.m-closing{font-size:16px;font-weight:600}
.mi{display:inline-grid;place-items:center;width:20px;height:20px;padding:0;border:1.5px solid currentColor;border-radius:50%;background:none;color:#3A3833;font:700 12px/1 system-ui,sans-serif;cursor:pointer;vertical-align:1px}
.mi:focus-visible{outline:3px solid #2346B8;outline-offset:2px}
.mi-t{display:block;margin-top:8px;padding:10px 12px;background:#FFFFFF;border:1px solid #E3E0D8;border-radius:10px;font-size:14px;color:#3A3833}
.mi-t[hidden]{display:none}
.m-legend{display:flex;flex-wrap:wrap;gap:10px 20px;align-items:center;font-size:14px;color:#3A3833}
.m-lg{display:inline-flex;align-items:center;gap:8px}
.m-cls{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:9px;font-weight:800;font-size:17px;flex:none}
.m-D{background:#A3361F;color:#FFFFFF}.m-C{background:#FBEAE5;color:#A3361F}.m-B{background:#FBF0D9;color:#8A5A00}.m-A{background:#E7EFE9;color:#3F5E49}
.m-list{background:#FFFFFF;border:1px solid #E3E0D8;border-radius:16px;overflow:hidden}
.m-row{display:grid;grid-template-columns:48px minmax(0,1.3fr) minmax(0,2.2fr) 96px;gap:16px;align-items:center;padding:14px 20px;width:100%;border:0;border-top:1px solid #E3E0D8;background:none;font:inherit;color:inherit;text-align:left;cursor:pointer}
.m-list>.m-row:first-child{border-top:0}
.m-row:hover{background:#F6F5F2}
.m-row:focus-visible{outline:3px solid #2346B8;outline-offset:-3px}
.m-name b{display:block;font-size:17px}.m-why{display:block;font-size:14px;color:#3A3833}.m-prov{display:block;font-size:12px;color:#66635D;margin-top:2px}
.m-axes{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}
.m-ax{display:flex;flex-direction:column;gap:4px;min-width:0}
.m-ax small{font-size:11px;color:#66635D;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.m-bar{display:block;height:8px;border-radius:4px;background:#E9E6DF;overflow:hidden}.m-bar i{display:block;height:100%;background:#3A3833}
.m-nd{background:repeating-linear-gradient(45deg,#E9E6DF 0 4px,transparent 4px 8px);border:1px solid #E3E0D8}
.m-score{font-variant-numeric:tabular-nums;font-weight:800;font-size:20px;text-align:right}.m-score small{display:block;font-weight:400;font-size:12px;color:#66635D}
.m-detail{padding:16px 20px 22px 84px;border-top:1px dashed #E3E0D8;background:#F6F5F2}
.m-detail[hidden]{display:none}
.m-detail h4{margin:16px 0 6px;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:#66635D}
.m-does{margin:0;padding-left:20px;font-size:15px;color:#3A3833;max-width:640px}
.m-whol{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px;max-width:640px}
.m-whol li{display:flex;justify-content:space-between;gap:12px;font-size:15px;border-bottom:1px solid #E3E0D8;padding-bottom:6px}
.m-pill{font-size:12px;font-weight:700;padding:3px 9px;border-radius:999px;white-space:nowrap}
.m-p-model{background:#FBF0D9;color:#8A5A00}.m-p-nobody{background:#FBEAE5;color:#A3361F}.m-p-you{background:#E7EFE9;color:#3F5E49}
.m-grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.m-card{background:#FFFFFF;border:1px solid #E3E0D8;border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:8px}
.m-card p{color:#3A3833;font-size:16px}.m-ex{font-size:14px;color:#66635D}
.m-cta{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px 32px;align-items:center;background:#1B1A18;color:#F6F5F2;border-radius:16px;padding:28px}
main .m-cta h2{color:#F6F5F2}.m-cta p{color:#D9D5CC}
.m-ctab{display:flex;flex-direction:column;gap:8px;align-items:flex-start}
.m-btn{display:inline-flex;align-items:center;min-height:44px;padding:12px 20px;border-radius:10px;font-weight:700;text-decoration:none;background:#F6F5F2;color:#1B1A18}
.m-btn:hover{color:#1B1A18}.m-btn:focus-visible{outline:3px solid #9DB2FF;outline-offset:3px}
.m-ctab small{font-size:14px;color:#B9B4AA}
.m-links a{color:#2346B8}
@media (max-width:820px){
.m-uses,.m-grid3,.m-cta{grid-template-columns:1fr}
.m-row{grid-template-columns:40px minmax(0,1fr) 72px;gap:12px}
.m-row .m-axes{grid-column:1 / -1}
.m-detail{padding-left:20px}
}
"""

SCRIPT = """<script>
/* GTM-138: each row opens its card; each «i» opens its text. Stores and sends nothing. */
document.addEventListener('click', function (e) {
  var b = e.target.closest && e.target.closest('.m-row, .mi');
  if (!b) return;
  var el = document.getElementById(b.getAttribute('aria-controls'));
  if (!el) return;
  var open = b.getAttribute('aria-expanded') !== 'true';
  b.setAttribute('aria-expanded', String(open));
  el.hidden = !open;
});
</script>"""


def fetch(tag=None):
    api = "https://api.github.com/repos/qtorb/rosmarops/releases/" + (f"tags/{tag}" if tag else "latest")
    rel = json.loads(urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "RosmarOps-Observatory/1"}), timeout=60).read())
    got = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    MAP_DATA.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        if name not in got:
            raise SystemExit(f"release {rel['tag_name']} has no {name}")
        req = urllib.request.Request(got[name], headers={"User-Agent": "RosmarOps-Observatory/1"})
        (MAP_DATA / name).write_bytes(urllib.request.urlopen(req, timeout=60).read())
    print(f"map data: {', '.join(ASSETS)} of {rel['tag_name']}")


def main(argv):
    if argv[:1] == ["fetch"]:
        fetch(argv[1] if len(argv) > 1 else None)
    elif argv[:1] == ["check"]:
        ep, _, cat = load()
        miss = missing_phrases(ep, cat["phrases"])
        for c in miss:
            print(f"::error::inputs code {c} has no phrase in observatory/i18n/map.json (the map shows its row without one)")
        sys.exit(1 if miss else 0)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
