"""GTM-230: RosmarOps Academy, its page (/academy/, /es/academy/, /ca/academy/) and its place in the menu, behind one
switch: "open" in observatory/data/academy.json.

Closed (the state the repository is delivered in): no Academy page is written, every menu is the one of before,
and the course lessons keep noindex, stay out of the sitemap and show no «Back to Academy» button.
Open: the page exists, «Academy» is in every header menu, and the page and the lessons are in the sitemap and lose
noindex. Opening it is Albert's decision, in one deploy.

The menu (spec §1.3 and §4, vigil docs/research/2026-11-27-academy-portada-y-menu.md): «Academy» goes right after
«Sandbox». On inner pages it takes the place of «FAQ»/«Preguntas»/«Preguntes», which stays in the footer; on the homes
(which have no FAQ entry) it is added. Only the header menu changes, never the footer.

The five places the menu comes from (GTM-228) all go through nav() below:
- hand-written pages in site/ (and the glossary, a copy of the methodology page): fix_site() rewrites their header
  menu in place at the start of every build, so the committed files follow the switch;
- the Observatory and the daily shells: build.page() passes its header through nav();
- the Sandbox section, topic, video and course pages: sandbox_section.shell_parts() passes the guide's header through it;
- the static About pages: build.build_static_about() passes its page through it;
- the WordPress blog: wp/mu-plugins/rosmarops-menu10-academy.php, whose ROSMAROPS_MENU10_OPEN line build() writes
  from the switch (inert while closed).

Usage: python3 observatory/academy.py --check-site   (used by the deploy: exit 1 if site/ does not match the switch)
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "observatory" / "data" / "academy.json"
CATALOG = ROOT / "observatory" / "i18n"
PLUGIN = ROOT / "wp" / "mu-plugins" / "rosmarops-menu10-academy.php"
BASE = "https://rosmarops.com"
LANGS = ("en", "es", "ca")
SANDBOX = {"en": "/sandbox/", "es": "/es/sandbox/", "ca": "/ca/sandbox/"}
LABEL = "Academy"


def esc(s):
    return html.escape(str(s), quote=True)


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_open(data=None):
    return bool((data or load())["open"])


def _cat(lang):
    return json.loads((CATALOG / f"{lang}.json").read_text(encoding="utf-8"))


def faq_link(lang):
    c = _cat(lang)
    return f'<a href="{c["site.nav.faq_url"]}">{c["site.nav.faq"]}</a>'


def method_url(lang):
    return _cat(lang)["site.nav.methodology_url"]


def academy_link(lang, path, current=False):
    cur = ' aria-current="page"' if current else ""
    return f'<a href="{path}"{cur}>{LABEL}</a>'


def nav_menu(menu, lang, open_, path, current=False):
    """One header <nav>…</nav>, set to the state of the switch. Idempotent both ways."""
    a = re.compile(r'<a href="%s"[^>]*>%s</a>' % (re.escape(path), LABEL))
    faq = faq_link(lang)
    meth = re.search(r'<a href="%s"[^>]*>[^<]*</a>' % re.escape(method_url(lang)), menu)
    if open_:
        menu = menu.replace(faq, "")
        current = current or bool(re.search(r'<a href="%s" aria-current="page">' % re.escape(path), menu))
        menu = a.sub("", menu)
        sb = re.search(r'<a href="%s"[^>]*>Sandbox</a>' % re.escape(SANDBOX[lang]), menu)
        menu = menu[:sb.end()] + academy_link(lang, path, current) + menu[sb.end():]
    else:
        had = a.search(menu)
        menu = a.sub("", menu)
        if had and meth and faq not in menu:
            m = re.search(r'<a href="%s"[^>]*>[^<]*</a>' % re.escape(method_url(lang)), menu)
            menu = menu[:m.end()] + faq + menu[m.end():]
    return menu


def nav(page, lang, open_=None, data=None, current=False):
    """The page (or a header fragment) with its header menu set to the switch. Only a <header> whose <nav> has the
    «Sandbox» entry of the site menu is touched (the sample reports have their own header)."""
    data = data or load()
    if open_ is None:
        open_ = is_open(data)
    h = re.search(r"<header\b.*?</header>", page, re.S)
    if not h:
        return page
    n = re.search(r"<nav>.*?</nav>", h.group(0), re.S)
    if not n or not re.search(r'<a href="%s"[^>]*>Sandbox</a>' % re.escape(SANDBOX[lang]), n.group(0)):
        return page
    new = nav_menu(n.group(0), lang, open_, data["path"][lang], current)
    start = h.start() + n.start()
    return page[:start] + new + page[start + len(n.group(0)):]


def page_lang(page):
    m = re.search(r'<html lang="(en|es|ca)"', page)
    return m.group(1) if m else None


def fix_site(site=SITE, data=None):
    """Sets the header menu of every page in site/ to the switch. Returns the pages it changed."""
    data = data or load()
    changed = []
    for f in sorted(Path(site).rglob("*.html")):
        s = f.read_text(encoding="utf-8")
        lang = page_lang(s)
        if not lang:
            continue
        new = nav(s, lang, data=data)
        if new != s:
            f.write_text(new, encoding="utf-8")
            changed.append(f)
    return changed


def menu_entries(page):
    """The labels of the header menu, in order (the tests compare them across pages)."""
    h = re.search(r"<header\b.*?</header>", page, re.S)
    n = re.search(r"<nav>(.*?)</nav>", h.group(0), re.S)
    return [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<a\b[^>]*>.*?</a>", n.group(1), re.S)]


# ---------------------------------------------------------------- the Academy page (spec §2 and §3)

CSS = """.ac-two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.ac-two .cs-c h2{font-size:18px;margin:0 0 8px;line-height:1.3}
.ac-two .cs-c p,.ac-two .cs-c ul{font-size:16px;line-height:1.55;color:var(--ink2);margin:0}
.ac-two .cs-c ul{list-style:disc;padding-left:20px}
.course .ac-course p{margin:0}
.course .ac-title{font-size:22px;font-weight:700;line-height:1.3}
.course .ac-meta{font-size:14px;color:var(--muted);margin-top:4px}
.course .ac-need{font-size:16px;margin-top:12px;color:var(--ink2)}
.course ul.vl{display:grid;padding:0}
.course .ac-all{margin:16px 0 0}
@media (max-width:820px){.ac-two{grid-template-columns:1fr}}"""


def lesson_cards(t, lesson_paths, lang):
    out = []
    for k, (h, txt) in enumerate(t["course.lessons"]):
        sub = f"<span>{esc(txt)}</span>" if txt else ""
        inner = f'<span class="cs-num">{k + 1}</span><span class="cs-lt"><b>{esc(h)}</b>{sub}</span>'
        if k < len(lesson_paths):
            out.append(f'<a class="cs-lesson" href="{esc(lesson_paths[k])}">{inner}</a>')
        else:
            out.append(f'<div class="cs-lesson">{inner}<span class="cs-pill-soon">{esc(t["soon"])}</span></div>')
    return "".join(out)


def page_html(lang, data, lessons, videos):
    """lessons: course_pages.load_all(); videos: videos_pages.load()."""
    import course_pages
    import videos_pages
    t, paths = data[lang], data["path"]
    lesson_paths = [lessons[n]["path"][lang] for n in course_pages.LESSONS]
    top, footer, scripts = course_pages.head(lang, paths, "RosmarOps Academy", t["lead"], noindex=False, raw_title=True)
    top = nav(top, lang, True, data, current=True)
    why = "".join(f"<li>{esc(t[k])}</li>" for k in ("why.1", "why.2", "why.3"))
    return f"""{top.replace("</head>", f"<style>{CSS}\n{videos_pages.CSS}</style>\n</head>")}
<main class="course"><div class="wrap"><div class="doc cs-entry">
<p class="eyebrow">{esc(t["eyebrow"])}</p><h1>{esc(t["h1"])}</h1>
<p class="lead">{esc(t["lead"])}</p>
<div class="ac-two"><div class="cs-c"><h2>{esc(t["what.h2"])}</h2><p>{esc(t["what.p"])}</p></div>
<div class="cs-c"><h2>{esc(t["why.h2"])}</h2><ul>{why}</ul></div></div>
<h2>{esc(t["who.h2"])}</h2><p>{esc(t["who.p"])}</p>
<h2>{esc(t["ex.h2"])}</h2><p class="cs-big">{esc(t["ex.p"])}</p>
<h2>{esc(t["course.h2"])}</h2>
<div class="ac-course"><p class="ac-title">{esc(t["course.title"])}</p><p class="ac-meta">{esc(t["course.meta"])}</p>
<p class="ac-need">{esc(t["course.need"])}</p></div>
<div class="cs-lessons">{lesson_cards(t, lesson_paths, lang)}</div>
<p class="cs-next"><a class="cs-btn primary" href="{esc(lesson_paths[0])}">{esc(t["course.cta"])}</a></p>
<h2>{esc(t["videos.h2"])}</h2><p>{esc(t["videos.p"])}</p></div>
<ul class="vl" style="margin-top:28px">{videos_pages.cards(videos, lang)}</ul>
<div class="doc"><p class="ac-all"><a href="{videos_pages.INDEX[lang]}">{esc(t["videos.all"])}</a></p>
<p class="cs-foot">{esc(t["foot"])}</p></div>
</div></main>

{footer}
{scripts}
</body>
</html>
"""


def pages(data=None):
    """{path: html} of the Academy page; empty while the switch is closed."""
    data = data or load()
    if not is_open(data):
        return {}
    import course_pages
    import videos_pages
    lessons = course_pages.load_all()
    videos = videos_pages.load()
    return {data["path"][lang]: page_html(lang, data, lessons, videos) for lang in LANGS}


def sitemap_urls(data=None):
    """(path, {lang: path}) for sitemap-pages.xml: the Academy page and the two lessons, only once open."""
    data = data or load()
    if not is_open(data):
        return []
    import course_pages
    groups = [data["path"]] + [course_pages.load_all()[n]["path"] for n in course_pages.LESSONS]
    return [(g[lang], g) for g in groups for lang in LANGS]


def write_plugin_switch(data=None, plugin=PLUGIN):
    data = data or load()
    s = plugin.read_text(encoding="utf-8")
    new = re.sub(r"const ROSMAROPS_MENU10_OPEN = (true|false);",
                 f"const ROSMAROPS_MENU10_OPEN = {'true' if is_open(data) else 'false'};", s)
    if new != s:
        plugin.write_text(new, encoding="utf-8")


def build(site=SITE, data=None):
    """Writes the Academy page when open and removes it when closed; keeps the blog patch in step with the switch."""
    import shutil
    data = data or load()
    built = pages(data)
    for lang in LANGS:
        d = Path(site) / data["path"][lang].strip("/")
        if data["path"][lang] not in built:
            shutil.rmtree(d, ignore_errors=True)
    for path, text in built.items():
        f = Path(site) / path.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    if Path(site).resolve() == SITE.resolve():
        write_plugin_switch(data)


def check_site(site=SITE, data=None):
    """What the deploy checks: site/ matches the switch. Returns the problems (empty when all is right)."""
    data = data or load()
    import course_pages
    open_ = is_open(data)
    bad = []
    lessons = [p for n in course_pages.LESSONS for p in course_pages.load_all()[n]["path"].values()]
    for p in data["path"].values():
        exists = (Path(site) / p.strip("/") / "index.html").exists()
        if exists != open_:
            bad.append(f"{p}: {'missing' if open_ else 'present while Academy is closed'}")
    for p in lessons:
        s = (Path(site) / p.strip("/") / "index.html").read_text(encoding="utf-8")
        noindex = '<meta name="robots" content="noindex">' in s
        if noindex == open_:
            bad.append(f"{p}: {'still noindex' if open_ else 'not noindex while Academy is closed'}")
    sm = (Path(site) / "sitemap-pages.xml").read_text(encoding="utf-8")
    for p in list(data["path"].values()) + lessons:
        if (f"<loc>{BASE}{p}</loc>" in sm) != open_:
            bad.append(f"{p}: {'missing from' if open_ else 'in'} the sitemap")
    for f in sorted(Path(site).rglob("*.html")):
        s = f.read_text(encoding="utf-8")
        lang = page_lang(s)
        if lang and nav(s, lang, data=data) != s:
            bad.append(f"{f.relative_to(site)}: header menu does not match the switch")
    return bad


if __name__ == "__main__":
    if "--check-site" in sys.argv:
        problems = check_site()
        for p in problems:
            print(p)
        print(f"Academy is {'open' if is_open() else 'closed'}; site/ {'matches' if not problems else 'does NOT match'} the switch")
        sys.exit(1 if problems else 0)
    build()
