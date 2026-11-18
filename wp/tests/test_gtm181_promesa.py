"""Tests for wp/mu-plugins/rosmarops-gtm181-promesa.php: the 0.15.0 promise in WordPress (GTM-181). The program's
privacy policy replaced (EN, ES) or created (CA, under a published parent «privadesa»), a dated line at the start of
14 posts, and four pages that the static site already serves set to draft. The policies' parents stay published.

Run from the repository root:  python3 -m unittest wp/tests/test_gtm181_promesa.py   (needs php on PATH)
"""

import html
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SITES = {"en": "https://rosmarops.com", "es": "https://rosmarops.com/es", "ca": "https://rosmarops.com/ca"}
POLICY = {"en": "https://rosmarops.com/privacy/app/", "es": "https://rosmarops.com/es/privacidad/app/",
          "ca": "https://rosmarops.com/ca/privadesa/app/"}
# Signed by Albert on 18-11 at 17:43 (the promise) and 17:52 (GTM-181).
PROMISE = {
    "en": "Nothing it reads on your computer leaves without your permission, and your keys never do.",
    "es": "Lo que lee de tu ordenador no sale sin tu permiso, y tus claves nunca.",
    "ca": "El que llegeix del teu ordinador no surt sense el teu permís, i les teves claus mai.",
}
LINE = {
    "en": "Update, 18-11-2026: from version 0.15.0, RosmarOps can send usage statistics if you give permission. "
          "Nothing it reads on your computer leaves without your permission, and your keys never do. "
          "What exactly it sends: the program's privacy policy.",
    "es": "Actualización del 18-11-2026: desde la versión 0.15.0, RosmarOps puede enviar estadísticas de uso si das permiso. "
          "Lo que lee de tu ordenador no sale sin tu permiso, y tus claves nunca. "
          "Qué envía exactamente: política de privacidad del programa.",
    "ca": "Actualització del 18-11-2026: des de la versió 0.15.0, RosmarOps pot enviar estadístiques d'ús si dones permís. "
          "El que llegeix del teu ordinador no surt sense el teu permís, i les teves claus mai. "
          "Què envia exactament: política de privadesa del programa.",
}
POSTS = {
    "en": {990: "my-machine-scored-18-of-100", 1176: "rosmarops-is-out", 1184: "rosmarops-0-3-0", 1189: "rosmarops-0-4-0",
           1202: "which-keys-can-your-ai-coding-agent-read"},
    "es": {1144: "mi-maquina-saco-un-18-de-100", 1163: "rosmarops-ya-se-puede-descargar", 1172: "rosmarops-0-3-0",
           1177: "rosmarops-0-4-0", 1191: "que-claves-puede-leer-tu-agente-de-ia"},
    "ca": {20: "la-meva-maquina-va-treure-un-18-de-100", 24: "rosmarops-ja-es-pot-descarregar", 37: "rosmarops-0-4-0",
           47: "quines-claus-pot-llegir-el-teu-agent-dia"},
}
DRAFTS = {"en": {993: "home", 1153: "about"}, "es": {34: "que-es-rosmarops"}, "ca": {25: "que-es-rosmarops"}}
KEEP = {"en": {1168: "privacy"}, "es": {1153: "privacidad"}, "ca": {}}  # the policies' parents: stay published
OLD = {"en": "<p>RosmarOps never connects to the network. It never sends telemetry.</p>",
       "es": "<p>RosmarOps nunca se conecta a la red. Nunca envía telemetría.</p>"}


def text(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"</?(a|em|strong|code)\b[^>]*>", "", s)  # inline tags: no space
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


class Gtm181(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.dbf = root / "db.json"
        self.content = root / "wp-content"
        self.content.mkdir()

    def db(self, lang, change=None):
        posts = []
        if lang in OLD:
            parent = next(iter(KEEP[lang]))
            posts.append({"ID": parent, "post_name": KEEP[lang][parent], "post_type": "page", "post_status": "publish",
                          "post_parent": 0, "post_content": "<p>web privacy</p>"})
            posts.append({"ID": 1175 if lang == "en" else 1162, "post_name": "app", "post_type": "page", "post_status": "publish",
                          "post_parent": parent, "post_title": "old", "post_content": OLD[lang]})
        for i, s in POSTS[lang].items():
            posts.append({"ID": i, "post_name": s, "post_type": "post", "post_status": "publish", "post_content": f"<p>body {i}</p>"})
        for i, s in DRAFTS[lang].items():
            posts.append({"ID": i, "post_name": s, "post_type": "page", "post_status": "publish", "post_content": "<p>x</p>"})
        data = {"options": {}, "posts": posts, "post_meta": {}, "cleaned": [],
                "users": [{"ID": 1, "display_name": "Albert Garcia Pujadas", "roles": ["administrator"]}]}
        if change:
            change(data)
        return data

    def run_once(self, home, data=None):
        if data is not None:
            self.dbf.write_text(json.dumps(data), encoding="utf-8")
        env = dict(os.environ, GTM181_DB=str(self.dbf), GTM181_CONTENT=str(self.content))
        p = subprocess.run(["php", str(TESTS / "gtm181-stub.php"), home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    def by_id(self, out):
        return {p["ID"]: p for p in out["posts"]}

    def test_policy_replaced_en_es(self):
        titles = {"en": "RosmarOps program privacy policy", "es": "Política de privacidad del programa RosmarOps"}
        for lang in ("en", "es"):
            log, out = self.run_once(SITES[lang], self.db(lang))
            pid = 1175 if lang == "en" else 1162
            p = self.by_id(out)[pid]
            t = text(p["post_content"])
            self.assertEqual(p["post_title"], titles[lang])
            self.assertIn(PROMISE[lang], t)
            self.assertIn("0.15.0", t)
            self.assertIn("rosmarops usage off", t)
            self.assertIn("https://app.rosmarops.com/privacy", t)
            self.assertNotIn(OLD[lang], p["post_content"])
            self.assertEqual(p["post_modified"], "2026-11-18 19:00:00")
            self.assertEqual(out["post_meta"][str(pid)], {"rosmarops_url_ca": POLICY["ca"]})
            parent = next(iter(KEEP[lang]))
            self.assertEqual(self.by_id(out)[parent]["post_status"], "publish", "the policy's parent stays published")
            self.assertTrue(any(l.startswith(f"done: policy page {pid}") for l in log), log)

    def test_ca_policy_created_under_a_published_parent(self):
        log, out = self.run_once(SITES["ca"], self.db("ca"))
        parent = next(p for p in out["posts"] if p["post_name"] == "privadesa")
        child = next(p for p in out["posts"] if p["post_name"] == "app")
        self.assertEqual((parent["post_type"], parent["post_status"], parent["post_content"], parent["post_title"]),
                         ("page", "publish", "", "Privadesa i galetes"))
        self.assertEqual((child["post_type"], child["post_status"], child["post_parent"]), ("page", "publish", parent["ID"]))
        self.assertEqual(child["post_title"], "Política de privadesa del programa RosmarOps")
        t = text(child["post_content"])
        self.assertIn(PROMISE["ca"], t)
        self.assertIn("El que treus tu", t)
        self.assertEqual(out["post_meta"][str(child["ID"])], {"rosmarops_url_en": POLICY["en"], "rosmarops_url_es": POLICY["es"]})

    def test_ca_existing_parent_is_reused_and_existing_child_is_not_touched(self):
        def parent(d):
            d["posts"].append({"ID": 70, "post_name": "privadesa", "post_type": "page", "post_status": "publish", "post_parent": 0, "post_content": ""})
        log, out = self.run_once(SITES["ca"], self.db("ca", parent))
        self.assertEqual(sum(1 for p in out["posts"] if p["post_name"] == "privadesa"), 1)
        self.assertEqual(next(p for p in out["posts"] if p["post_name"] == "app")["post_parent"], 70)

        def both(d):
            parent(d)
            d["posts"].append({"ID": 71, "post_name": "app", "post_type": "page", "post_status": "draft", "post_parent": 70, "post_content": "mine"})
        log, out = self.run_once(SITES["ca"], self.db("ca", both))
        self.assertEqual(self.by_id(out)[71]["post_content"], "mine")
        self.assertTrue(any(l.startswith("skipped: CA policy") for l in log), log)

    def test_dated_line_at_the_start_of_the_14_posts_only(self):
        for lang, posts in POSTS.items():
            log, out = self.run_once(SITES[lang], self.db(lang))
            for i in posts:
                c = self.by_id(out)[i]["post_content"]
                self.assertTrue(c.endswith(f"<p>body {i}</p>"), (lang, i))
                first = c[:c.index("<!-- /wp:paragraph -->")]
                self.assertEqual(text(first), LINE[lang], (lang, i))
                self.assertIn(f'href="{POLICY[lang]}"', first)
                self.assertIn("<em>", first)
        self.assertEqual(sum(len(p) for p in POSTS.values()), 14)

    def test_four_pages_to_draft_and_nothing_else(self):
        for lang in SITES:
            log, out = self.run_once(SITES[lang], self.db(lang))
            for i in DRAFTS[lang]:
                self.assertEqual(self.by_id(out)[i]["post_status"], "draft", (lang, i))
            for i in KEEP[lang]:
                self.assertEqual(self.by_id(out)[i]["post_status"], "publish", (lang, i))
            for i in POSTS[lang]:
                self.assertEqual(self.by_id(out)[i]["post_status"], "publish", (lang, i))
        self.assertEqual(sum(len(d) for d in DRAFTS.values()), 4)

    def test_anything_unexpected_is_left_alone(self):
        def odd(d):
            for p in d["posts"]:
                if p["ID"] == 990:
                    p["post_status"] = "draft"
                if p["ID"] == 1176:
                    p["post_name"] = "renamed"
                if p["ID"] == 1175:
                    p["post_content"] = "<p>someone already changed it</p>"
                if p["ID"] == 993:
                    p["post_type"] = "post"
        log, out = self.run_once(SITES["en"], self.db("en", odd))
        b = self.by_id(out)
        self.assertEqual(b[990]["post_content"], "<p>body 990</p>")
        self.assertEqual(b[1176]["post_content"], "<p>body 1176</p>")
        self.assertEqual(b[1175]["post_content"], "<p>someone already changed it</p>")
        self.assertEqual(b[993]["post_status"], "publish")
        self.assertEqual(sum(1 for l in log if l.startswith("skipped:")), 4, log)

    def test_runs_once_and_never_twice_the_line(self):
        self.run_once(SITES["es"], self.db("es"))
        log, out = self.run_once(SITES["es"])
        self.assertIsNone(log)
        self.assertEqual(self.by_id(out)[1144]["post_content"].count("rosmarops-gtm181"), 2)  # block attribute + class, once

        def already(d):
            for p in d["posts"]:
                if p["ID"] == 1144:
                    p["post_content"] = '<p class="rosmarops-gtm181"><em>x</em></p><p>body 1144</p>'
        log, out = self.run_once(SITES["es"], self.db("es", already))
        self.assertIn("skipped: post 1144 mi-maquina-saco-un-18-de-100 already has the line", log)

    def test_other_sites_and_log(self):
        log, _ = self.run_once("https://example.com", self.db("en"))
        self.assertIsNone(log)
        self.run_once(SITES["en"], self.db("en"))
        f = self.content / "rosmarops-private" / "gtm181-en.log"
        self.assertTrue(f.is_file())
        self.assertEqual((self.content / "rosmarops-private" / ".htaccess").read_text(), "Require all denied\n")

    def test_policies_match_in_structure(self):
        # Same sections in the three languages, and the program's privacy policy is the one the site links to.
        sections = {}
        for lang in SITES:
            _, out = self.run_once(SITES[lang], self.db(lang))
            p = next(p for p in out["posts"] if p["post_name"] == "app")
            sections[lang] = (len(re.findall(r"<h2", p["post_content"])), len(re.findall(r"<li>", p["post_content"])))
        self.assertEqual(sections["en"], (6, 5))
        self.assertEqual(sections["en"], sections["es"])
        self.assertEqual(sections["en"], sections["ca"])
        repo = TESTS.parents[1]
        for f, url in [("site/index.html", "/privacy/app/"), ("site/es/index.html", "/es/privacidad/app/"),
                       ("site/ca/index.html", "/ca/privadesa/app/")]:
            self.assertIn(f'href="{url}"', (repo / f).read_text(encoding="utf-8"), f)


if __name__ == "__main__":
    unittest.main()
