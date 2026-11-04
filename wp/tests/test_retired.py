"""Tests for wp/mu-plugins/rosmarops-retired.php: which /es/blog/ addresses answer 301 to /es/blog/.

Run from the repository root:  python3 -m unittest wp/tests/test_retired.py   (needs php on PATH)
"""

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "wp" / "mu-plugins" / "rosmarops-retired.php"

PRODUCT = [  # the product's own posts: never retired
    "que-es-rosmarops", "que-claves-puede-leer-tu-agente-de-ia", "puede-un-agente-de-ia-cambiar-la-configuracion-de-otro",
    "herramientas-que-revisan-a-que-llegan-tus-agentes-de-ia", "mi-maquina-saco-un-18-de-100", "rosmarops-ya-se-puede-descargar",
    "rosmarops-0-3-0", "rosmarops-0-4-0", "como-funciona-la-nota-de-exposicion", "antes-de-decirle-a-tu-agente-que-lo-instale",
    "lo-que-no-se-leyo-no-cuenta-como-limpio", "modo-auto-claude-code-que-puede-leer",
]
KEPT = [  # group 1 (rewritten in place) and group 2 (to qtorb.com) samples: not retired here
    "mcp-seguridad-agentes-cadena-suministro-confianza", "la-capa-de-inferencia-cuando-aprobar-ya-no-es-lo-mismo-que-decidir",
    "europa-en-la-guerra-digital-la-urgencia-de-una-soberania-tecnologica",
]


def targets(uris):
    code = (
        "define('ABSPATH', '/');"
        "function add_action(...$a) {}"
        f"require '{PLUGIN}';"
        "$out = [];"
        "foreach (json_decode(stream_get_contents(STDIN), true) as $u) { $out[$u] = rosmarops_retired_target($u); }"
        "echo json_encode($out);"
    )
    p = subprocess.run(["php", "-r", code], input=json.dumps(uris), capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def listed():
    return re.findall(r"^\t'([^']+)',$", PLUGIN.read_text(encoding="utf-8"), re.M)


class Retired(unittest.TestCase):
    def test_list(self):
        slugs = listed()
        self.assertEqual(len(slugs), 90)
        self.assertEqual(len(set(slugs)), 90)
        for s in PRODUCT + KEPT:
            self.assertNotIn(s, slugs)
        for page in ("guerra-de-la-informacion-iw", "ai-seo", "ciberseguridad-en-ia", "seo-adversarial", "agentes-autonomia"):
            self.assertIn(page, slugs)

    def test_retired_addresses(self):
        t = targets([
            "/es/blog/como-construir-un-ejercito-de-bots-para-manipulacion-de-seo-guia-tecnica/",
            "/es/blog/como-construir-un-ejercito-de-bots-para-manipulacion-de-seo-guia-tecnica",
            "/es/blog/ai-seo/?utm=x",
            "/es/blog/redes-de-proxys-dinamicas-la-clave-para-el-anonimato-y-la-flexibilidad-en-linea/feed/",
        ])
        self.assertEqual(set(t.values()), {"/es/blog/"})

    def test_untouched_addresses(self):
        uris = [f"/es/blog/{s}/" for s in PRODUCT + KEPT] + [
            "/es/blog/", "/es/", "/blog/ai-seo/", "/ca/blog/ai-seo/", "/es/blog/category/seo/", "/ai-seo/", "/es/blog/ai-seo-x/",
        ]
        self.assertEqual(set(targets(uris).values()), {None})


if __name__ == "__main__":
    unittest.main()


def blog_categories(urls):
    code = (
        "define('ABSPATH', '/');"
        "function add_action(...$a) {}"
        f"require '{PLUGIN}';"
        "$out = [];"
        "foreach (json_decode(stream_get_contents(STDIN), true) as $u) { $out[$u] = rosmarops_blog_categories($u); }"
        "echo json_encode($out);"
    )
    p = subprocess.run(["php", "-r", code], input=json.dumps(urls), capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


class BlogHome(unittest.TestCase):
    def test_only_spanish_home_is_limited(self):
        c = blog_categories(["https://rosmarops.com/es", "https://rosmarops.com/es/", "https://rosmarops.com", "https://rosmarops.com/ca"])
        three = ["novedades-de-rosmarops", "que-puede-hacer-tu-agente", "metodologia"]
        self.assertEqual(c["https://rosmarops.com/es"], three)
        self.assertEqual(c["https://rosmarops.com/es/"], three)
        self.assertIsNone(c["https://rosmarops.com"])
        self.assertIsNone(c["https://rosmarops.com/ca"])
