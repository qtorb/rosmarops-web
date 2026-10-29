"""Runs wp/tests/seo-check.php (GTM-21). python3 -m unittest wp/tests/test_seo.py"""
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Seo(unittest.TestCase):
    def test_seo_plugin(self):
        r = subprocess.run(["php", str(HERE / "seo-check.php")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
