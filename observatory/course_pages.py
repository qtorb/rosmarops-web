"""GTM-206, GTM-227: the public course, in EN, ES and CA.

- Lesson 1, «The inspector»: /course/the-inspector/, /es/curso/el-inspector/, /ca/curs/linspector/, from
  observatory/data/course/the-inspector.json.
- Lesson 2, «The chain»: /course/the-chain/, /es/curso/la-cadena/, /ca/curs/la-cadena/, from
  observatory/data/course/the-chain.json.
- The course entry page: /course/, /es/curso/, /ca/curs/, from observatory/data/course/course.json. Its title is the
  course name, which is not decided: while `name` is empty the entry page is not written and no lesson links to it.

Texts are literal from the documents Albert signed (see each file's _source). Both lessons follow the same six steps.
Design: vigil docs/research/2026-11-26-curso-diseno-entrada-y-seis-pasos.md, on top of the lesson 2 design
(docs/research/2026-11-24-curso-leccion-2-diseno.md). Same shell as the topic pages (the sandbox guide of each
language); styles and script in site/assets/course/.

Not published yet: noindex, no link from any other page or menu, not in the sitemap or llms.txt.
"""

import html
import json
import re
from pathlib import Path

import sandbox_section
from topic_pages import BASE, FORBIDDEN, LANGS, switch_langs

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIR = ROOT / "observatory" / "data" / "course"
DATA = DIR / "the-chain.json"
LESSONS = ("the-inspector", "the-chain")
DOWNLOAD = {"en": "/download?from=course", "es": "/es/descargar?from=course", "ca": "/ca/descarregar?from=course"}
GLOSS = {"en": "/glossary/", "es": "/es/glosario/", "ca": "/ca/glossari/"}
TERMS = ROOT / "tools" / "glossary" / "terms.json"
CATALOG = ROOT / "observatory" / "i18n"
ASSET_V = "2"


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(s):
    """**x** is bold and `x` is code, as in the signed texts."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_all():
    """{"the-inspector": …, "the-chain": …, "course": …}"""
    return {name: load(DIR / f"{name}.json") for name in LESSONS + ("course",)}


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
            if lang == "en" and ("«" in s or "»" in s):
                raise ValueError(f"en: quotes in English pages are “ ” (design §6): {s!r}")


def glossary_anchor(tid, lang):
    for t in json.loads(TERMS.read_text(encoding="utf-8"))["terms"]:
        if t["id"] == tid:
            return t.get("anchors", {}).get(lang, tid)
    raise KeyError(tid)


def long_date(iso, lang):
    c = json.loads((CATALOG / f"{lang}.json").read_text(encoding="utf-8"))
    y, m, d = iso.split("-")
    return c["common.date"].replace("{day}", str(int(d))).replace("{month}", c["common.months"][int(m) - 1]).replace("{year}", y)


def entry_ready(entry):
    return bool(entry and entry.get("name"))


# ---------------------------------------------------------------- the six steps

def step(n, t, body, extra=""):
    return (f'<section class="cs-step" id="p{n}"{extra}><div class="doc"><p class="cs-label">{esc(t["labels"][n - 1])}</p></div>\n'
            f"{body}\n</section>")


def title(h, sub=""):
    s = f'<h2 class="cs-st">{esc(h)}</h2>'
    if sub:
        s += f'<p class="sub">{esc(sub)}</p>'
    return s


def index(t):
    items = "".join(f'<li><a href="#p{k + 1}"><b>{k + 1}</b>{esc(lab.split(" · ", 1)[1])}</a></li>'
                    for k, lab in enumerate(t["labels"]))
    return f'<ol class="cs-steps" aria-label="{esc(t["steps_aria"])}">{items}</ol>'


def todo(label, items, cls=""):
    lis = "".join(f"<li>{fmt(x)}</li>" for x in items)
    return f'<p class="cs-do">{esc(label)}</p><ol class="cs-todo{cls}">{lis}</ol>'


def seen(s):
    h, items = s
    return (f'<div class="cs-seen"><h3>{esc(h)}</h3><ul>' + "".join(f"<li>{fmt(x)}</li>" for x in items) + "</ul></div>")


def step1(t):
    ps = "".join(f"<p><b>{esc(b)}</b>{'' if rest.startswith(',') else ' '}{fmt(rest)}</p>" for b, rest in t["before"])
    return step(1, t, f'<div class="doc"><div class="cs-before">{ps}</div></div>')


def step2(t):
    I = t["idea"]
    paras = "".join(f"<p>{fmt(p)}</p>" for p in I["para"])
    cards = "".join(f'<div class="cs-c"><span class="cs-l">{esc(c[0])}</span><h3>{esc(c[1])}</h3><p>{fmt(c[2])}</p></div>'
                    for c in I["cards"])
    blocks = "".join(f"<h3>{esc(h)}</h3><ul>" + "".join(f"<li>{fmt(x)}</li>" for x in lines) + "</ul>"
                     for h, lines in I["blocks"])
    return step(2, t, f"""<div class="doc">{title(I["title"], I["sub"])}<div class="cs-para">{paras}</div></div>
<div class="cs-cards">{cards}</div>
<div class="doc cs-blocks">{blocks}</div>""")


# Lesson 1, step 3: «Who decides?»

def rows(M, mode):
    return "".join(
        f'<div class="cs-row"><div class="cs-act"><span class="cs-num">{k + 1}</span><span>{esc(a)}</span></div>'
        f'<span class="cs-mtag {M["states"][mode][k]}">{esc(M["tags"][M["states"][mode][k]])}</span></div>'
        for k, a in enumerate(M["actions"]))


def modes_piece(Y, lang):
    M = Y["modes"]
    btns = "".join(
        f'<button type="button" class="cs-pill" role="radio" aria-checked="{"true" if k == "manual" else "false"}" '
        f'tabindex="{"0" if k == "manual" else "-1"}" data-m="{k}">{esc(M["buttons"][k])}</button>' for k in ("manual", "auto", "bypass"))
    note = M["note"].replace("{fecha de la comprobación}", long_date(M["checked"], lang))
    return f"""<div class="cs-try"><div class="cs-how">{todo(Y["do_label"], Y["do"])}</div>
<div class="cs-piece cs-who" aria-label="{esc(Y["title"])}" role="group">
<p class="cs-q" id="cs-ml">{esc(M["label"])}</p>
<div class="cs-pills" id="cs-modes" role="radiogroup" aria-labelledby="cs-ml">{btns}</div>
<div class="cs-rows" id="cs-rows" aria-live="polite">{rows(M, "manual")}</div>
<p class="cs-msg manual" id="cs-mmsg" role="status">{fmt(M["msg"]["manual"])}</p>
<p class="cs-fixed">{fmt(M["fixed"])}</p>
</div></div>
<div class="doc"><p class="cs-note">{esc(note)}</p>
{seen(Y["seen"])}</div>"""


# Lesson 2, step 3: «Break the chain»

def chain_piece(Y):
    P = Y["piece"]
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
    return f"""<div class="doc">{todo(Y["do_label"], Y["do"])}</div>
<section class="cs-piece" aria-label="{esc(Y["title"])}">
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
<div class="doc"><p class="cs-note">{esc(P["note"])}</p>
{seen(Y["seen"])}</div>"""


def step3(t, lang):
    Y = t["try"]
    body = f'<div class="doc">{title(Y["title"], Y["sub"])}</div>\n'
    body += modes_piece(Y, lang) if "modes" in Y else chain_piece(Y)
    return step(3, t, body)


def step4(t):
    C = t["check"]
    G, Q = C["game"], C["test"]
    intro = f'<p class="cs-intro">{fmt(C["intro"])}</p>' if C["intro"] else ""
    first = "cs-st" if not intro else "cs-st cs-after"
    return step(4, t, f"""<div class="doc cs-quiz">{intro}<h2 class="{first}">{esc(G["title"])}</h2><p class="sub">{esc(G["sub"])}</p>
<p class="cs-q">{esc(G["header"])}</p>
<div id="cs-game"></div></div>
<div class="doc cs-quiz"><h2>{esc(Q["title"])}</h2>
<div id="cs-test"></div></div>""")


def link_text(text, link):
    """The text with the linked phrase as a link."""
    phrase, href = link
    before, after = text.split(phrase, 1)
    return f'{fmt(before)}<a href="{esc(href)}">{esc(phrase)}</a>{fmt(after)}'


def step5(t, lang):
    E = t["computer"]
    items = []
    for s in E["steps"]:
        h = fmt(s["do"])
        if "link" in s:
            star = " data-star-block" if s.get("star") else ""
            h += (f'<br><a class="cs-btn primary"{star} href="{esc(s["link"][1])}" target="_blank" rel="nofollow noopener">'
                  f'{esc(s["link"][0])}</a>')
        if "see" in s:
            h += f'<p class="cs-see"><b>{esc(E["see_label"])}</b> {fmt(s["see"])}</p>'
        if "see_list" in s:
            h += '<ul class="cs-see-list">' + "".join(f"<li>{fmt(x)}</li>" for x in s["see_list"]) + "</ul>"
        for a in s.get("after", []):
            h += f'<p class="cs-also">{link_text(a["text"], a["link"]) if "link" in a else fmt(a["text"])}</p>'
        items.append(f"<li>{h}</li>")
    intro = f"<p>{esc(E['intro'])}</p>" if E["intro"] else ""
    return step(5, t, f"""<div class="doc"><p class="sub cs-st5">{fmt(E["sub"])}</p>
<div class="cs-piece cs-ex">{intro}<ol>{"".join(items)}</ol>
<h3>{esc(E["none_title"])}</h3><p>{fmt(E["none"])}</p></div></div>""")


def step6(t, lang, target):
    C = t["take"]
    items = "".join(f"<li>{fmt(x)}</li>" for x in C["items"])
    links = " · ".join(f'<a href="{GLOSS[lang]}#{esc(glossary_anchor(tid, lang))}">{esc(name)}</a>' for name, tid in C["terms"])
    btn = f'<p class="cs-next"><a class="cs-btn primary" href="{esc(target)}">{esc(C["button"])}</a></p>' if target else ""
    return step(6, t, f"""<div class="doc"><ul class="cs-take">{items}</ul></div>
<div class="doc cs-terms"><h2>{esc(C["terms_label"])}</h2><p>{links}</p>
{btn}<p class="cs-note">{esc(C["footer"])}</p></div>""")


def script_data(t):
    Y, C = t["try"], t["check"]
    keep = {"game": C["game"], "test": C["test"]}
    if "modes" in Y:
        keep["modes"] = {k: v for k, v in Y["modes"].items() if k not in ("note", "checked", "fixed", "label", "buttons")}
    else:
        keep["piece"] = Y["piece"]
    return json.dumps(keep, ensure_ascii=False).replace("</", "<\\/")


def head(lang, paths, t_title, desc):
    style, header, footer, scripts = sandbox_section.shell_parts(lang)
    header = header.replace(' aria-current="page"', "")
    url = BASE + paths[lang]
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{p}">\n' for l, p in paths.items())
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE}{paths["en"]}">\n'
    top = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{esc(t_title)} · RosmarOps</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
{alts}{style.strip()}
<link rel="stylesheet" href="/assets/course/chain.css?v={ASSET_V}">
</head>
<body>
{switch_langs(header, lang, paths)}
"""
    return top, switch_langs(footer, lang, paths), scripts


def lesson_html(lang, data, target):
    t, paths = data[lang], data["path"]
    top, footer, scripts = head(lang, paths, t["title"], t["lead"])
    return f"""{top}
<main class="course"><div class="wrap">
<div class="doc"><p class="eyebrow">{esc(t["eyebrow"])}</p><h1>{esc(t["title"])}</h1>
<p class="lead">{esc(t["lead"])}</p>
{index(t)}</div>
{step1(t)}
{step2(t)}
{step3(t, lang)}
{step4(t)}
{step5(t, lang)}
{step6(t, lang, target)}
</div></main>

{footer}
<script type="application/json" id="cs-data">{script_data(t)}</script>
<script src="/assets/course/chain.js?v={ASSET_V}" defer></script>
{scripts}
</body>
</html>
"""


# Kept for the name the GTM-206 tests and README use.
def page_html(lang, data, target=None):
    return lesson_html(lang, data, target)


def entry_html(lang, entry, lessons):
    """The course entry page (design §4). Built only when the course name is set."""
    t, paths = entry[lang], entry["path"]
    name = entry["name"] if isinstance(entry["name"], str) else entry["name"][lang]
    top, footer, scripts = head(lang, paths, name, t["lead"])
    l1 = lessons["the-inspector"]["path"][lang]
    links = [l1, lessons["the-chain"]["path"][lang]]

    def soon(s):
        m = re.fullmatch(r"(.*?)\s*(\*\([^)]*\)\*|\([^)]*\))$", s)
        if not m:
            return fmt(s)
        return f'{fmt(m.group(1))} <span class="cs-soon">{esc(m.group(2).strip("*"))}</span>'

    who = "".join(f"<li>{fmt(x)}</li>" for x in t["who"][1])
    outs = "".join(f"<li>{soon(x)}</li>" for x in t["outcomes"][1])
    need = "".join(f"<li>{fmt(x)}</li>" for x in t["need"][1])
    cards = []
    for k, (h, txt) in enumerate(t["lessons"][1]):
        inner = f'<span class="cs-num">{k + 1}</span><span class="cs-lt"><b>{esc(h)}</b><span>{fmt(txt)}</span></span>'
        if k < len(links):
            cards.append(f'<a class="cs-lesson" href="{esc(links[k])}">{inner}</a>')
        else:
            cards.append(f'<div class="cs-lesson">{inner}<span class="cs-pill-soon">{esc(t["soon_pill"])}</span></div>')
    return f"""{top}
<main class="course"><div class="wrap"><div class="doc cs-entry">
<p class="eyebrow">{esc(t["eyebrow"])}</p><h1>{esc(name)}</h1>
<p class="lead">{esc(t["lead"])}</p>
<h2>{esc(t["example"][0])}</h2><p class="cs-big">{fmt(t["example"][1])}</p>
<h2>{esc(t["who"][0])}</h2><ul>{who}</ul>
<h2>{esc(t["outcomes"][0])}</h2><ol class="cs-todo">{outs}</ol>
<div class="cs-cards cs-two"><div class="cs-c"><h3>{esc(t["need"][0])}</h3><ul>{need}</ul></div>
<div class="cs-c"><h3>{esc(t["time"][0])}</h3><p>{fmt(t["time"][1])}</p></div></div>
<h2>{esc(t["start"][0])}</h2><p>{fmt(t["start"][1])}</p>
<p class="cs-next"><a class="cs-btn primary" href="{esc(l1)}">{esc(t["start"][2])}</a></p>
<h2>{esc(t["lessons"][0])}</h2><div class="cs-lessons">{"".join(cards)}</div>
<p class="cs-foot">{esc(t["footer"])}</p>
</div></div></main>

{footer}
{scripts}
</body>
</html>
"""


def pages(data=None):
    """{path: html} of every page to publish. data: load_all(), or the lesson 2 data alone (GTM-206 tests)."""
    import star_card  # GTM-206: the GitHub star card under the download button
    every = load_all()
    if data is not None and "path" in data:
        every["the-chain"] = data
    elif data is not None:
        every.update(data)
    entry = every["course"]
    out = {}
    targets = {"the-inspector": every["the-chain"]["path"], "the-chain": entry["path"] if entry_ready(entry) else None}
    for name in LESSONS:
        d = every[name]
        check(d)
        for lang in LANGS:
            to = targets[name][lang] if targets[name] else None
            out[d["path"][lang]] = star_card.apply(lesson_html(lang, d, to), lang)
    if entry_ready(entry):
        check(entry)
        for lang in LANGS:
            out[entry["path"][lang]] = entry_html(lang, entry, every)
    return out


def build(site=SITE, data=None):
    for path, text in pages(data).items():
        f = Path(site) / path.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return data


if __name__ == "__main__":
    build()
