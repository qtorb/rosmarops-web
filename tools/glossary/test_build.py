"""Tests for tools/glossary/build.py (GTM-206): mark() links each term to its own anchor on the glossary page.

Run from the repository root:  python3 -m unittest tools/glossary/test_build.py
"""
import importlib.util
import pathlib
import re
import unittest

HERE = pathlib.Path(__file__).resolve().parent
# Loaded by path under its own name: other tools in the same test run also have a build.py.
_spec = importlib.util.spec_from_file_location('glossary_build', HERE / 'build.py')
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

ROOT = HERE.parents[1]


class Mark(unittest.TestCase):
    def setUp(self):
        self.saved = (build.TERMS, dict(build.PATTERNS['es']))
        build.TERMS = build.TERMS + [{"id": "x-test", "anchors": {"es": "prueba-x", "en": "x-test", "ca": "prova-x"},
                                      "en": ["X test", "."], "es": ["Prueba X", "."], "ca": ["Prova X", "."]}]
        build.PATTERNS['es']['x-test'] = r'prueba x'

    def tearDown(self):
        build.TERMS, pat = self.saved
        build.PATTERNS['es'].clear()
        build.PATTERNS['es'].update(pat)

    def test_link_uses_the_terms_own_anchor(self):
        s, missing = build.mark('<main><p>Una prueba X aquí.</p></main>', 'es', ['x-test'])
        self.assertEqual(missing, [])
        self.assertIn('href="/es/glosario/#prueba-x"', s)
        self.assertNotIn('#x-test"', s)

    def test_a_hyphenated_term_already_marked_is_not_marked_again(self):
        once, _ = build.mark('<main><p>Una prueba X aquí.</p></main>', 'es', ['x-test'])
        twice, missing = build.mark(once, 'es', ['x-test'])
        self.assertEqual(twice, once)
        self.assertEqual(missing, [])


class Pages(unittest.TestCase):
    def test_every_term_has_its_anchor_on_each_glossary_page(self):
        for lang, path in (('en', 'glossary'), ('es', 'es/glosario'), ('ca', 'ca/glossari')):
            page = (ROOT / 'site' / path / 'index.html').read_text(encoding='utf-8')
            ids = set(re.findall(r'<dt id="([^"]+)">', page))
            for t in build.TERMS:
                self.assertIn(build.anchor(t, lang), ids, (lang, t['id']))

    def test_every_glossary_link_on_the_site_points_to_an_anchor_that_exists(self):
        pages = {'en': 'glossary', 'es': 'es/glosario', 'ca': 'ca/glossari'}
        ids = {l: set(re.findall(r'<dt id="([^"]+)">', (ROOT / 'site' / p / 'index.html').read_text(encoding='utf-8')))
               for l, p in pages.items()}
        for f in (ROOT / 'site').rglob('*.html'):
            for base, a in re.findall(r'href="(/glossary/|/es/glosario/|/ca/glossari/)#([^"]+)"', f.read_text(encoding='utf-8')):
                lang = {'/glossary/': 'en', '/es/glosario/': 'es', '/ca/glossari/': 'ca'}[base]
                self.assertIn(a, ids[lang], (str(f.relative_to(ROOT)), base + '#' + a))


if __name__ == '__main__':
    unittest.main()
