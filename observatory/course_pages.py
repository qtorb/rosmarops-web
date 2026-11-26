"""GTM-206: lesson 2 of the course, «The chain», in EN, ES and CA.

/course/the-chain/, /es/curso/la-cadena/ and /ca/curs/la-cadena/, from observatory/data/course/the-chain.json
(literal texts signed by Albert; see its _source). Same shell as the topic pages (the sandbox guide of each
language). Design: vigil docs/research/2026-11-24-curso-leccion-2-diseno.md §1-§4, with its CSS and script in
site/assets/course/.

Not published yet (§5): noindex, no link from any page or menu, not in the sitemap or llms.txt.
"""

import html
import json
import re
from pathlib import Path

import sandbox_section
from topic_pages import BASE, FORBIDDEN, LANGS, switch_langs

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "observatory" / "data" / "course" / "the-chain.json"
DOWNLOAD = {"en": "/download?from=course", "es": "/es/descargar?from=course", "ca": "/ca/descarregar?from=course"}
GLOSS = {"en": "/glossary/", "es": "/es/glosario/", "ca": "/ca/glossari/"}
TERMS = ROOT / "tools" / "glossary" / "terms.json"
ASSET_V = "1"


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(s):
    """**x** is bold and `x` is code, as in the signed texts."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for y in x:
            yield from strings(y)
    elif isinstance(x, dict):
        for y in x.values():
            yield from strings(y)


def check(data):
    for lang in LANGS:
        for s in strings(data[lang]):
            m = FORBIDDEN.search(s)
            if m:
                raise ValueError(f"{lang}: forbidden word {m.group(0)!r} in {s!r}")


def glossary_anchor(tid, lang):
    for t in json.loads(TERMS.read_text(encoding="utf-8"))["terms"]:
        if t["id"] == tid:
            return t.get("anchors", {}).get(lang, tid)
    raise KeyError(tid)


def piece(t):
    P = t["piece"]
    L = P["links"]
    small = [L[0][2], P["small2"]["allow"], L[2][2], L[3][2]]

    def tag(k):
        sid = ' id="cs-s2"' if k == 1 else ""
        return (f'<button type="button" class="cs-tag" aria-pressed="{"true" if k == 0 else "false"}">'
                f'<span class="cs-l">{esc(L[k][0])}</span><span class="cs-t">{esc(L[k][1])}</span>'
                f'<span class="cs-s"{sid}>{esc(small[k])}</span></button>')

    def arr(label, ident=""):
        i = f' id="{ident}"' if ident else ""
        tid = f' id="{ident}t"' if ident else ""
        return f'<div class="cs-arr"{i} aria-hidden="true"><i></i><span{tid}>{esc(label)}</span></div>'

    A = P["a"]
    pills = "".join(
        f'<button type="button" class="cs-pill" role="radio" aria-checked="{"true" if k == "allow" else "false"}" '
        f'tabindex="{"0" if k == "allow" else "-1"}" data-a="{k}">{esc(A[k])}</button>' for k in ("allow", "ask", "deny"))
    d = P["detail"][0]
    det = (f'<span class="cs-l">{esc(L[0][0])}</span><h3>{esc(L[0][1])}</h3><dl>'
           + "".join(f"<dt>{esc(q)}</dt><dd>{fmt(a)}</dd>" for q, a in d) + "</dl>")
    return f"""<div class="doc"><h2>{esc(P["title"])}</h2><p class="sub">{esc(P["instr"])}</p></div>
<section class="cs-piece" aria-label="{esc(P["title"])}">
<div class="cs-chain">
{tag(0)}
{arr(P["arrows"]["can"])}
{tag(1)}
{arr(P["arrows"]["reaches"], "cs-a23")}
{tag(2)}
{arr(P["arrows"]["opens"])}
{tag(3)}
</div>
<div class="cs-below"><div>
<div class="cs-ctl"><div><p class="cs-q" id="cs-la">{esc(P["a_label"])}</p><div class="cs-pills" id="cs-a" role="radiogroup" aria-labelledby="cs-la">{pills}</div></div>
<div><p class="cs-q" id="cs-lb">{esc(P["b_label"])}</p><div class="cs-swrow"><button type="button" class="cs-sw" id="cs-b" role="switch" aria-checked="false" aria-labelledby="cs-lb"></button><span id="cs-bt" aria-hidden="true">{esc(P["b"]["no"])}</span></div></div></div>
<div class="cs-msg whole" id="cs-msg" role="status" aria-live="polite">{fmt(P["msg"]["allow0"])}</div></div>
<aside class="cs-det" id="cs-det" aria-live="polite">{det}</aside></div>
</section>
<p class="cs-note doc">{esc(P["note"])}</p>"""


def idea(t):
    I = t["idea"]
    cards = "".join(f'<div class="cs-c"><span class="cs-l">{esc(c[0])}</span><h3>{esc(c[1])}</h3><p>{fmt(c[2])}</p></div>'
                    for c in I["cards"])
    blocks = "".join(f"<h3>{esc(h)}</h3><ul>" + "".join(f"<li>{fmt(x)}</li>" for x in lines) + "</ul>"
                     for h, lines in I["blocks"])
    return f"""<div class="doc"><h2>{esc(I["title"])}</h2><p class="sub">{esc(I["sub"])}</p></div>
<div class="cs-cards">{cards}</div>
<div class="doc cs-blocks">{blocks}</div>"""


def game(t):
    G = t["game"]
    return f"""<div class="doc cs-quiz"><h2>{esc(G["title"])}</h2><p class="sub">{esc(G["sub"])}</p>
<p class="cs-q">{esc(G["header"])}</p>
<div id="cs-game"></div></div>"""


def exercise(t, lang):
    E = t["exercise"]
    steps = []
    for k, s in enumerate(E["steps"]):
        extra = (f'<br><a class="cs-btn primary" data-star-block href="{esc(DOWNLOAD[lang])}" target="_blank" rel="nofollow noopener">'
                 f'{esc(E["download"])}</a>') if k == 0 else ""
        steps.append(f"<li>{fmt(s)}{extra}</li>")
    intro = f"<p>{esc(E['intro'])}</p>" if E["intro"] else ""
    return f"""<div class="doc"><h2>{esc(E["title"])}</h2><p class="sub">{esc(E["sub"])}</p>
<div class="cs-piece cs-ex">{intro}<ol>{"".join(steps)}</ol>
<h3>{esc(E["none_title"])}</h3><p>{fmt(E["none"])}</p></div></div>"""


def test(t):
    Q = t["test"]
    return f"""<div class="doc cs-quiz"><h2>{esc(Q["title"])}</h2>
<div id="cs-test"></div></div>"""


def close(t, lang):
    C = t["close"]
    links = " · ".join(f'<a href="{GLOSS[lang]}#{esc(glossary_anchor(tid, lang))}">{esc(name)}</a>' for name, tid in C["terms"])
    return f"""<div class="doc cs-terms"><h2>{esc(C["terms_label"])}</h2><p>{links}</p>
<p class="cs-note">{esc(C["footer"])}</p></div>"""


def script_data(t):
    keep = {k: t[k] for k in ("piece", "game", "test")}
    return json.dumps(keep, ensure_ascii=False).replace("</", "<\\/")


def page_html(lang, data):
    t, paths = data[lang], data["path"]
    style, header, footer, scripts = sandbox_section.shell_parts(lang)
    header = header.replace(' aria-current="page"', "")
    url = BASE + paths[lang]
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{p}">\n' for l, p in paths.items())
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE}{paths["en"]}">\n'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(t["title"])} · RosmarOps</title>
<meta name="description" content="{esc(t["lead"])}">
<link rel="canonical" href="{url}">
{alts}{style.strip()}
<link rel="stylesheet" href="/assets/course/chain.css?v={ASSET_V}">
</head>
<body>
{switch_langs(header, lang, paths)}

<main class="course"><div class="wrap">
<div class="doc"><p class="eyebrow">{esc(t["eyebrow"])}</p><h1>{esc(t["title"])}</h1>
<p class="lead">{esc(t["lead"])}</p></div>
{piece(t)}
{idea(t)}
{game(t)}
{exercise(t, lang)}
{test(t)}
{close(t, lang)}
</div></main>

{switch_langs(footer, lang, paths)}
<script type="application/json" id="cs-data">{script_data(t)}</script>
<script src="/assets/course/chain.js?v={ASSET_V}" defer></script>
{scripts}
</body>
</html>
"""


def pages(data):
    import star_card  # GTM-206: the GitHub star card under the download button
    check(data)
    return {data["path"][lang]: star_card.apply(page_html(lang, data), lang) for lang in LANGS}


def build(site=SITE, data=None):
    data = load() if data is None else data
    for path, text in pages(data).items():
        f = Path(site) / path.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return data


if __name__ == "__main__":
    build()
