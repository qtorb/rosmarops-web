#!/usr/bin/env python3
"""RosmarOps observatory: static page generator.

Reads observatory/data/agents/*.json (validated in CI against
observatory/schema/observatory.v1.schema.json) and the fixed-text catalogs
observatory/i18n/{en,es,ca}.json, and writes:

  site/observatory/              index (EN)
  site/es/observatorio/          index (ES)
  site/ca/observatori/           index (CA)
  site/<lang path>/<id>/         agent page, only if the agent has at least
                                 one entry in `changes` or `ratings`
  site/observatory/<id>.json     each agent file, unchanged
  site/observatory/data.json     all agents in one file

Every page carries noindex while this lives on the `observatory` branch
(NOINDEX below). Nothing here touches sitemaps or llms.txt.

Standard library only. Run from the repository root:  python3 observatory/build.py
"""

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "observatory" / "data" / "agents"
I18N = ROOT / "observatory" / "i18n"
SITE = ROOT / "site"
BASE = "https://rosmarops.com"

# Index pages: indexable since GTM-11 (2026-10-28). Agent pages stay noindex until verified (see AGENT_PAGES_NOINDEX).
NOINDEX = False

LANGS = ["en", "es", "ca"]
INDEX_PATH = {"en": "/observatory/", "es": "/es/observatorio/", "ca": "/ca/observatori/"}
OG_LOCALE = {"en": "en_GB", "es": "es_ES", "ca": "ca_ES"}
LANG_NAME = {"en": "English", "es": "Español", "ca": "Català"}
JSON_BASE = "/observatory/"


# ---------------------------------------------------------------- inputs

def load_catalogs():
    cats = {l: json.loads((I18N / f"{l}.json").read_text(encoding="utf-8")) for l in LANGS}
    keys = {l: set(k for k in c if not k.startswith("_")) for l, c in cats.items()}
    for l in LANGS[1:]:
        missing = keys["en"] - keys[l]
        extra = keys[l] - keys["en"]
        if missing or extra:
            sys.exit(f"catalog {l}.json differs from en.json: missing {sorted(missing)}, extra {sorted(extra)}")
    return cats


def load_agents():
    agents = []
    for f in sorted(DATA.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["agent"]["id"] != f.stem:
            sys.exit(f"{f.name}: agent.id {d['agent']['id']!r} does not match the file name")
        agents.append(d)
    if not agents:
        sys.exit("no agent files found")
    rank = {"evaluated": 0, "detected": 1, "not_supported": 2}

    def key(a):
        r = a["agent"]["rosmarops"]
        v = tuple(int(x) for x in r.get("since_version", "0.0.0").split("."))
        return (rank[r["status"]], tuple(-x for x in v), a["agent"]["name"].lower())

    return sorted(agents, key=key)


# ---------------------------------------------------------------- helpers

def esc(s):
    return html.escape(str(s), quote=True)


class T:
    """Catalog lookup for one language. Values are plain text; fill() escapes the inserted values."""

    def __init__(self, cat):
        self.c = cat

    def raw(self, key):
        if key not in self.c:
            sys.exit(f"missing catalog key {key!r}")
        return self.c[key]

    def __call__(self, key, **kw):
        s = esc(self.raw(key))
        for k, v in kw.items():
            s = s.replace("{" + k + "}", v if isinstance(v, Markup) else esc(v))
        return s

    def text(self, key, **kw):
        """Unescaped, for <title>, meta and JSON-LD (escaped later where needed)."""
        s = self.raw(key)
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def date(self, iso):
        y, m, d = iso.split("-")
        return self.text("common.date", day=str(int(d)), month=self.raw("common.months")[int(m) - 1], year=y)


class Markup(str):
    pass


def has_page(a):
    return any(a.get(k) for k in ("changes", "ratings", "capabilities", "storage", "default_mode"))


# Agent pages are generated for review whenever there is content, but stay noindex,
# unlinked and out of the deploy until their id is listed here (after product advisor verification).
PUBLISHED_AGENT_PAGES = {"claude-code", "cursor", "kanvas"}  # verified by the product advisor, ES/CA signed by Albert (2026-10-28)


def texts(a):
    """Every prose object in an agent file (schema v1.3: {en, es, ca})."""
    out = []
    for x in [a.get("default_mode")] + a.get("capabilities", []) + a.get("storage", []):
        if x and "note" in x:
            out.append(x["note"])
    for c in a["changes"]:
        out += [c["before"], c["after"]]
        if "correction" in c:
            out.append(c["correction"]["reason"])
    return out


def translated(a):
    return all(isinstance(t, dict) and all(t.get(l) for l in LANGS) for t in texts(a))


def is_published(a):
    # Never in any language until every text has en, es and ca (schema v1.3 rule).
    return has_page(a) and translated(a) and a["agent"]["id"] in PUBLISHED_AGENT_PAGES


def loc(text, lang):
    """(value, lang attribute) for a prose field; falls back to EN, marked, only on unpublished review pages."""
    if isinstance(text, str):
        return text, ("" if lang == "en" else ' lang="en"')
    if text.get(lang):
        return text[lang], ""
    return text["en"], ' lang="en"'


def agent_path(lang, aid):
    return f"{INDEX_PATH[lang]}{aid}/"


def date_modified(a):
    ds = [a["agent"]["reviewed_at"]]
    for c in a["changes"]:
        ds.append(c["date"])
        ds.append(c["verified"]["at"])
        if "correction" in c:
            ds.append(c["correction"]["at"])
    for v in a["versions"]:
        ds.append(v["released_at"])
    return max(ds)


def latest_change(a):
    return max(a["changes"], key=lambda c: (c["date"], c["id"])) if a["changes"] else None


def latest_version(a):
    return max(a["versions"], key=lambda v: (v["released_at"], v["version"]))["version"] if a["versions"] else None


def ld(obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + s.replace("</", "<\\/") + "</script>"


def software_app(a):
    ag = a["agent"]
    os_names = {"windows": "Windows", "macos": "macOS", "linux": "Linux", "web": "Web"}
    return {
        "@type": "SoftwareApplication",
        "name": ag["name"],
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": ", ".join(os_names[p] for p in ag["platforms"]),
        "author": {"@type": "Organization", "name": ag["vendor"]},
    }


# ---------------------------------------------------------------- page shell

CSS = """
:root{--bg:#F6F5F2;--ink:#1B1A18;--ink2:#3A3833;--muted:#66635D;--line:#E3E0D8;--card:#FFFFFF;--accent:#6F8F78}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--ink)}a:hover{color:var(--accent)}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
header .wrap{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:16px;padding-top:24px;padding-bottom:24px}
header img{height:40px;width:auto;display:block}
nav{display:flex;flex-wrap:wrap;gap:24px;font-size:16px}
nav a[aria-current]{font-weight:700;text-decoration:none}
main .wrap{display:flex;flex-direction:column;gap:56px;padding-top:48px;padding-bottom:64px}
.hero{display:flex;flex-direction:column;gap:20px;max-width:760px}
.eyebrow{margin:0;font-size:14px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{margin:0;font-size:clamp(34px,6vw,52px);line-height:1.08;font-weight:700;letter-spacing:-.02em}
.lead{margin:0;font-size:20px;line-height:1.55;color:var(--ink2)}
.actions{display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-flex;align-items:center;min-height:44px;padding:0 20px;border-radius:8px;font-size:16px;text-decoration:none;border:1px solid var(--ink)}
.btn.primary{background:var(--ink);color:#FFFFFF}.btn.primary:hover{background:var(--ink2);color:#FFFFFF}
.btn.secondary{background:transparent;color:var(--ink)}
section{display:flex;flex-direction:column;gap:16px}
h2{margin:0;font-size:26px;line-height:1.2}
h3{margin:0;font-size:18px}
.note{margin:0;font-size:15px;line-height:1.55;color:var(--muted)}
.box{background:var(--card);border:1px solid var(--line);border-radius:12px}
.tablebox{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:16px;min-width:760px;table-layout:fixed}
thead th{text-align:left;font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);padding:14px 16px;border-bottom:1px solid var(--line)}
tbody th{text-align:left;font-weight:700;padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.45}
td{padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:top;line-height:1.45}
tr:last-child td,tr:last-child th{border-bottom:0}
.changes{list-style:none;margin:0;padding:0}
.changes li{padding:16px;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:6px;line-height:1.5}
.changes li:last-child{border-bottom:0}
.changes .meta{margin:0;font-size:14px;color:var(--muted)}
.changes p{margin:0}
.empty{margin:0;padding:20px;font-size:16px;line-height:1.55;color:var(--ink2)}
.trio{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;padding:24px}
.trio div{display:flex;flex-direction:column;gap:8px}
.trio p{margin:0;font-size:16px;line-height:1.55;color:var(--ink2)}
.disclaimer{margin:0;font-size:14px;line-height:1.5;color:var(--muted)}
.crumbs{margin:0;font-size:14px;color:var(--muted);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.obs-brand{display:flex;align-items:center;gap:16px;margin:0 0 20px;font-size:22px;font-weight:700;letter-spacing:-.01em;line-height:1.2;color:var(--ink)}
.obs-brand img{display:block;width:64px;height:64px;flex:none}
.crumbs img{display:block;width:24px;height:24px;flex:none}
.layout{display:flex;flex-wrap:wrap;gap:40px;align-items:flex-start}
.toc{flex:1 1 200px;display:flex;flex-direction:column;gap:8px;font-size:15px}
.toc p{margin:0 0 4px;font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.article{flex:999 1 600px;min-width:0;display:flex;flex-direction:column;gap:40px}
.article h1{font-size:clamp(30px,5vw,44px);line-height:1.12}
.pagemeta{margin:0;font-size:15px;color:var(--muted)}
.panel{padding:20px;display:flex;flex-direction:column;gap:12px}
.panel p{margin:0;font-size:16px;line-height:1.55}
.plain li,td,.panel p{overflow-wrap:anywhere}
td.keep{overflow-wrap:normal;word-break:normal;hyphens:none}
td code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:14px;overflow-wrap:anywhere}
.panel code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.plain{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:8px;font-size:16px;line-height:1.5}
footer{border-top:1px solid var(--line)}
footer .wrap{padding-top:28px;padding-bottom:28px;font-size:15px;color:var(--muted)}
footer nav{gap:20px;font-size:15px}
@media (max-width:700px){.obs-brand{gap:12px;margin-bottom:16px;font-size:20px}.obs-brand img{width:48px;height:48px}
nav{gap:16px}main .wrap{gap:40px;padding-top:32px}.lead{font-size:18px}
table{min-width:0;table-layout:auto}colgroup,thead{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
table,tbody,tr,tbody th,td{display:block}
tbody tr{padding:16px;border-bottom:1px solid var(--line)}tbody tr:last-child{border-bottom:0}
tbody th{padding:0 0 8px;border:0;font-size:18px}
td{padding:4px 0;border:0;display:grid;grid-template-columns:minmax(110px,40%) 1fr;gap:12px;font-size:15px}
td::before{content:attr(data-label);font-size:13px;color:var(--muted)}
td:empty{display:none}}
""".strip()


def nav_links(t, lang, alternates, current_obs=True):
    current = ' aria-current="page"' if current_obs else ""
    parts = [
        f'<a href="{esc(t.text("site.nav.blog_url"))}">{t("site.nav.blog")}</a>',
        f'<a href="{esc(t.text("site.nav.about_url"))}">{t("site.nav.about")}</a>',
        f'<a href="{INDEX_PATH[lang]}"{current}>{t("site.nav.observatory")}</a>',
        f'<a href="{esc(t.text("site.nav.methodology_url"))}">{t("site.nav.methodology")}</a>',
        f'<a href="{esc(t.text("site.nav.faq_url"))}">{t("site.nav.faq")}</a>',
    ]
    for l in LANGS:
        if l != lang:
            parts.append(f'<a href="{alternates[l]}" hreflang="{l}" lang="{l}" aria-label="{LANG_NAME[l]}">{l.upper()}</a>')
    return "".join(parts)


def page(lang, t, *, path, title, description, alternates, jsonld, body, og_type="website", noindex=None):
    url = BASE + path
    head = [
        "<!doctype html>",
        f'<html lang="{lang}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
    ]
    if NOINDEX if noindex is None else noindex:
        head.append('<meta name="robots" content="noindex">')
    head.append(f'<link rel="canonical" href="{url}">')
    for l in LANGS:
        head.append(f'<link rel="alternate" hreflang="{l}" href="{BASE}{alternates[l]}">')
    head.append(f'<link rel="alternate" hreflang="x-default" href="{BASE}{alternates["en"]}">')
    head += [
        f'<meta property="og:type" content="{og_type}">',
        '<meta property="og:site_name" content="RosmarOps">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}">',
        '<meta property="og:image" content="https://rosmarops.com/assets/brand/observatory/observatory-social.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    head += [ld(j) for j in jsonld]
    head += [
        '<link rel="stylesheet" href="/assets/consent/cookieconsent.css?v=3.1.0">',
        '<link rel="icon" href="/assets/brand/observatory/observatory-favicon.ico" sizes="48x48">',
        '<link rel="icon" href="/assets/brand/observatory/observatory-favicon.svg" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="/assets/brand/observatory/observatory-apple-touch-180.png">',
        f"<style>\n{CSS}\n</style>",
        "</head>",
        "<body>",
    ]
    logo = (
        f'<a href="{esc(t.text("site.home_url"))}"><img src="/assets/brand/rosmarops-logo.png" '
        'srcset="/assets/brand/rosmarops-logo.png 1x, /assets/brand/rosmarops-logo@2x.png 2x" '
        f'width="512" height="131" alt="{t("site.logo_alt")}"></a>'
    )
    links = nav_links(t, lang, alternates)
    header = f'<header><div class="wrap">\n{logo}\n<nav>{links}</nav>\n</div></header>'
    footer = (
        '<footer><div class="wrap">\n<nav>'
        + links
        + f'<a href="{esc(t.text("site.footer.privacy_url"))}">{t("site.footer.privacy")}</a>'
        + f'<a href="#" data-cc="show-preferencesModal">{t("site.footer.cookies")}</a>'
        + "</nav>\n</div></footer>"
    )
    tail = [
        '<script src="/assets/consent/cookieconsent.umd.js?v=3.1.0" defer></script>',
        '<script src="/assets/consent/consent.js?v=2" defer></script>',
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(head) + "\n" + header + "\n\n<main><div class=\"wrap\">\n" + body + "\n</div></main>\n\n" + footer + "\n" + "\n".join(tail)


def write(path, content):
    out = SITE / path.lstrip("/")
    if path.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- index

def kinds_text(t, a):
    return t.raw("common.list_sep").join(t.text("kind." + k) for k in a["agent"]["kinds"])


def platforms_text(t, a):
    return t.raw("common.list_sep").join(t.text("platform." + p) for p in a["agent"]["platforms"])


def status_text(t, a):
    st = a["agent"]["rosmarops"]
    v = st.get("since_version", "")
    return t.text("status." + st["status"], version=v)


def change_item(t, lang, a, c, with_agent):
    ag = a["agent"]
    cat = t.text("category." + c["category"])
    if with_agent:
        label = ag["name"] + (" " + c["version"] if c.get("version") else "")
        meta = f'{esc(t.date(c["date"]))} · {esc(label)} · {esc(cat)}'
    elif c.get("version"):
        meta = t("agent.change_meta", date=t.date(c["date"]), version=c["version"], category=cat)
    else:
        meta = t("agent.change_meta_noversion", date=t.date(c["date"]), category=cat)
    if "correction" in c:
        meta += " · " + t("agent.corrected", date=t.date(c["correction"]["at"]), reason=loc(c["correction"]["reason"], lang)[0])
    src_label = t("agent.source_official") if c["source"]["official"] else t("agent.source_rosmarops")
    before, bl = loc(c["before"], lang)
    after, al = loc(c["after"], lang)
    verified = t("agent.verified", date=t.date(c["verified"]["at"]), how=t.text("how." + c["verified"]["how"]))
    name_link = ""
    if with_agent and is_published(a):
        name_link = f' <a href="{agent_path(lang, ag["id"])}">{esc(ag["name"])}</a> ·'
    return (
        "<li>"
        f'<p class="meta">{meta}</p>'
        f'<p><strong>{t("agent.before")}</strong> <span{bl}>{esc(before)}</span></p>'
        f'<p><strong>{t("agent.after")}</strong> <span{al}>{esc(after)}</span></p>'
        f'<p class="meta">{verified}{name_link} <a href="{esc(c["source"]["url"])}" rel="noopener">{src_label}</a></p>'
        "</li>"
    )


def item_list(lang, items):
    return [
        dict(
            {"@type": "ListItem", "position": i + 1, "item": software_app(a)},
            **({"url": BASE + agent_path(lang, a["agent"]["id"])} if is_published(a) else {}),
        )
        for i, a in enumerate(items)
    ]


def build_index(lang, t, agents):
    path = INDEX_PATH[lang]
    reviewed = max(a["agent"]["reviewed_at"] for a in agents)
    modified = max(date_modified(a) for a in agents)
    title = t.text("index.title")
    desc = t.text("index.description")

    def is_tool(a):
        return "agent_tooling" in a["agent"]["kinds"]

    def table(items, first_col):
        cols = "<colgroup>" + "".join(f'<col style="width:{w}%">' for w in (15, 15, 21, 17, 16, 16)) + "</colgroup>"
        head = cols + (
            f'<thead><tr><th scope="col">{t(first_col)}</th><th scope="col">{t("index.th_vendor")}</th>'
            f'<th scope="col">{t("index.th_type")}</th><th scope="col">{t("index.th_platforms")}</th>'
            f'<th scope="col">{t("index.th_rosmarops")}</th><th scope="col">{t("index.th_last_change")}</th></tr></thead>'
        )
        return f'<div class="box tablebox"><table>\n{head}\n<tbody>\n' + "\n".join(row(a) for a in items) + "\n</tbody>\n</table></div>"

    def row(a):
        ag = a["agent"]
        name = esc(ag["name"])
        if is_published(a):
            name = f'<a href="{agent_path(lang, ag["id"])}">{name}</a>'
        lc = latest_change(a)
        last = (
            f'{esc(t.date(lc["date"]))} · {esc(t.text("category." + lc["category"]))}' if lc else t("index.no_change")
        )
        return (
            "<tr>"
            f'<th scope="row">{name}</th>'
            f'<td data-label="{t("index.th_vendor")}">{esc(ag["vendor"])}</td>'
            f'<td data-label="{t("index.th_type")}">{esc(kinds_text(t, a))}</td>'
            f'<td data-label="{t("index.th_platforms")}">{esc(platforms_text(t, a))}</td>'
            f'<td data-label="{t("index.th_rosmarops")}">{esc(status_text(t, a))}</td>'
            f'<td data-label="{t("index.th_last_change")}">{last}</td>'
            "</tr>"
        )

    agent_list = [a for a in agents if not is_tool(a)]
    tool_list = [a for a in agents if is_tool(a)]
    tools_section = ""
    if tool_list:
        tools_section = f"""

<section aria-labelledby="tools">
<h2 id="tools">{t("index.tooling_h2")}</h2>
<p class="note">{t("index.tooling_note")}</p>
{table(tool_list, "index.th_tool")}
</section>"""

    all_changes = sorted(
        ((c, a) for a in agents for c in a["changes"]), key=lambda x: (x[0]["date"], x[0]["id"]), reverse=True
    )[:10]
    if all_changes:
        changes = '<ol class="changes box">' + "".join(change_item(t, lang, a, c, True) for c, a in all_changes) + "</ol>"
    else:
        changes = f'<p class="empty box">{t("index.changes_empty")}</p>'

    body = f"""<section class="hero">
<p class="obs-brand"><img src="/assets/brand/observatory/observatory-mark.svg" width="64" height="64" alt="">{t("site.observatory_brand")}</p>
<p class="eyebrow">{t("index.eyebrow", date=t.date(reviewed))}</p>
<h1>{t("index.h1")}</h1>
<p class="lead">{t("index.lead")}</p>
<div class="actions"><a class="btn primary" href="#method">{t("index.cta_method")}</a><a class="btn secondary" href="{JSON_BASE}data.json">{t("index.cta_data")}</a></div>
</section>

<section aria-labelledby="agents">
<h2 id="agents">{t("index.agents_h2")}</h2>
<p class="note">{t("index.agents_scope")}</p>
{table(agent_list, "index.th_agent")}
<p class="note">{t("index.status_note")}</p>
<p class="note">{t("index.pages_note")}</p>
</section>{tools_section}

<section aria-labelledby="changes">
<h2 id="changes">{t("index.changes_h2")}</h2>
{changes}
</section>

<section id="method" class="box trio" aria-label="{t("index.method_h3")}">
<div><h3>{t("index.method_h3")}</h3><p>{t("index.method_p")}</p></div>
<div><h3>{t("index.independence_h3")}</h3><p>{t("index.independence_p")}</p></div>
<div><h3>{t("index.data_h3")}</h3><p>{t("index.data_p")}</p><a href="{JSON_BASE}data.json">{t("index.data_link")}</a></div>
</section>

<p class="disclaimer">{t("common.disclaimer")}</p>"""

    url = BASE + path
    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "@id": BASE + INDEX_PATH["en"] + "#dataset",
            "name": title.split(" · ")[-1],
            "description": desc,
            "url": url,
            "inLanguage": lang,
            "dateModified": modified,
            "isAccessibleForFree": True,
            "creator": {"@type": "Organization", "@id": "https://rosmarops.com/#org", "name": "RosmarOps", "url": "https://rosmarops.com/"},
            "distribution": [
                {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + JSON_BASE + "data.json"}
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": t.text("index.agents_h2"),
            "numberOfItems": len(agent_list),
            "itemListElement": item_list(lang, agent_list),
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": t.text("index.breadcrumb_home"), "item": BASE + t.text("site.home_url")},
                {"@type": "ListItem", "position": 2, "name": t.text("site.nav.observatory"), "item": url},
            ],
        },
    ]
    if tool_list:
        jsonld.insert(2, {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": t.text("index.tooling_h2"),
            "numberOfItems": len(tool_list),
            "itemListElement": item_list(lang, tool_list),
        })
    write(path, page(lang, t, path=path, title=title, description=desc, alternates=INDEX_PATH, jsonld=jsonld, body=body))


# ---------------------------------------------------------------- agent page

def build_agent(lang, t, a):
    ag = a["agent"]
    path = agent_path(lang, ag["id"])
    alternates = {l: agent_path(l, ag["id"]) for l in LANGS}
    reviewed = t.date(ag["reviewed_at"])
    tool = "agent_tooling" in ag["kinds"]
    sfx = "_tool" if tool else ""
    title = t.text("agent.title" + sfx, agent=ag["name"])
    desc = t.text("agent.description" + sfx, agent=ag["name"], vendor=ag["vendor"], date=reviewed)
    st = ag["rosmarops"]
    rosm = t("agent.rosmarops_" + st["status"], version=st.get("since_version", ""))
    lv = latest_version(a)
    meta = t("agent.meta", vendor=ag["vendor"], kinds=kinds_text(t, a), date=reviewed)
    if lv:
        meta += " · " + t("agent.latest_version", version=lv)

    def note(x):
        if not x.get("note"):
            return "", ""
        v, attr = loc(x["note"], lang)
        return esc(v), attr

    def note_cell(x):
        v, attr = note(x)
        return f'<td data-label="{t("agent.th_note")}"{attr}>{v}</td>'

    def src_link(src):
        label = t("agent.source_official") if src["official"] else t("agent.source_rosmarops")
        return f'<a href="{esc(src["url"])}" rel="noopener">{label}</a>'

    mode_html = ""
    dm = a.get("default_mode")
    if dm:
        lines = [f'<p>{t("agent.mode_name", mode=Markup("<code>" + esc(dm["name"]) + "</code>"))}</p>',
                 f'<p>{t("agent.mode_who", who=t.text("who." + dm["who_decides"]))}</p>']
        if dm.get("since_version"):
            lines.append(f'<p>{t("agent.mode_since", agent=ag["name"], version=dm["since_version"])}</p>')
        if dm.get("note"):
            v, attr = note(dm)
            lines.append(f'<p class="note"{attr}>{v}</p>')
        lines.append(f'<p class="note">{src_link(dm["source"])} · {t("agent.accessed", date=t.date(dm["source"]["accessed_at"]))}</p>')
        mode_html = f'''<section id="mode" class="box panel" aria-labelledby="mode-h">
<h2 id="mode-h">{t("agent.mode_h2")}</h2>
{"".join(lines)}
</section>'''

    caps_html = ""
    if a.get("capabilities"):
        rows = "".join(
            "<tr>"
            f'<th scope="row">{t("action." + c["action"])}</th>'
            f'<td data-label="{t("agent.th_scope")}">{t("scope." + c["scope"])}</td>'
            f'<td class="keep" data-label="{t("agent.th_default")}">{t("default." + c["default"])}</td>'
            f'{note_cell(c)}'
            f'<td data-label="{t("agent.th_source")}">{src_link(c["source"])}</td>'
            "</tr>"
            for c in a["capabilities"]
        )
        cols = "<colgroup>" + "".join(f'<col style="width:{w}%">' for w in (15, 19, 15, 33, 18)) + "</colgroup>"
        caps_html = f'''<section id="capabilities" aria-labelledby="caps-h">
<h2 id="caps-h">{t("agent.caps_h2")}</h2>
<p class="note">{t("agent.caps_note")}</p>
<div class="box tablebox"><table>{cols}
<thead><tr><th scope="col">{t("agent.th_action")}</th><th scope="col">{t("agent.th_scope")}</th><th scope="col">{t("agent.th_default")}</th><th scope="col">{t("agent.th_note")}</th><th scope="col">{t("agent.th_source")}</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="note">{t("agent.caps_ask_note")}</p>
</section>'''

    storage_html = ""
    if a.get("storage"):
        rows = "".join(
            "<tr>"
            f'<th scope="row">{t("storage." + s["kind"])}</th>'
            f'<td data-label="{t("agent.th_path")}"><code>{esc(s["path_windows"])}</code></td>'
            f'<td data-label="{t("agent.th_keys")}">{t("secrets." + s["secrets"])}</td>'
            f'{note_cell(s)}'
            f'<td data-label="{t("agent.th_source")}">{src_link(s["source"])}</td>'
            "</tr>"
            for s in a["storage"]
        )
        cols = "<colgroup>" + "".join(f'<col style="width:{w}%">' for w in (16, 27, 14, 25, 18)) + "</colgroup>"
        storage_html = f'''<section id="storage" aria-labelledby="storage-h">
<h2 id="storage-h">{t("agent.storage_h2")}</h2>
<p class="note">{t("agent.storage_note")}</p>
<div class="box tablebox"><table>{cols}
<thead><tr><th scope="col">{t("agent.th_what")}</th><th scope="col">{t("agent.th_path")}</th><th scope="col">{t("agent.th_keys")}</th><th scope="col">{t("agent.th_note")}</th><th scope="col">{t("agent.th_source")}</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</section>'''

    changes = sorted(a["changes"], key=lambda c: (c["date"], c["id"]), reverse=True)
    history = (
        '<ol class="changes box">' + "".join(change_item(t, lang, a, c, False) for c in changes) + "</ol>"
        if changes
        else f'<p class="empty box">{t("agent.history_empty")}</p>'
    )

    versions_html = ""
    if a["versions"]:
        items = "".join(
            f'<li>{t("agent.version_line", version=v["version"], date=t.date(v["released_at"]))} · '
            f'<a href="{esc(v["source"]["url"])}" rel="noopener">{t("agent.source_official") if v["source"]["official"] else t("agent.source_rosmarops")}</a></li>'
            for v in sorted(a["versions"], key=lambda v: (v["released_at"], v["version"]), reverse=True)
        )
        versions_html = f'<section id="versions" aria-labelledby="versions-h"><h2 id="versions-h">{t("agent.versions_h2")}</h2><ul class="plain">{items}</ul></section>'

    sources = {}
    for c in a["changes"]:
        sources.setdefault(c["source"]["url"], c["source"])
    for v in a["versions"]:
        sources.setdefault(v["source"]["url"], v["source"])
    for x in [a.get("default_mode")] + a.get("capabilities", []) + a.get("storage", []):
        if x:
            sources.setdefault(x["source"]["url"], x["source"])
    src_items = "".join(
        f'<li><a href="{esc(u)}" rel="noopener">{esc(u)}</a> · {t("agent.accessed", date=t.date(s["accessed_at"]))}</li>'
        for u, s in sorted(sources.items())
    )
    src_items += f'<li><a href="{JSON_BASE}{ag["id"]}.json">{t("agent.json_link")}</a></li>'

    toc_items = []
    if mode_html:
        toc_items.append(("#mode", "agent.mode_h2"))
    if caps_html:
        toc_items.append(("#capabilities", "agent.caps_h2"))
    if storage_html:
        toc_items.append(("#storage", "agent.storage_h2"))
    toc_items += [("#rosmarops", "agent.rosmarops_h2" + sfx), ("#history", "agent.history_h2")]
    if versions_html:
        toc_items.append(("#versions", "agent.versions_h2"))
    toc_items += [("#sources", "agent.sources_h2"), ("#reply", "agent.reply_h2")]
    toc = "".join(f'<a href="{h}">{t(k)}</a>' for h, k in toc_items)

    body = f"""<div class="layout">
<nav class="toc" aria-label="{t("agent.toc")}"><p>{t("agent.toc")}</p>{toc}</nav>
<article class="article">
<section>
<p class="crumbs"><img src="/assets/brand/observatory/observatory-mark.svg" width="24" height="24" alt=""><a href="{INDEX_PATH[lang]}">{t("site.nav.observatory")}</a> › {esc(ag["name"])}</p>
<h1>{t("agent.h1" + sfx, agent=ag["name"])}</h1>
<p class="pagemeta">{meta}</p>
</section>
{mode_html}
{caps_html}
{storage_html}
<section id="rosmarops" class="box panel" aria-labelledby="rosmarops-h">
<h2 id="rosmarops-h">{t("agent.rosmarops_h2" + sfx)}</h2>
<p>{rosm}</p>
<div class="actions"><a class="btn primary" href="{esc(t.text("site.download_url"))}" target="_blank" rel="noopener">{t("agent.cta_download")}</a></div>
</section>

<section id="history" aria-labelledby="history-h">
<h2 id="history-h">{t("agent.history_h2")}</h2>
<p class="note">{t("agent.history_note")}</p>
{history}
</section>
{versions_html}
<section id="sources" aria-labelledby="sources-h">
<h2 id="sources-h">{t("agent.sources_h2")}</h2>
<ul class="plain">{src_items}</ul>
</section>

<section id="reply" aria-labelledby="reply-h">
<h2 id="reply-h">{t("agent.reply_h2")}</h2>
<p class="note">{t("agent.reply_empty")}</p>
<p class="note">{t("agent.report_error")} <a href="mailto:{esc(t.text("agent.report_email"))}">{t("agent.report_email")}</a></p>
</section>

<p class="disclaimer">{t("common.disclaimer")}</p>
</article>
</div>"""

    published = min([c["date"] for c in a["changes"]] or [ag["reviewed_at"]])
    url = BASE + path
    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "@id": url + "#article",
            "headline": t.text("agent.h1" + sfx, agent=ag["name"]),
            "description": desc,
            "inLanguage": lang,
            "datePublished": published,
            "dateModified": date_modified(a),
            "mainEntityOfPage": url,
            "about": software_app(a),
            "publisher": {"@type": "Organization", "@id": "https://rosmarops.com/#org", "name": "RosmarOps", "url": "https://rosmarops.com/"},
            "isBasedOn": BASE + JSON_BASE + ag["id"] + ".json",
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": t.text("index.breadcrumb_home"), "item": BASE + t.text("site.home_url")},
                {"@type": "ListItem", "position": 2, "name": t.text("site.nav.observatory"), "item": BASE + INDEX_PATH[lang]},
                {"@type": "ListItem", "position": 3, "name": ag["name"], "item": url},
            ],
        },
    ]
    write(path, page(lang, t, path=path, title=title, description=desc, alternates=alternates, jsonld=jsonld, body=body, og_type="article", noindex=not is_published(a)))


# ---------------------------------------------------------------- data files

SITEMAP = "sitemap-pages.xml"
SM_START, SM_END = "  <!-- observatory:start -->", "  <!-- observatory:end -->"


def build_sitemap(agents):
    """Keep the observatory index entries in site/sitemap-pages.xml, with the real lastmod."""
    f = SITE / SITEMAP
    if not f.exists():
        return
    lastmod = max(date_modified(a) for a in agents)
    alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{BASE}{INDEX_PATH[l]}"/>' for l in LANGS)
    alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}{INDEX_PATH["en"]}"/>'
    lines = [SM_START] + [f"  <url><loc>{BASE}{INDEX_PATH[l]}</loc><lastmod>{lastmod}</lastmod>{alts}</url>" for l in LANGS]
    for a in agents:
        if not is_published(a):
            continue
        aid = a["agent"]["id"]
        aalts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{BASE}{agent_path(l, aid)}"/>' for l in LANGS)
        aalts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}{agent_path("en", aid)}"/>'
        lines += [f"  <url><loc>{BASE}{agent_path(l, aid)}</loc><lastmod>{date_modified(a)}</lastmod>{aalts}</url>" for l in LANGS]
    lines += [SM_END]
    xml = f.read_text(encoding="utf-8")
    if SM_START in xml:
        xml = xml[: xml.index(SM_START)] + "\n".join(lines) + xml[xml.index(SM_END) + len(SM_END):]
    else:
        xml = xml.replace("</urlset>", "\n".join(lines) + "\n</urlset>")
    f.write_text(xml, encoding="utf-8")


LLMS = "llms.txt"
LL_START, LL_END = "<!-- observatory agents:start -->", "<!-- observatory agents:end -->"


def build_llms(agents, t_en):
    """Keep one llms.txt line per published agent page, between markers, after the observatory line."""
    f = SITE / LLMS
    if not f.exists():
        return
    txt = f.read_text(encoding="utf-8")
    lines = [LL_START]
    for a in agents:
        if is_published(a):
            ag = a["agent"]
            h1 = t_en.text("agent.h1_tool" if "agent_tooling" in ag["kinds"] else "agent.h1", agent=ag["name"])
            lines.append(f"- [{h1}]({BASE}{agent_path('en', ag['id'])}): observatory page, with its data at {BASE}{JSON_BASE}{ag['id']}.json")
    lines.append(LL_END)
    block = "\n".join(lines)
    if LL_START in txt:
        txt = txt[: txt.index(LL_START)] + block + txt[txt.index(LL_END) + len(LL_END):]
    else:
        anchor = "- Observatory: what each AI coding agent can do on your computer"
        i = txt.index(anchor)
        j = txt.index("\n", i)
        txt = txt[: j + 1] + block + "\n" + txt[j + 1:]
    f.write_text(txt, encoding="utf-8")


def build_data(agents):
    for a in agents:
        write(JSON_BASE + a["agent"]["id"] + ".json", json.dumps(a, ensure_ascii=False, indent=2) + "\n")
    write(JSON_BASE + "data.json", json.dumps({"schema_version": 1, "agents": agents}, ensure_ascii=False, indent=2) + "\n")


def main():
    global DATA, SITE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=DATA, help="folder with the agent JSON files")
    ap.add_argument("--out", type=Path, default=SITE, help="output root (default: site/)")
    args = ap.parse_args()
    DATA, SITE = args.data, args.out
    cats = load_catalogs()
    agents = load_agents()
    for p in INDEX_PATH.values():
        shutil.rmtree(SITE / p.strip("/"), ignore_errors=True)
    build_data(agents)
    build_sitemap(agents)
    build_llms(agents, T(cats["en"]))
    pages = 0
    for lang in LANGS:
        t = T(cats[lang])
        build_index(lang, t, agents)
        pages += 1
        for a in agents:
            if has_page(a):
                build_agent(lang, t, a)
                pages += 1
    print(f"observatory: {len(agents)} agents, {pages} pages, {len(agents) + 1} JSON files")


if __name__ == "__main__":
    main()
