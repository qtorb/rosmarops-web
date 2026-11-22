"""GTM-198: three standing pages that answer a real question in their first sentence, in EN, ES and CA.

/agent-orchestrators/, /claude-code-subagents/ and /mcp-servers/ (and their ES and CA addresses), from
observatory/data/topic-pages.json. Same shell as the sandbox guide; the text-page style (.doc). Each page carries
TechArticle, FAQPage (its own question, answered by its first sentence) and BreadcrumbList. Its video, if one is
public (observatory/data/videos/, GTM-199), goes at the top, loaded only when the person presses play, with its
VideoObject.
"""

import html
import json
import re
from pathlib import Path

import sandbox_section
import videos_pages

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "observatory" / "data" / "topic-pages.json"
BASE = "https://rosmarops.com"
LANGS = ("en", "es", "ca")
HOME = {"en": "/", "es": "/es/", "ca": "/ca/"}
DOWNLOAD = {"en": "/download", "es": "/es/descargar/", "ca": "/ca/descarregar/"}
FORBIDDEN = re.compile(r"\b(safe|safely|secure|securely|protects?|protected|seguro|segura|protege|protegido|segur|protegeix|no telemetry|sin telemetr\w*|sense telemetr\w*)\b", re.I)
DOC_CSS = """.doc{max-width:760px;display:flex;flex-direction:column;gap:18px;font-size:18px;line-height:1.65}
.doc h1{margin:0;font-size:clamp(30px,5vw,44px);line-height:1.12;font-weight:700;letter-spacing:-.02em}
.doc h2{margin:20px 0 0;font-size:22px;line-height:1.3}
.doc p,.doc ul,.doc ol{margin:0}.doc ul,.doc ol{padding-left:22px;display:flex;flex-direction:column;gap:8px}
.doc .tp-first{font-size:20px;line-height:1.55;color:var(--ink2)}
.doc code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.92em;overflow-wrap:anywhere}
.tp-video{margin:8px 0 0;display:flex;flex-direction:column;gap:8px}
.tp-video img{display:block;width:100%;height:auto;border-radius:12px;border:1px solid var(--line)}
.tp-video figcaption{font-size:15px;color:var(--muted)}
.tp-more{border-top:1px solid var(--line);padding-top:20px}"""


def esc(s):
    return html.escape(s, quote=True)


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(data):
    """Stops the build if a text is missing, says a forbidden word or a page doesn't open with its answer."""
    for pid, p in data["pages"].items():
        for lang in LANGS:
            t = p[lang]
            for k in ("title", "desc", "first"):
                if not t.get(k, "").strip():
                    raise ValueError(f"topic page {pid}/{lang}: {k} is empty")
            if not t["sections"] or any(not s["h2"].strip() or not "".join(s["body"]).strip() for s in t["sections"]):
                raise ValueError(f"topic page {pid}/{lang}: a section is empty")
            blob = " ".join([t["title"], t["desc"], t["first"],
                             *(x for s in t["sections"] for x in [s["h2"], *s["body"]]),
                             *(l[0] for l in t["links"])])
            m = FORBIDDEN.search(re.sub(r"<[^>]+>", " ", blob))
            if m:
                raise ValueError(f"topic page {pid}/{lang}: forbidden word «{m.group(0)}»")


def body(lang, pid, page, data):
    t, L = page[lang], data["labels"][lang]
    out = [f'<article class="doc"><h1>{esc(t["title"])}</h1>', f'<p class="tp-first">{esc(t["first"])}</p>']
    v = videos_pages.top_video(videos_pages.load(), pid)  # GTM-199: the page's video at the top, loaded on click
    if v:
        out.append(videos_pages.player(v, lang))
    for s in t["sections"]:
        out.append(f'<h2>{esc(s["h2"])}</h2>')
        out += s["body"]
    links = "".join(f'<li><a href="{esc(h)}">{esc(x)}</a></li>' for x, h in t["links"])
    links += f'<li><a href="{DOWNLOAD[lang]}">{esc(L["download"])}</a></li>'
    out.append(f'<section class="tp-more"><h2>{esc(L["more"])}</h2><ul>{links}</ul></section>')
    out.append(f'<p>{esc(L["closing"])}</p></article>')
    return "\n".join(out)


def ld(lang, pid, page, data):
    t = page[lang]
    url = BASE + page["path"][lang]
    org = {"@type": "Organization", "name": "RosmarOps", "url": BASE + "/"}
    graph = [
        {"@type": "TechArticle", "@id": url + "#article", "headline": t["title"], "description": t["desc"],
         "inLanguage": lang, "url": url, "mainEntityOfPage": url, "author": org, "publisher": org,
         "about": {"@type": "Thing", "name": page["about"]},
         "mentions": [{"@type": "SoftwareApplication", "name": n} for n in page["mentions"]],
         "isPartOf": {"@id": BASE + "/#website"}},
        {"@type": "FAQPage", "@id": url + "#faq", "inLanguage": lang, "url": url,
         "mainEntity": [{"@type": "Question", "name": t["title"],
                         "acceptedAnswer": {"@type": "Answer", "text": t["first"]}}]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": data["labels"][lang]["home"], "item": BASE + HOME[lang]},
            {"@type": "ListItem", "position": 2, "name": t["title"], "item": url}]},
    ]
    v = videos_pages.top_video(videos_pages.load(), pid)
    if v:
        graph.append(videos_pages.video_object(v, lang))
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def switch_langs(block, lang, paths):
    for o, p in paths.items():
        if o != lang:
            block = re.sub(r'<a href="[^"]*" hreflang="%s"' % o, f'<a href="{p}" hreflang="{o}"', block)
    return block


def page_html(lang, pid, page, data):
    style, header, footer, scripts = sandbox_section.shell_parts(lang)
    t, paths = page[lang], page["path"]
    url = BASE + paths[lang]
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{p}">\n' for l, p in paths.items())
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE}{paths["en"]}">\n'
    # The guide's own header marks «Sandbox» as the current page; here no item is.
    header = header.replace(' aria-current="page"', "")
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(t["title"])} · RosmarOps</title>
<meta name="description" content="{esc(t["desc"])}">
<link rel="canonical" href="{url}">
{alts}<meta property="og:type" content="article">
<meta property="og:site_name" content="RosmarOps">
<meta property="og:title" content="{esc(t["title"])} · RosmarOps">
<meta property="og:description" content="{esc(t["desc"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/brand/rosmarops-social.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld(lang, pid, page, data)}</script>
{style.strip()}
<style>
{DOC_CSS}
{videos_pages.CSS}
</style>
</head>
<body>
{switch_langs(header, lang, paths)}

<main><div class="wrap">
{body(lang, pid, page, data)}
</div></main>

{switch_langs(footer, lang, paths)}
{scripts}
{videos_pages.SCRIPT if videos_pages.top_video(videos_pages.load(), pid) else ""}
</body>
</html>
"""


def pages(data):
    check(data)
    return {p["path"][lang]: page_html(lang, pid, p, data) for pid, p in data["pages"].items() for lang in LANGS}


def sitemap_urls(data):
    """(path, {lang: path}) for sitemap-pages.xml, with hreflang between the three languages."""
    return [(p["path"][l], p["path"]) for p in data["pages"].values() for l in LANGS]


def llms_lines(data):
    """One line per page for llms.txt (EN), with the question as the link text."""
    return [f"- [{p['en']['title']}]({BASE}{p['path']['en']}): {p['en']['first']}" for p in data["pages"].values()]


def build(site=SITE, data=None):
    data = load() if data is None else data
    for path, text in pages(data).items():
        f = Path(site) / path.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return data
