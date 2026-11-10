"""GTM-130b: the footer paragraph that wp/mu-plugins/rosmarops-consent.php adds to the blogs, in the three languages.

Run from the repository root:  python3 -m unittest wp/tests/test_consent_footer.py   (needs php on PATH)
"""

import json
import subprocess
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
PLUGIN = TESTS.parent / "mu-plugins" / "rosmarops-consent.php"
STYLE = '<p class="rosmarops-cc-link" style="text-align:center;font-size:14px;margin:16px 0">'
WANT = {
    "es_ES": '<a href="/es/privacidad/">Privacidad</a> · <a href="/es/aviso-legal/">Aviso legal</a> · <a href="/es/terminos/">Términos</a> · <a href="#" data-cc="show-preferencesModal">Configurar cookies</a>',
    "ca": '<a href="/ca/privadesa/">Privadesa</a> · <a href="/ca/avis-legal/">Avís legal</a> · <a href="/ca/termes/">Termes</a> · <a href="#" data-cc="show-preferencesModal">Configura les galetes</a>',
    "en_US": '<a href="/privacy/">Privacy</a> · <a href="/legal-notice/">Legal notice</a> · <a href="/terms/">Terms</a> · <a href="#" data-cc="show-preferencesModal">Cookie settings</a>',
}
STUB = r"""
define('ABSPATH', '/');
$GLOBALS['actions'] = [];
function add_action($h, $cb, $p = 10) { $GLOBALS['actions'][$h][] = $cb; }
function esc_attr($s) { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
function esc_html($s) { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
function get_locale() { return $GLOBALS['locale']; }
require %s;
$GLOBALS['locale'] = $argv[1];
ob_start();
foreach ($GLOBALS['actions']['wp_footer'] as $cb) { $cb(); }
echo ob_get_clean();
"""


def footer(locale):
    code = STUB % json.dumps(str(PLUGIN))
    return subprocess.run(["php", "-r", code, locale], capture_output=True, text=True, check=True).stdout


class ConsentFooter(unittest.TestCase):
    def test_three_languages(self):
        for locale, links in WANT.items():
            self.assertEqual(footer(locale), STYLE + links + "</p>", locale)

    def test_unknown_locale_is_english(self):
        self.assertEqual(footer("de_DE"), STYLE + WANT["en_US"] + "</p>")

    def test_links_go_to_pages_that_exist(self):
        site = TESTS.parents[1] / "site"
        for links in WANT.values():
            for href in __import__("re").findall(r'href="(/[^"]+)"', links):
                self.assertTrue((site / href.strip("/") / "index.html").is_file(), href)


if __name__ == "__main__":
    unittest.main()
