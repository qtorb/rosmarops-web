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
        cls.public = videos_pages.public(cls.videos)

    def test_index_and_one_page_per_public_video(self):
        self.assertEqual(len(self.pages), 3 + 3 * len(self.public))
        for lang in videos_pages.LANGS:
            self.assertIn(videos_pages.INDEX[lang], self.pages)
        for k, v in self.videos.items():
            for lang in videos_pages.LANGS:
                self.assertEqual(videos_pages.path(v, lang) in self.pages, bool(v["public"]), (k, lang))

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
                self.assertIn(f'data-yt="{v["youtube_id"]}"', html)
                self.assertIn(f'<img src="{v["thumb"]}"', html)
                self.assertIn(videos_pages.L[lang]["ai"], html)
                self.assertIn(f'href="https://www.youtube.com/watch?v={v["youtube_id"]}"', html)
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
            self.assertEqual(len(g[0]["itemListElement"]), len(self.public))

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


if __name__ == "__main__":
    unittest.main()
