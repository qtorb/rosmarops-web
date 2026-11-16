#!/usr/bin/env python3
"""GTM-175: the «Sandbox» section of rosmarops.com (/sandbox/, /es/sandbox/, /ca/sandbox/), generated from the agent files.

Data: the optional "templates" field of each agent file (schema v1.13; CTO-58 §5.4, with CTO-58 §1, CTO-59, CTO-60 and
qtorb/rosmarops-vigil docs/research/2026-11-16-gtm-175-lo-que-no-cubre.md). Texts: observatory/i18n/sandbox-section.json
(signed, literal). Page shell: the guide «How to try an AI agent in a test environment» of the same language, so the
section has its text width, headings and paragraphs. A template shows «Por revisar» when the latest raw file of the
collector says one of its pages lost a watched string (sources.json page-watch, GTM-175 §1). Called by build.py.

§2.3 «Try it without installing anything» is drawn only when the program's release ships sandbox-example.json
(BV-249 §6). No release does yet (0.12.1), so the page leaves it out.
"""

import html
import json
import re
from pathlib import Path

import company_page
import map_page
import sandbox_page

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TEXTS = ROOT / "observatory" / "i18n" / "sandbox-section.json"
SOURCES = ROOT / "observatory" / "sources.json"
RAW_DIR = ROOT / "observatory" / "raw"
LANGS = ("en", "es", "ca")
SECTION_PATH = {"en": "/sandbox/", "es": "/es/sandbox/", "ca": "/ca/sandbox/"}
GUIDE_FILE = {"en": "try-an-ai-agent/index.html", "es": "es/probar-un-agente-de-ia/index.html",
              "ca": "ca/provar-un-agent-dia/index.html"}
OBS_PATH = {"en": "/observatory/", "es": "/es/observatorio/", "ca": "/ca/observatori/"}
METHOD_PATH = {"en": "/methodology/", "es": "/es/metodologia/", "ca": "/ca/metodologia/"}
LOCALE = {"en": "en_US", "es": "es_ES", "ca": "ca_ES"}
DOWNLOAD = {
    "en": ("/download", "en", "Download from the Microsoft Store", "/macos/", "Mac (preview)", "/linux/"),
    "es": ("/es/descargar", "es", "Descargar desde Microsoft Store", "/es/macos/", "Mac (vista previa)", "/es/linux/"),
    "ca": ("/ca/descarregar", "ca", "Descarrega del Microsoft Store", "/ca/macos/", "Mac (vista prèvia)", "/ca/linux/"),
}
# The signed placeholders, as they read in each language of the brief, all filled from one name.
PLACEHOLDER = re.compile(r"\{(agent|file|system|maker|date|list)\}")
SYSTEM_PREFIX = {"macos": re.compile(r"^(En|On|A) macOS"), "linux": re.compile(r"^(En|On|A) Linux")}
COMMENT = {"json": "//", "toml": "#", "yaml": "#"}

CSS = """
:root{--paper:#FFFFFF}
.sb-sec{display:flex;flex-direction:column;gap:18px}
.tb-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;align-items:start;max-width:1040px}
@media (max-width:760px){.tb-grid{grid-template-columns:minmax(0,1fr)}}
.tb{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:16px 18px;min-width:0;display:flex;flex-direction:column;gap:12px;scroll-margin-top:16px}
.tb h3{margin:0;font-size:20px;line-height:1.25}
.tb-b{display:flex;flex-direction:column;gap:8px;border-top:1px solid var(--line);padding-top:12px;min-width:0}
.tb-os{margin:0;font-size:12.5px;font-weight:600;color:var(--ink2)}
.tb-sub{margin:4px 0 0;font-size:12.5px;font-weight:600;color:var(--muted)}
.tb-k{margin:0;font-size:12.5px;font-weight:600;color:var(--ink2)}
.tb p{margin:0;font-size:15px;line-height:1.55}
.tb ul{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:4px;font-size:14px;line-height:1.5}
.tb code,.tb pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.tb code{font-size:.92em}
.tb-tag{font-size:12px;font-weight:600;color:var(--muted)}
.tb-pre{position:relative;min-width:0}
.tb pre{margin:0;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-size:12.5px;line-height:1.5;white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}
.tb-copy{align-self:flex-start;font:inherit;font-size:14px;font-weight:600;padding:6px 14px;border:1px solid var(--ink);border-radius:8px;background:transparent;color:var(--ink);cursor:pointer}
.tb-copy:hover{background:var(--bg)}.tb-copy:focus-visible,.tb-s summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.tb-s{display:flex;flex-direction:column;gap:8px}
.tb-s summary{display:inline-block;width:max-content;max-width:100%;font-size:14px;font-weight:600;padding:6px 14px;border:1px solid var(--line);border-radius:8px;cursor:pointer;list-style:none}
.tb-s summary::-webkit-details-marker{display:none}
.tb-s[open]>*:not(summary){margin-top:8px}
.tb-src{font-size:12.5px !important;color:var(--muted)}.tb-src a{color:var(--muted)}
.tb-rev{font-size:12.5px !important;color:var(--ink);font-weight:600}
.dlrow{display:flex;flex-wrap:wrap;align-items:center;gap:12px}
.sbadge{display:inline-block;line-height:0;flex:none}.sbadge img{display:block;height:52px;width:auto}
.hbtn{display:inline-flex;align-items:center;text-decoration:none;font-weight:700;line-height:1.2}
.hbtn.sec{height:52px;padding:0 24px;border:1px solid var(--ink);border-radius:12px;background:transparent;color:var(--ink);font-size:17px;justify-content:center}
.hbtn.sec:hover{color:var(--ink);background:var(--card)}
@media (max-width:699px){.dlrow{flex-direction:column;align-items:stretch;width:100%}.dlrow .sbadge{align-self:flex-start}}
.sb-note{font-size:12.5px !important;color:var(--muted)}
""".strip()

SCRIPT = """<script>
document.querySelectorAll('.tb-copy').forEach(function(b){b.addEventListener('click',function(){
var pre=document.getElementById(b.getAttribute('data-copy'));if(!pre)return;
function select(){var r=document.createRange();r.selectNodeContents(pre);var s=window.getSelection();s.removeAllRanges();s.addRange(r);}
try{navigator.clipboard.writeText(pre.textContent).catch(select);}catch(e){select();}});});
</script>"""


def esc(s):
    return html.escape(str(s), quote=True)


def texts():
    return json.loads(TEXTS.read_text(encoding="utf-8"))["texts"]


def fill(s, **kw):
    return PLACEHOLDER.sub(lambda m: str(kw[m.group(1)]), s)


def code(s):
    """Escaped text with `...` painted as <code> (GTM-175 §1)."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))


def with_templates(agents):
    """The agent files with templates, in the Observatory's alphabetical order (the comparison table's)."""
    items = [a for a in agents if a.get("templates")]
    names = map_page.agent_names([a["agent"] for a in items], "en")
    return sorted(items, key=lambda a: names[a["agent"]["id"]].lower())


def template_urls(t):
    urls = [t["source"]["url"]] + [s["url"] for s in t.get("extra_sources", [])]
    if "session" in t:
        urls.append(t["session"]["source"]["url"])
    return urls


def watch_map(agents):
    """{url: watch strings} of every template page, in the order they first appear: what sources.json must watch."""
    out = {}
    for a in agents:
        for s in ("windows", "macos", "linux"):
            t = (a.get("templates") or {}).get(s)
            if not t:
                continue
            pairs = [(t["source"]["url"], t["watch"])] + [(x["url"], x.get("watch", [])) for x in t.get("extra_sources", [])]
            if "session" in t:
                pairs.append((t["session"]["source"]["url"], t["session"]["source"].get("watch", [])))
            for url, watch in pairs:
                if watch:
                    lst = out.setdefault(url, [])
                    lst += [w for w in watch if w not in lst]
    return out


def to_review(raw_dir=RAW_DIR, sources_file=SOURCES):
    """URLs whose page lost a watched string in the latest raw file of the collector (empty if there is none)."""
    files = sorted(Path(raw_dir).glob("????-??-??.json"))
    if not files:
        return set()
    raw = json.loads(files[-1].read_text(encoding="utf-8"))
    url = {s["id"]: s.get("read", {}).get("url") for s in json.loads(Path(sources_file).read_text(encoding="utf-8"))["sources"]}
    return {url.get(s["id"]) for s in raw.get("sources", []) if s.get("missing")} - {None}


def maker(a):
    return a["agent"]["vendor"].split(" (")[0]


class Card:
    def __init__(self, a, lang, review):
        self.a, self.lang, self.T, self.review = a, lang, texts()[lang], review
        self.aid = a["agent"]["id"]
        self.name = map_page.agent_names([a["agent"]], lang)[self.aid]
        self.n = 0

    def pre(self, text):
        self.n += 1
        pid = f"{self.aid}-c{self.n}"
        return (f'<pre id="{pid}">{esc(text)}</pre>'
                f'<button type="button" class="tb-copy" data-copy="{pid}">{esc(self.T["copy"])}</button>')

    def tag(self, system, text):
        """A system's name before an item that holds on only one of macOS and Linux, unless the text already says it."""
        if system is None or SYSTEM_PREFIX[system].match(text):
            return ""
        return f'<span class="tb-tag">{company_page.SYSTEM_NAME[system]}:</span> '

    def body(self, t):
        T = self.T
        out = [f'<p class="tb-k">{esc(T["template"])}</p>']
        for b in t["blocks"]:
            if b["format"] == "ui":
                out.append(f'<p>{esc(T["ui." + b["value"]])}</p>')
        files = [b for b in t["blocks"] if b["format"] in COMMENT]
        intro = t.get("intro", "paste_one")
        if intro == "vscode_settings":
            out.append(f'<p>{esc(T["paste.vscode"])}</p>')
            out.append(self.pre("\n\n".join(b["value"] for b in files)))
        elif intro == "paste_many":
            blocks = "\n\n".join(f'{COMMENT[b["format"]]} {b["file"]}\n{b["value"]}' for b in files)
            out.append(self.pre(fill(T["paste.many"], agent=self.name) + "\n\n" + blocks))
        else:
            out.append(self.pre(fill(T["paste.one"], agent=self.name, file=files[0]["file"]) + "\n\n" + files[0]["value"]))
        for b in t["blocks"]:
            if b["format"] == "env":
                out.append(f'<p>{esc(T["env." + b["note"]])}</p>')
                out.append(self.pre(b["value"]))
        return out

    def uncovered(self, items):
        """items: [(code, system or None)]."""
        if not items:
            return []
        T = self.T
        lis = "".join(f'<li>{self.tag(s, T["uncovered." + c])}{code(T["uncovered." + c])}</li>' for c, s in items)
        return [f'<p class="tb-k">{esc(T["uncovered.h"])}</p><ul>{lis}</ul>']

    def session(self, t, requires):
        """requires: [(code, system or None)]."""
        if "session" not in t:
            return []
        T = self.T
        s = t["session"]
        parts = [f'<p>{esc(fill(T["session.p"], agent=self.name))}</p>', self.pre(s["command"])]
        for c, system in requires:
            parts.append(f'<p>{self.tag(system, "")}{esc(fill(T["session.requires"], list=T["requires." + c]))}</p>')
        if "/RUTA/DEL/PROYECTO" in s["command"]:
            parts.append(f'<p>{esc(T["session.path"])}</p>')
        return [f'<details class="tb-s"><summary>{esc(T["session.button"])}</summary>{"".join(parts)}</details>']

    def footer(self, ts):
        T = self.T
        t = ts[0]
        date = map_page.fmt_date(t["source"]["accessed_at"], self.lang)
        mk = f'<a href="{esc(t["source"]["url"])}" rel="noopener">{esc(maker(self.a))}</a>'
        out = [f'<p class="tb-src">{fill(esc(T["source"]), maker=mk, date=esc(date))}</p>']
        if any(u in self.review for x in ts for u in template_urls(x)):
            out.append(f'<p class="tb-rev">{esc(T["review"])}</p>')
        return out

    def one(self, t, system):
        """The content of one system's template (system names the block's sole system, or is None)."""
        T = self.T
        if t["kind"] == "separate_account":
            return [f'<p>{esc(fill(T["separate_account"], system=company_page.SYSTEM_NAME[system], agent=self.name))}</p>']
        if not t["blocks"]:
            return [f'<p>{esc(T["container"])}</p>']
        return self.body(t)

    def unix(self):
        T = self.T
        mac, lin = self.a["templates"]["macos"], self.a["templates"]["linux"]
        same = (mac["kind"], mac.get("intro"), mac["blocks"]) == (lin["kind"], lin.get("intro"), lin["blocks"])
        out = [f'<p class="tb-os">{esc(T["block.unix"])}</p>']
        if mac["kind"] == "separate_account" and same:
            out.append(f'<p>{esc(fill(T["separate_account"], system=T["block.unix"], agent=self.name))}</p>')
            return out + self.footer([mac, lin])
        if same:
            out += self.one(mac, None)
            unc = [(c, None if c in lin["uncovered"] else "macos") for c in mac["uncovered"]]
            unc += [(c, "linux") for c in lin["uncovered"] if c not in mac["uncovered"]]
            out += self.uncovered(unc)
            if "session" in mac and "session" in lin and mac["session"]["command"] == lin["session"]["command"]:
                mr, lr = mac["session"]["requires"], lin["session"]["requires"]
                req = [(c, None if c in lr else "macos") for c in mr] + [(c, "linux") for c in lr if c not in mr]
                out += self.session(mac, req)
            return out + self.footer([mac, lin])
        for system, t in (("macos", mac), ("linux", lin)):
            out.append(f'<p class="tb-sub">{company_page.SYSTEM_NAME[system]}</p>')
            out += self.one(t, system)
            out += self.uncovered([(c, None) for c in t["uncovered"]])
            if "session" in t:
                out += self.session(t, [(c, None) for c in t["session"]["requires"]])
            out += self.footer([t])
        return out

    def windows(self):
        T = self.T
        t = self.a["templates"]["windows"]
        out = [f'<p class="tb-os">{esc(T["block.windows"])}</p>'] + self.one(t, "windows")
        out += self.uncovered([(c, None) for c in t["uncovered"]])
        if "session" in t:
            out += self.session(t, [(c, None) for c in t["session"]["requires"]])
        return out + self.footer([t])

    def html(self):
        return (f'<section class="tb" id="{esc(self.aid)}" aria-labelledby="tb-{esc(self.aid)}">'
                f'<h3 id="tb-{esc(self.aid)}">{esc(self.name)}</h3>'
                f'<div class="tb-b">{"".join(self.unix())}</div>'
                f'<div class="tb-b">{"".join(self.windows())}</div>'
                "</section>")


def download(lang):
    route, l, alt, mac, mac_label, linux = DOWNLOAD[lang]
    return (f'<div class="dlrow"><a class="sbadge" href="{route}?from=sandbox&amp;os=store" target="_blank" rel="nofollow noopener">'
            f'<img src="/assets/store/microsoft-store-{l}.svg" width="161" height="44" alt="{esc(alt)}"></a>'
            f'<a class="hbtn sec" href="{mac}">{esc(mac_label)}</a><a class="hbtn sec" href="{linux}">Linux</a></div>')


def article(lang, agents, review):
    T = texts()[lang]
    cards = "\n".join(Card(a, lang, review).html() for a in with_templates(agents))
    guide = company_page.GUIDE_PATH[lang]
    return f"""<article class="doc"><h1>{esc(T["title"])}</h1>
<p>{esc(T["lead"])}</p>
<h2 id="which">{esc(T["which.h"])}</h2>
<p>{esc(T["which.p"])}</p>
<p><a href="{sandbox_page.SANDBOX_PATH[lang]}">{esc(T["which.link"])}</a></p>
<h2 id="templates">{esc(T["on.h"])}</h2>
<p>{esc(T["on.p"])}</p>
</article>
<div class="tb-grid">
{cards}
</div>
<article class="doc">
<h2 id="apart">{esc(T["apart.h"])}</h2>
<p>{esc(T["apart.p"])}</p>
<p><a href="{guide}">{esc(T["apart.link"])}</a></p>
<h2 id="then">{esc(T["then.h"])}</h2>
<p>{esc(T["then.p"])}</p>
{download(lang)}
<p class="sb-note">{esc(T["note"])}</p>
</article>"""


def shell_parts(lang):
    """(head styles and links, header, footer, scripts) of the guide page of the language."""
    s = (SITE / GUIDE_FILE[lang]).read_text(encoding="utf-8")
    style = s[s.index('<link rel="stylesheet"'):s.index("</head>")]
    header = s[s.index("<header>"):s.index("</header>") + len("</header>")]
    footer = s[s.index("<footer>"):s.index("</footer>") + len("</footer>")]
    scripts = s[s.index("</footer>") + len("</footer>"):s.index("</body>")].strip()
    return style, header, footer, scripts


def nav_for_section(block, lang):
    """The guide's navigation with the language links pointing to this section and «Sandbox» as the current page."""
    for o in LANGS:
        if o != lang:
            block = re.sub(r'<a href="[^"]*" hreflang="%s"' % o, f'<a href="{SECTION_PATH[o]}" hreflang="{o}"', block)
    return block.replace(f'<a href="{SECTION_PATH[lang]}">', f'<a href="{SECTION_PATH[lang]}" aria-current="page">')


def page(lang, agents, review):
    T = texts()[lang]
    style, header, footer, scripts = shell_parts(lang)
    url = "https://rosmarops.com" + SECTION_PATH[lang]
    title = T["title"] + " · RosmarOps"
    desc = T["lead"]
    alts = "".join(f'<link rel="alternate" hreflang="{o}" href="https://rosmarops.com{SECTION_PATH[o]}">\n' for o in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="https://rosmarops.com{SECTION_PATH["en"]}">\n'
    ld = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#page", "url": url, "name": T["title"],
                     "inLanguage": lang, "isPartOf": {"@id": "https://rosmarops.com/#website"}}, ensure_ascii=False)
    alt = {"en": "RosmarOps logo", "es": "Logotipo de RosmarOps", "ca": "Logotip de RosmarOps"}[lang]
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
{alts}<meta property="og:type" content="article">
<meta property="og:site_name" content="RosmarOps">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:image" content="https://rosmarops.com/assets/brand/rosmarops-social.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(alt)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script>
{style.strip()}
<style>
{CSS}
</style>
</head>
<body>
{nav_for_section(header, lang)}

<main><div class="wrap">
{article(lang, agents, review)}
</div></main>

{nav_for_section(footer, lang)}
{scripts}
{SCRIPT}
</body>
</html>
"""


def build(agents, site=SITE):
    review = to_review()
    for lang in LANGS:
        out = Path(site) / SECTION_PATH[lang].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(lang, agents, review), encoding="utf-8")
