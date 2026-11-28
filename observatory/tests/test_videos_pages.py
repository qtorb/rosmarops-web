"""Tests for observatory/videos_pages.py and observatory/videos_check.py (GTM-199): the videos on the website."""

import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import videos_check  # noqa: E402
import videos_pages  # noqa: E402

SITE = videos_pages.SITE
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
EXTERNAL = re.compile(r'(?:src|href)="(https?://[^"]+)"')


class Pages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.videos = videos_pages.load()
        cls.pages = videos_pages.pages(cls.videos)
        cls.public = videos_pages.on_youtube(cls.videos)  # videos with a page of their own

    def test_index_and_one_page_per_public_video(self):
        self.assertEqual(len(self.pages), 3 + 3 * len(self.public))
        for lang in videos_pages.LANGS:
            self.assertIn(videos_pages.INDEX[lang], self.pages)
        for k, v in self.videos.items():
            for lang in videos_pages.LANGS:
                self.assertEqual(videos_pages.path(v, lang) in self.pages, bool(v["public"] and not v.get("post")), (k, lang))

    def test_nothing_from_google_loads_before_play(self):
        for p, html in self.pages.items():
            self.assertNotIn("<iframe", html, p)
            for m in re.finditer(r'<(img|script|link)[^>]+(?:src|href)="([^"]+)"', html):
                self.assertFalse(m.group(2).startswith("http") and "rosmarops.com" not in m.group(2), (p, m.group(0)))
            # the only player the script creates is the privacy-enhanced one
            if 'class="vp"' in html:
                self.assertIn("https://www.youtube-nocookie.com/embed/", html)
                self.assertNotIn("youtube.com/embed", html.replace("youtube-nocookie.com/embed", ""))

    def test_player_and_label(self):
        for k, v in self.public:
            for lang in videos_pages.LANGS:
                html = self.pages[videos_pages.path(v, lang)]
                self.assertIn(f'data-yt="{videos_pages.yt(v, lang)}"', html)
                self.assertIn(f'<img src="{videos_pages.thumb(v, lang)}"', html)
                self.assertEqual(videos_pages.L[lang]["ai"] in html, videos_pages.presenter(v))
                self.assertIn(f'href="https://www.youtube.com/watch?v={videos_pages.yt(v, lang)}"', html)
                self.assertIn(f'<h1>{videos_pages.esc(v["title"][lang])}</h1>\n<p class="tp-first">{videos_pages.esc(v["answer"][lang])}</p>', html)

    def test_transcript_and_how_to(self):
        for k, v in self.public:
            for lang in videos_pages.LANGS:
                html = self.pages[videos_pages.path(v, lang)]
                for x in v["how_to"][lang]:
                    self.assertIn(f"<li>{videos_pages.esc(x)}</li>", html)
                for x in v["transcript"][lang]:
                    self.assertIn(f"<p>{videos_pages.esc(x)}</p>", html)
        # the Spanish transcripts are the signed ones (vigil docs/research/2026-11-22-videos-transcripciones.md)
        self.assertTrue(self.videos["paperclip"]["transcript"]["es"][0].startswith("Hola, soy Rosmary"))

    def test_structured_data(self):
        for k, v in self.public:
            for lang in videos_pages.LANGS:
                g = json.loads(LD.findall(self.pages[videos_pages.path(v, lang)])[0])["@graph"]
                vo = g[0]
                self.assertEqual(vo["@type"], "VideoObject")
                self.assertEqual(vo["embedUrl"], f"https://www.youtube-nocookie.com/embed/{v['youtube_id']}")
                self.assertEqual(vo["thumbnailUrl"], "https://rosmarops.com" + v["thumb"])
                self.assertEqual("uploadDate" in vo, bool(v["upload_date"]))
                self.assertEqual(g[1]["@type"], "BreadcrumbList")
        for lang in videos_pages.LANGS:
            g = json.loads(LD.findall(self.pages[videos_pages.INDEX[lang]])[0])["@graph"]
            self.assertEqual(len(g[0]["itemListElement"]), len(videos_pages.public(self.videos)))

    def test_video_in_a_blog_post(self):
        """GTM-67: the homepage video lives in a blog post: a card in the index that links to the post, nothing else."""
        v = self.videos["decide-tu"]
        for lang in videos_pages.LANGS:
            post = v["post"][lang]
            self.assertNotIn(post, self.pages)
            idx = self.pages[videos_pages.INDEX[lang]]
            self.assertIn(f'<h2><a href="{post}">', idx)
            self.assertIn(f'src="{v["thumb"][lang]}"', idx)
            self.assertNotIn(post, [p for p, _ in videos_pages.sitemap_urls(self.videos)])
        self.assertIsNone(videos_pages.top_video({"x": dict(v, topic_page="sandbox")}, "sandbox"))
        bad = copy.deepcopy(self.videos)
        del bad["decide-tu"]["post"]["ca"]
        with self.assertRaises(ValueError):
            videos_pages.check(bad)

    def test_index_newest_first(self):
        html = self.pages["/videos/"]
        order = [html.index(videos_pages.path(v, "en")) for _, v in self.public]
        self.assertEqual(order, sorted(order))
        dates = [v["public_since"] for _, v in self.public]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_check_stops_the_build(self):
        bad = []
        v = copy.deepcopy(self.videos)
        v["paperclip"]["answer"]["ca"] = ""
        bad.append(v)
        v = copy.deepcopy(self.videos)
        v["worktree"]["transcript"]["en"].append("This is safe.")
        bad.append(v)
        v = copy.deepcopy(self.videos)
        v["worktree"]["youtube_id"] = None
        bad.append(v)
        v = copy.deepcopy(self.videos)
        v["paperclip"]["thumb"] = "/assets/video/none.jpg"
        bad.append(v)
        v = copy.deepcopy(self.videos)
        v["paperclip"]["how_to"]["en"] = v["paperclip"]["how_to"]["en"][:2]
        bad.append(v)
        for b in bad:
            with self.assertRaises(ValueError):
                videos_pages.check(b)

    def test_hidden_video_turned_public_appears(self):
        v = copy.deepcopy(self.videos)
        v["trailer"].update(public=True, youtube_id="AAAAAAAAAAA", thumb="/assets/video/paperclip-especial.jpg")
        self.assertIn("/videos/what-is-rosmarops/", videos_pages.pages(v))

    def test_sitemap_and_llms(self):
        sm = (SITE / "sitemap-pages.xml").read_text(encoding="utf-8")
        llms = (SITE / "llms.txt").read_text(encoding="utf-8")
        for path, _ in videos_pages.sitemap_urls(self.videos):
            self.assertIn(f"<loc>https://rosmarops.com{path}</loc>", sm)
        self.assertIn("https://rosmarops.com/videos/", llms)
        for _, v in self.public:
            self.assertIn("https://rosmarops.com" + videos_pages.path(v, "en"), llms)


class Site(unittest.TestCase):
    def test_footer_links_to_videos(self):
        want = {"en": '<a href="/videos/">Videos</a>', "es": '<a href="/es/videos/">Vídeos</a>', "ca": '<a href="/ca/videos/">Vídeos</a>'}
        for f in ("faq/index.html", "es/preguntas-frecuentes/index.html", "ca/preguntes-frequents/index.html",
                  "observatory/index.html", "sandbox/index.html", "videos/index.html", "index.html", "es/index.html", "ca/index.html"):
            html = (SITE / f).read_text(encoding="utf-8")
            footer = html[html.index("<footer"):html.index("</footer>")]
            lang = "es" if f.startswith("es/") else "ca" if f.startswith("ca/") else "en"
            self.assertIn(want[lang], footer, f)

    def test_privacy_explains_videos(self):
        for f, words in (("privacy/index.html", ("youtube-nocookie.com", "unless you press play on a video")),
                         ("es/privacidad/index.html", ("youtube-nocookie.com", "salvo que pulses reproducir en un vídeo")),
                         ("ca/privadesa/index.html", ("youtube-nocookie.com", "tret que premis reproduir en un vídeo"))):
            html = (SITE / f).read_text(encoding="utf-8")
            for w in words:
                self.assertIn(w, html, f)

    def test_sandbox_has_its_video_at_the_top(self):
        v = videos_pages.top_video(videos_pages.load(), "sandbox")
        for f in ("sandbox/index.html", "es/sandbox/index.html", "ca/sandbox/index.html"):
            html = (SITE / f).read_text(encoding="utf-8")
            if v:
                self.assertLess(html.index('class="sg-lead"'), html.index('<div class="vp">'))
                self.assertLess(html.index('<div class="vp">'), html.index('<div class="doc">'))
            self.assertNotIn("<iframe", html)


FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
<entry><yt:videoId>AAAAAAAAAAA</yt:videoId><published>2026-11-25T09:00:00+00:00</published></entry>
<entry><yt:videoId>BBBBBBBBBBB</yt:videoId><published>2026-11-20T09:00:00+00:00</published></entry>
</feed>"""


class Check(unittest.TestCase):
    def test_marks_public_and_fills_dates(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            data = d / "videos"
            data.mkdir()
            (d / "site" / "assets" / "video").mkdir(parents=True)
            base = json.loads((videos_pages.DATA / "trailer.json").read_text(encoding="utf-8"))
            hidden = dict(base, youtube_id="AAAAAAAAAAA", public=False, public_since=None, upload_date=None, thumb="/assets/video/a.jpg")
            other = dict(base, youtube_id="CCCCCCCCCCC", public=False, public_since=None, upload_date=None, thumb="/assets/video/c.jpg")
            already = dict(base, youtube_id="BBBBBBBBBBB", public=True, public_since="2026-11-20", upload_date="2026-11-20", thumb="/assets/video/b.jpg")
            for name, v in (("a", hidden), ("c", other), ("b", already)):
                (data / f"{name}.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
            (d / "site" / "assets" / "video" / "b.jpg").write_bytes(b"x")
            changes = videos_check.update(videos_check.feed_videos(FEED), "2026-11-25", data, d / "site", thumbs=False)
            a = json.loads((data / "a.json").read_text(encoding="utf-8"))
            self.assertTrue(a["public"])
            self.assertEqual(a["public_since"], "2026-11-25")
            self.assertEqual(a["upload_date"], "2026-11-25")
            self.assertFalse(json.loads((data / "c.json").read_text(encoding="utf-8"))["public"])
            self.assertEqual(json.loads((data / "b.json").read_text(encoding="utf-8")), already)
            self.assertIn("a: now public", changes)
            self.assertFalse(any(c.startswith("b:") for c in changes))



FAMILY = Path(__file__).resolve().parent / "fixture" / "videos" / "familia-ordenador-fabricante.json"


class OwnLanguageVideos(unittest.TestCase):
    """GTM-236: a video made in each language, with no presenter (fixture: the «vendor's computer» video as it is
    published on 1-12-2026)."""

    @classmethod
    def setUpClass(cls):
        cls.videos = dict(videos_pages.load(), **{"familia": json.loads(FAMILY.read_text(encoding="utf-8"))})
        cls.v = cls.videos["familia"]
        cls.pages = videos_pages.pages(cls.videos)

    def page(self, lang):
        return self.pages[videos_pages.path(self.v, lang)]

    def test_one_youtube_id_and_thumbnail_per_language(self):
        for lang in videos_pages.LANGS:
            html = self.page(lang)
            self.assertIn(f'data-yt="{self.v["youtube_id"][lang]}"', html)
            self.assertIn(f'<img src="{self.v["thumb"][lang]}"', html)
            for other in videos_pages.LANGS:
                if other != lang:
                    self.assertNotIn(self.v["youtube_id"][other], html)

    def test_no_presenter_label_and_no_spanish_note(self):
        for lang in videos_pages.LANGS:
            html = self.page(lang)
            self.assertNotIn(videos_pages.L[lang]["ai"], html)
            if videos_pages.L[lang]["spanish"]:
                self.assertNotIn(videos_pages.L[lang]["spanish"], html)

    def test_video_language_is_the_page_language(self):
        for lang in videos_pages.LANGS:
            graph = json.loads(LD.search(self.page(lang)).group(1))["@graph"]
            vo = next(x for x in graph if x["@type"] == "VideoObject")
            self.assertEqual(vo["inLanguage"], lang)
            self.assertEqual(vo["description"], self.v["answer"][lang])
            self.assertEqual(vo["thumbnailUrl"], "https://rosmarops.com" + self.v["thumb"][lang])
        # the presenter's videos are still in Spanish
        pc = self.videos["paperclip"]
        self.assertEqual(videos_pages.video_object(pc, "en")["inLanguage"], "es")

    def test_read_more_links_to_the_family(self):
        import minimum
        fam = next(f for f in minimum.families() if f["id"] == self.v["family"])
        for lang in videos_pages.LANGS:
            self.assertIn(f'<li><a href="{fam["path"][lang]}">{videos_pages.esc(fam[lang]["h1"])}</a></li>', self.page(lang))

    def test_transcript_one_paragraph_per_sentence(self):
        for lang in videos_pages.LANGS:
            html = self.page(lang)
            for x in self.v["transcript"][lang]:
                self.assertIn(f"<p>{videos_pages.esc(x)}</p>", html)
        self.assertEqual(self.v["transcript"]["es"][0], self.v["title"]["es"].split(" ¿")[0])

    def test_card_in_each_index(self):
        for lang in videos_pages.LANGS:
            self.assertIn(f'<a href="{videos_pages.path(self.v, lang)}"><img src="{self.v["thumb"][lang]}"', self.pages[videos_pages.INDEX[lang]])

    def test_check_wants_every_language_id(self):
        v = copy.deepcopy(self.videos)
        v["familia"]["youtube_id"]["ca"] = None
        with self.assertRaises(ValueError):
            videos_pages.check(v)

    def test_check_marks_it_public_from_any_of_its_ids(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            d = copy.deepcopy(self.v)
            d.update(public=False, public_since=None)
            (tmp / "familia.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            changes = videos_check.update({d["youtube_id"]["en"]: "2026-12-01"}, "2026-12-01", folder=tmp, site=tmp, thumbs=True)
            self.assertIn("familia: now public", changes)
            self.assertIs(json.loads((tmp / "familia.json").read_text(encoding="utf-8"))["public"], True)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
