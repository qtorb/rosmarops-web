"""site_check.py: the generated pages travel with the change that makes them (advisor, 17-11)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import site_check  # noqa: E402

# A stand-in for build.py: writes site/observatory/<agent>.json from data/agents/<agent>.json, as the real build does.
FAKE_BUILD = """
import pathlib
for f in pathlib.Path("data/agents").glob("*.json"):
    out = pathlib.Path("site/observatory") / f.name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("page of " + f.read_text())
"""


def run(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class SiteCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        run(self.root, "init", "-q")
        run(self.root, "config", "user.email", "t@example.com")
        run(self.root, "config", "user.name", "t")
        (self.root / "build.py").write_text(FAKE_BUILD)
        (self.root / "data/agents").mkdir(parents=True)
        (self.root / "data/agents/kiro.json").write_text('{"changes": []}')
        self.build = [sys.executable, "build.py"]
        site_check.stale(self.root, self.build)
        run(self.root, "add", "-A")
        run(self.root, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def daily_change(self):
        """What the writer did on 17-11: a new entry in an agent file, and a new agent."""
        (self.root / "data/agents/kiro.json").write_text('{"changes": [1]}')
        (self.root / "data/agents/qwen-code.json").write_text('{"changes": [1]}')
        run(self.root, "add", "data")

    def test_up_to_date_after_a_clean_build(self):
        self.assertEqual(site_check.stale(self.root, self.build), [])

    def test_the_daily_of_17_11_fails_before_pushing(self):
        self.daily_change()
        lines = site_check.stale(self.root, self.build)
        self.assertIn(" M site/observatory/kiro.json", lines)
        self.assertIn("?? site/observatory/qwen-code.json", lines)

    def test_stage_puts_the_regenerated_pages_in_the_same_commit(self):
        self.daily_change()
        self.assertEqual(site_check.stale(self.root, self.build, stage=True), [])
        run(self.root, "commit", "-q", "-m", "observatory: daily")
        shown = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=self.root, check=True,
                               capture_output=True, text=True).stdout.split()
        self.assertEqual(sorted(shown), ["data/agents/kiro.json", "data/agents/qwen-code.json",
                                         "site/observatory/kiro.json", "site/observatory/qwen-code.json"])
        self.assertEqual(site_check.stale(self.root, self.build), [])

    def test_a_failing_build_stops_the_check(self):
        (self.root / "build.py").write_text("raise SystemExit(2)")
        with self.assertRaises(subprocess.CalledProcessError):
            site_check.stale(self.root, self.build)

    def test_the_paths_are_the_ones_the_ci_checks(self):
        self.assertEqual(site_check.GENERATED, ["site", "wp/daily", "wp/pages", "wp/mu-plugins/rosmarops-downloads.php"])


if __name__ == "__main__":
    unittest.main()
