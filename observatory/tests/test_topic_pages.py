"""Tests for observatory/topic_pages.py (GTM-198): the three standing pages in EN, ES and CA."""

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import topic_pages  # noqa: E402

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


class TopicPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = topic_pages.load()
        cls.pages = topic_pages.pages(cls.data)

    def test_nine_pages(self):
        self.assertEqual(len(self.pages), 9)
        for p in self.data["pages"].values():
            self.assertEqual(set(p["path"]), {"en", "es", "ca"})

    def test_first_sentence_right_after_the_h1(self):
        for pid, p in self.data["pages"].items():
            for lang in topic_pages.LANGS:
                html = self.pages[p["path"][lang]]
                t = p[lang]
                h1 = f"<h1>{topic_pages.esc(t['title'])}</h1>\n<p class=\"tp-first\">{topic_pages.esc(t['first'])}</p>"
                self.assertIn(h1, html, f"{pid}/{lang}")
                self.assertIn(f"<title>{topic_pages.esc(t['title'])} · RosmarOps</title>", html)
                self.assertIn(f'<meta name="description" content="{topic_pages.esc(t["desc"])}">', html)

    def test_hreflang_and_canonical(self):
        for p in self.data["pages"].values():
            for lang in topic_pages.LANGS:
                html = self.pages[p["path"][lang]]
                self.assertIn(f'<link rel="canonical" href="https://rosmarops.com{p["path"][lang]}">', html)
                for o in topic_pages.LANGS:
                    self.assertIn(f'hreflang="{o}" href="https://rosmarops.com{p["path"][o]}"', html)
                self.assertIn(f'hreflang="x-default" href="https://rosmarops.com{p["path"]["en"]}"', html)
                self.assertIn(f'<html lang="{lang}">', html)

    def test_structured_data(self):
        for p in self.data["pages"].values():
            for lang in topic_pages.LANGS:
                blocks = LD.findall(self.pages[p["path"][lang]])
                self.assertEqual(len(blocks), 1)
                graph = json.loads(blocks[0])["@graph"]
                types = [g["@type"] for g in graph]
                self.assertEqual(types[:3], ["TechArticle", "FAQPage", "BreadcrumbList"])
                faq = graph[1]["mainEntity"][0]
                self.assertEqual(faq["name"], p[lang]["title"])
                self.assertEqual(faq["acceptedAnswer"]["text"], p[lang]["first"])
                public = [v for v in p["videos"] if self.data["videos"][v]["public"]]
                self.assertEqual(types.count("VideoObject"), len(public))

    def test_videos_only_when_public(self):
        for p in self.data["pages"].values():
            for lang in topic_pages.LANGS:
                html = self.pages[p["path"][lang]]
                for v in p["videos"]:
                    vv = self.data["videos"][v]
                    if vv["public"]:
                        self.assertIn(f'href="{vv["url"]}"', html)
                        self.assertTrue((topic_pages.SITE / vv["thumb"].lstrip("/")).exists(), vv["thumb"])
                    else:
                        self.assertNotIn(topic_pages.esc(vv["name"]), html)
        # A video turned public appears; one turned private disappears.
        d = copy.deepcopy(self.data)
        d["videos"]["mcp"].update(public=True, url="https://youtu.be/x", id="x", thumb="/assets/video/paperclip-especial.jpg")
        self.assertIn('href="https://youtu.be/x"', topic_pages.pages(d)["/mcp-servers/"])
        d["videos"]["paperclip"]["public"] = False
        self.assertNotIn("2IKYyCEKZ0E", topic_pages.pages(d)["/agent-orchestrators/"])

    def test_no_forbidden_words_and_the_check_stops_the_build(self):
        for html in self.pages.values():
            article = html[html.index("<article"):html.index("</article>")]
            self.assertIsNone(topic_pages.FORBIDDEN.search(re.sub(r"<[^>]+>", " ", article)))
        for word in ("safe", "seguro", "protegeix", "no telemetry"):
            d = copy.deepcopy(self.data)
            d["pages"]["mcp"]["es"]["sections"][0]["body"] = [f"<p>Esto es {word}.</p>"]
            with self.assertRaises(ValueError):
                topic_pages.pages(d)

    def test_not_said(self):
        # Proposal: the MCP page says nothing about unpinned versions or auto-approval of project servers (CTO-79 §2).
        for lang in topic_pages.LANGS:
            html = self.pages[self.data["pages"]["mcp"]["path"][lang]].lower()
            for word in ("enableallprojectmcpservers", "unpinned", "sin fijar", "sense fixar", "auto-approv", "aprobación automática", "aprovació automàtica"):
                self.assertNotIn(word, html)

    def test_internal_links_exist(self):
        site = topic_pages.SITE
        for p in self.data["pages"].values():
            for lang in topic_pages.LANGS:
                for _, href in p[lang]["links"]:
                    if "/blog/" in href:
                        continue  # WordPress, not in site/
                    self.assertTrue((site / href.strip("/") / "index.html").exists(), href)

    def test_build_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            topic_pages.build(d, self.data)
            for p in self.data["pages"].values():
                for path in p["path"].values():
                    self.assertTrue((Path(d) / path.strip("/") / "index.html").exists())

    def test_sitemap_and_llms(self):
        urls = topic_pages.sitemap_urls(self.data)
        self.assertEqual(len(urls), 9)
        lines = topic_pages.llms_lines(self.data)
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(l.startswith("- [") and "https://rosmarops.com/" in l for l in lines))
        sm = (topic_pages.SITE / "sitemap-pages.xml").read_text(encoding="utf-8")
        llms = (topic_pages.SITE / "llms.txt").read_text(encoding="utf-8")
        for p in self.data["pages"].values():
            for path in p["path"].values():
                self.assertIn(f"<loc>https://rosmarops.com{path}</loc>", sm)
            self.assertIn(f"https://rosmarops.com{p['path']['en']}", llms)


if __name__ == "__main__":
    unittest.main()
