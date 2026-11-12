"""GTM-111: every ?from= the site sends to the download counter is on its closed list, and the team is not counted.

Run from the repository root:  python3 -m unittest wp/tests/test_download_sources.py   (needs php on PATH)
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "wp" / "mu-plugins" / "rosmarops-downloads.php"
sys.path.insert(0, str(ROOT / "observatory"))


def closed_list():
    src = PLUGIN.read_text(encoding="utf-8").split("ROSMAROPS_DL_FROM   = [")[1].split("];")[0]
    return re.findall(r"'([a-z0-9-]+)'", src)


def sent_values():
    """(file, from) for every link to /download, /es/descargar or /ca/descarregar in site/ and wp/ (not wp/tests)."""
    rx = re.compile(r"/(?:download|es/descargar|ca/descarregar)/?\?([^\"'<>\s)]*)")
    out = []
    for f in sorted(list((ROOT / "site").rglob("*")) + list((ROOT / "wp").rglob("*"))):
        if not f.is_file() or "tests" in f.relative_to(ROOT).parts or f.suffix not in {".html", ".php", ".js", ".txt", ".json", ".md"}:
            continue
        for q in rx.findall(f.read_text(encoding="utf-8", errors="replace")):
            m = re.search(r"(?:^|&|&amp;)from=([^&]+)", q)
            if m:
                out.append((str(f.relative_to(ROOT)), m.group(1)))
    return out


class Sources(unittest.TestCase):
    def test_every_from_is_on_the_list(self):
        allowed = set(closed_list())
        sent = sent_values()
        self.assertTrue(sent, "no download links found")
        missing = sorted({f"{v} ({f})" for f, v in sent if v not in allowed})
        self.assertEqual(missing, [], "these ?from= values would be counted as «other»")

    def test_observatory_part_follows_the_published_pages(self):
        import build
        agents = build.load_agents()
        want = {f"observatory-{a['agent']['id']}" for a in agents if build.is_published(a)}
        have = {v for v in closed_list() if v.startswith("observatory-")} - {"observatory-map"}  # GTM-138: the map
        self.assertEqual(have, want)

    def test_team_cookie(self):
        code = ("require 'wp/tests/wp-stub-min.php'; require 'wp/mu-plugins/rosmarops-downloads.php';"
                "echo json_encode([rosmarops_is_team(['wordpress_logged_in_abc123' => 'x']), rosmarops_is_team(['cc_cookie' => 'x']),"
                " rosmarops_is_team([]), rosmarops_is_team(['wordpress_test_cookie' => 'x', 'wordpress_sec_1' => 'x'])]);")
        p = subprocess.run(["php", "-r", code], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(p.stdout, "[true,false,false,false]")


if __name__ == "__main__":
    unittest.main()
