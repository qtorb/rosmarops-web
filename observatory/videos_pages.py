"""GTM-199 (signed by Albert 22-11 15:16): the videos on the website.

One data file per video in observatory/data/videos/<name>.json. Only videos with "public": true get a page, a card in
the index (/videos/, /es/videos/, /ca/videos/), a place in the sitemap and llms.txt, and a player on their standing
page. The player shows a thumbnail served by rosmarops.com; nothing is loaded from Google until the person presses
play. Then a small inline script swaps the thumbnail for the YouTube player in privacy-enhanced mode
(youtube-nocookie.com). Without JavaScript, the thumbnail is a plain link to the video on YouTube.

GTM-67 (signed by Albert 23-11 09:51): a video that lives in a blog post instead of YouTube has "post" (its post path per
language) instead of "youtube_id". It gets a card in the index that links to the post, and nothing else here: no page of
its own, no sitemap entry (the post is in WordPress's sitemap), no player on a standing page. Its "thumb" may be one
path per language.

GTM-236 (signed by Albert 28-11): a video made in each language, with no presenter. Then "youtube_id" and "thumb" are
one per language, "presenter" is false (no «AI-generated presenter» label and no «The video is in Spanish» note), the
language of each page's video is its own language for search engines, and "family" names a Control Baseline family, whose
signed title and address go under «Read more».
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "observatory" / "data" / "videos"
BASE = "https://rosmarops.com"
LANGS = ("en", "es", "ca")
HOME = {"en": "/", "es": "/es/", "ca": "/ca/"}
INDEX = {"en": "/videos/", "es": "/es/videos/", "ca": "/ca/videos/"}
DOWNLOAD = {"en": "/download", "es": "/es/descargar/", "ca": "/ca/descarregar/"}
SANDBOX = {"en": "/sandbox/", "es": "/es/sandbox/", "ca": "/ca/sandbox/"}
FORBIDDEN = re.compile(r"\b(safe|safely|secure|securely|protects?|protected|seguro|segura|protege|protegido|segur|protegeix|no telemetry|sin telemetr\w*|sense telemetr\w*)\b", re.I)
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

L = {
    "en": {"ai": "AI-generated presenter", "watch": "Watch on YouTube", "play": "Play the video", "spanish": "The video is in Spanish.",
           "how": "How to use it with care", "transcript": "Transcript", "more": "Read more", "videos": "Videos",
           "all": "All videos", "download": "Download RosmarOps", "home": "Home", "sandbox": "Turn on your AI agent's sandbox in 3 steps",
           "index_lead": "Short videos about AI agents: one real question each, and what to do about it. Some are presented by Rosmary, an AI-generated presenter, in Spanish; others are text and drawings only, in your language.",
           "index_title": "Videos about AI agents", "index_desc": "Short videos about AI agents: one real question each, and what to do about it."},
    "es": {"ai": "Presentadora generada con IA", "watch": "Ver en YouTube", "play": "Reproducir el vídeo", "spanish": "",
           "how": "Cómo usarlo con cabeza", "transcript": "Transcripción", "more": "Para seguir", "videos": "Vídeos",
           "all": "Todos los vídeos", "download": "Descargar RosmarOps", "home": "Inicio", "sandbox": "Enciende el sandbox de tu agente de IA en 3 pasos",
           "index_lead": "Vídeos cortos sobre agentes de IA: una pregunta real cada uno, y qué hacer. Unos los presenta Rosmary, una presentadora generada con IA, en castellano; otros son solo texto y dibujos, en tu idioma.",
           "index_title": "Vídeos sobre agentes de IA", "index_desc": "Vídeos cortos sobre agentes de IA: una pregunta real cada uno, y qué hacer."},
    "ca": {"ai": "Presentadora generada amb IA", "watch": "Veure a YouTube", "play": "Reproduir el vídeo", "spanish": "El vídeo és en castellà.",
           "how": "Com fer-lo servir amb seny", "transcript": "Transcripció", "more": "Per continuar", "videos": "Vídeos",
           "all": "Tots els vídeos", "download": "Descarregar RosmarOps", "home": "Inici", "sandbox": "Encén el sandbox del teu agent d'IA en 3 passos",
           "index_lead": "Vídeos curts sobre agents d'IA: una pregunta real cadascun, i què fer. Uns els presenta la Rosmary, una presentadora generada amb IA, en castellà; d'altres són només text i dibuixos, en el teu idioma.",
           "index_title": "Vídeos sobre agents d'IA", "index_desc": "Vídeos curts sobre agents d'IA: una pregunta real cadascun, i què fer."},
}

CSS = """.vp{position:relative;aspect-ratio:16/9;width:100%;max-width:760px;border-radius:12px;overflow:hidden;background:#111;border:1px solid var(--line)}
.vp a,.vp iframe{display:block;width:100%;height:100%;border:0}
.vp img{display:block;width:100%;height:100%;object-fit:cover}
.vp-play{position:absolute;left:50%;top:50%;width:76px;height:76px;margin:-38px 0 0 -38px;border-radius:50%;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center}
.vp-play::after{content:"";margin-left:6px;border-style:solid;border-width:15px 0 15px 25px;border-color:transparent transparent transparent #fff}
.vp a:hover .vp-play,.vp a:focus-visible .vp-play{background:rgba(0,0,0,.9)}
.vp-meta{margin:8px 0 0;font-size:15px;color:var(--muted)}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.vl{list-style:none;padding:0;margin:0;display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.vl img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;border-radius:10px;border:1px solid var(--line)}
.vl h2{font-size:19px;margin:10px 0 4px;line-height:1.3}.vl p{margin:0;font-size:16px;color:var(--ink2)}
.doc details summary{cursor:pointer;font-weight:600}"""

# Swaps the thumbnail for the player when the person presses play. Nothing is loaded from Google before that.
SCRIPT = """<script>
document.querySelectorAll('.vp a[data-yt]').forEach(function(a){a.addEventListener('click',function(e){
e.preventDefault();var f=document.createElement('iframe'),cc=a.dataset.cc;
f.src='https://www.youtube-nocookie.com/embed/'+a.dataset.yt+'?autoplay=1&rel=0'+(cc?'&cc_load_policy=1&cc_lang_pref='+cc:'');
f.title=a.dataset.title;f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;
f.referrerPolicy='strict-origin-when-cross-origin';a.parentNode.replaceChild(f,a);});});
</script>"""


def esc(s):
    return html.escape(s, quote=True)


def load(folder=DATA):
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(folder).glob("*.json"))}


def public(videos):
    """Public videos, newest first (by the date they became public, then the upload date)."""
    pub = [(k, v) for k, v in videos.items() if v.get("public")]
    return sorted(pub, key=lambda kv: (kv[1].get("public_since") or "", kv[1].get("upload_date") or ""), reverse=True)


def check(videos, site=SITE):
    """Stops the build if a public video is missing something, or a text says a forbidden word."""
    for k, v in videos.items():
        for lang in LANGS:
            blob = " ".join([v["title"].get(lang, ""), v["answer"].get(lang, ""), *v["how_to"].get(lang, []), *v["transcript"].get(lang, [])])
            m = FORBIDDEN.search(blob)
            if m:
                raise ValueError(f"video {k}/{lang}: forbidden word «{m.group(0)}»")
        if not v.get("public"):
            continue
        if v.get("post"):
            for lang in LANGS:
                if not str(v["post"].get(lang, "")).startswith("/"):
                    raise ValueError(f"video {k}/{lang}: post without a path")
        elif not all(YT_ID.match(yt(v, lang) or "") for lang in LANGS):
            raise ValueError(f"video {k}: public without a valid youtube_id")
        if not v.get("public_since"):
            raise ValueError(f"video {k}: public without public_since")
        for t in sorted({thumb(v, lang) for lang in LANGS}):
            if not (Path(site) / t.lstrip("/")).exists():
                raise ValueError(f"video {k}: thumbnail {t} is not in site/")
        for lang in LANGS:
            for f in ("title", "answer"):
                if not v[f].get(lang, "").strip():
                    raise ValueError(f"video {k}/{lang}: {f} is empty")
            if len(v["how_to"].get(lang, [])) != len(v["how_to"]["es"]):
                raise ValueError(f"video {k}/{lang}: how_to has a different number of points")
            if v["transcript"]["es"] and len(v["transcript"].get(lang, [])) != len(v["transcript"]["es"]):
                raise ValueError(f"video {k}/{lang}: transcript has a different number of paragraphs")
            if not v["slug"].get(lang):
                raise ValueError(f"video {k}/{lang}: no slug")


def path(v, lang):
    if v.get("post"):
        return v["post"][lang]
    return INDEX[lang] + v["slug"][lang] + "/"


def thumb(v, lang):
    t = v["thumb"]
    return t[lang] if isinstance(t, dict) else t


def yt(v, lang):
    """The YouTube id of the video in this language: one for all, or one per language (GTM-236)."""
    i = v.get("youtube_id")
    return i.get(lang) if isinstance(i, dict) else i


def presenter(v):
    """Whether the video has the AI-generated presenter (every video before GTM-236)."""
    return v.get("presenter", True)


def video_lang(v, lang):
    """The language spoken or shown in the video: Spanish for the presenter's videos, the page's own for GTM-236's."""
    return "es" if presenter(v) else lang


def on_youtube(videos):
    """Public videos that have their own page (on YouTube), newest first."""
    return [(k, v) for k, v in public(videos) if not v.get("post")]


def mmss(iso):
    m = re.match(r"^PT(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
    return f"{int(m.group(1) or 0)}:{int(m.group(2) or 0):02d}" if m else ""


def player(v, lang, heading_level=None):
    """The thumbnail with a play button; the player loads only on click. Plus the AI-presenter label."""
    vid, t = yt(v, lang), v["title"][lang]
    watch = f"https://www.youtube.com/watch?v={vid}"
    cc = lang if lang in v.get("subtitles", []) else ""
    meta = ([esc(L[lang]["ai"])] if presenter(v) else []) + ([mmss(v["duration"])] if mmss(v.get("duration")) else []) + \
           [f'<a href="{watch}" rel="noopener">{esc(L[lang]["watch"])}</a>']
    return (f'<div class="vp"><a href="{watch}" rel="noopener" data-yt="{vid}" data-cc="{cc}" data-title="{esc(t)}">'
            f'<img src="{esc(thumb(v, lang))}" width="1280" height="720" alt="{esc(t)}">'
            f'<span class="vp-play" aria-hidden="true"></span><span class="vh">{esc(L[lang]["play"])}: {esc(t)}</span></a></div>\n'
            f'<p class="vp-meta">{" · ".join(meta)}</p>')


def video_object(v, lang, url=None):
    o = {"@type": "VideoObject", "name": v["title"][lang], "description": v["answer"][lang],
         "thumbnailUrl": BASE + thumb(v, lang), "inLanguage": video_lang(v, lang),
         "embedUrl": f"https://www.youtube-nocookie.com/embed/{yt(v, lang)}",
         "url": url or f"https://www.youtube.com/watch?v={yt(v, lang)}"}
    if v.get("upload_date"):
        o["uploadDate"] = v["upload_date"]
    if v.get("duration"):
        o["duration"] = v["duration"]
    return o


def topic_link(v, lang):
    """(text, href) of the standing page of the video's topic, or None."""
    if v.get("family"):  # GTM-236: the Control Baseline family, with its signed title
        import minimum
        f = next(f for f in minimum.families() if f["id"] == v["family"])
        return (f[lang]["h1"], f["path"][lang])
    tp = v.get("topic_page")
    if tp == "sandbox":
        return (L[lang]["sandbox"], SANDBOX[lang])
    if tp:
        import topic_pages
        p = topic_pages.load()["pages"][tp]
        return (p[lang]["title"], p["path"][lang])
    return None


def top_video(videos, topic):
    """The newest public video of a standing page, or None."""
    for _, v in on_youtube(videos):
        if v.get("topic_page") == topic:
            return v
    return None


def shell(lang, paths, title, desc, url, ld, body):
    import sandbox_section
    style, header, footer, scripts = sandbox_section.shell_parts(lang)
    header = header.replace(' aria-current="page"', "")

    def switch(block):
        for o, p in paths.items():
            if o != lang:
                block = re.sub(r'<a href="[^"]*" hreflang="%s"' % o, f'<a href="{p}" hreflang="{o}"', block)
        return block
    alts = "".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{p}">\n' for l, p in paths.items())
    alts += f'<link rel="alternate" hreflang="x-default" href="{BASE}{paths["en"]}">\n'
    import topic_pages
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · RosmarOps</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
{alts}<meta property="og:type" content="website">
<meta property="og:site_name" content="RosmarOps">
<meta property="og:title" content="{esc(title)} · RosmarOps">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/brand/rosmarops-social.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False)}</script>
{style.strip()}
<style>
{topic_pages.DOC_CSS}
{CSS}
</style>
</head>
<body>
{switch(header)}

<main><div class="wrap">
{body}
</div></main>

{switch(footer)}
{scripts}
{SCRIPT}
</body>
</html>
"""


def video_page(k, v, lang):
    url = BASE + path(v, lang)
    out = [f'<article class="doc"><h1>{esc(v["title"][lang])}</h1>', f'<p class="tp-first">{esc(v["answer"][lang])}</p>', player(v, lang)]
    if v["how_to"][lang]:
        out.append(f'<h2>{esc(L[lang]["how"])}</h2><ol>' + "".join(f"<li>{esc(x)}</li>" for x in v["how_to"][lang]) + "</ol>")
    if v["transcript"].get(lang):
        note = f'<p>{esc(L[lang]["spanish"])}</p>' if L[lang]["spanish"] and presenter(v) else ""
        out.append(f'<details><summary>{esc(L[lang]["transcript"])}</summary>{note}'
                   + "".join(f"<p>{esc(p)}</p>" for p in v["transcript"][lang]) + "</details>")
    links = []
    tl = topic_link(v, lang)
    if tl:
        links.append(tl)
    links += [(L[lang]["all"], INDEX[lang]), (L[lang]["download"], DOWNLOAD[lang])]
    out.append(f'<section class="tp-more"><h2>{esc(L[lang]["more"])}</h2><ul>'
               + "".join(f'<li><a href="{esc(h)}">{esc(x)}</a></li>' for x, h in links) + "</ul></section></article>")
    ld = [video_object(v, lang),
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": L[lang]["home"], "item": BASE + HOME[lang]},
              {"@type": "ListItem", "position": 2, "name": L[lang]["videos"], "item": BASE + INDEX[lang]},
              {"@type": "ListItem", "position": 3, "name": v["title"][lang], "item": url}]}]
    paths = {l: path(v, l) for l in LANGS}
    return shell(lang, paths, v["title"][lang], v["answer"][lang], url, ld, "\n".join(out))


def cards(videos, lang):
    """The cards of the index, newest first (also on the RosmarOps Academy page, GTM-230)."""
    return "".join(
        f'<li><a href="{path(v, lang)}"><img src="{esc(thumb(v, lang))}" width="1280" height="720" loading="lazy" alt="{esc(v["title"][lang])}"></a>'
        f'<h2><a href="{path(v, lang)}">{esc(v["title"][lang])}</a></h2>'
        f'<p>{esc(v["answer"][lang])}{(" · " + mmss(v["duration"])) if mmss(v.get("duration")) else ""}</p></li>'
        for _, v in public(videos))


def index_page(videos, lang):
    pub = public(videos)
    body = (f'<article class="doc"><h1>{esc(L[lang]["videos"])}</h1><p class="tp-first">{esc(L[lang]["index_lead"])}</p></article>'
            f'<ul class="vl" style="margin-top:28px">{cards(videos, lang)}</ul>')
    url = BASE + INDEX[lang]
    ld = [{"@type": "ItemList", "itemListElement": [
              ({"@type": "ListItem", "position": i + 1, "url": BASE + path(v, lang)} if v.get("post") else
               {"@type": "ListItem", "position": i + 1, "url": BASE + path(v, lang), "item": video_object(v, lang, BASE + path(v, lang))})
              for i, (_, v) in enumerate(pub)]},
          {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": L[lang]["home"], "item": BASE + HOME[lang]},
              {"@type": "ListItem", "position": 2, "name": L[lang]["videos"], "item": url}]}]
    return shell(lang, INDEX, L[lang]["index_title"], L[lang]["index_desc"], url, ld, body)


def pages(videos=None):
    videos = load() if videos is None else videos
    check(videos)
    out = {INDEX[lang]: index_page(videos, lang) for lang in LANGS}
    for k, v in on_youtube(videos):
        for lang in LANGS:
            out[path(v, lang)] = video_page(k, v, lang)
    return out


def sitemap_urls(videos=None):
    videos = load() if videos is None else videos
    groups = [INDEX] + [{l: path(v, l) for l in LANGS} for _, v in on_youtube(videos)]
    return [(g[l], g) for g in groups for l in LANGS]


def llms_lines(videos=None):
    videos = load() if videos is None else videos
    lines = [f"- [Videos]({BASE}/videos/): short videos about AI agents; some in Spanish with an AI-generated presenter, others text and drawings only in English, Spanish and Catalan."]
    lines += [f"- [{v['title']['en']}]({BASE}{path(v, 'en')}): {v['answer']['en']}" for _, v in public(videos)]
    return lines


def build(site=SITE, videos=None):
    videos = load() if videos is None else videos
    for p, text in pages(videos).items():
        f = Path(site) / p.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return videos
