"""Tests for observatory/daily_alert.py (GTM-23 §7). Run: python3 -m unittest observatory/tests/test_daily_alert.py"""

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import daily_alert  # noqa: E402

VALID = ROOT / "observatory" / "tests" / "daily" / "2026-01-15.json"


class Alert(unittest.TestCase):
    def msgs(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "2026-01-15.json"
            p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return daily_alert.for_file(p)

    def setUp(self):
        self.d = json.loads(VALID.read_text(encoding="utf-8"))

    def test_held(self):
        m = self.msgs(self.d)
        self.assertEqual([x["Subject"] for x in m], ["Sinopsis diaria 2026-01-15: retenidos"])
        self.assertEqual(m[0]["To"], "albert@rosmarops.com")

    def test_clean_day_no_alert(self):
        d = copy.deepcopy(self.d)
        d["held"] = []
        self.assertEqual(self.msgs(d), [])

    def test_incomplete(self):
        d = copy.deepcopy(self.d)
        d.update(status="incomplete", items=[], not_checked=["F3 OpenAI Codex"])
        self.assertIn("revisión incompleta", self.msgs(d)[0]["Subject"])

    def test_invalid(self):
        d = copy.deepcopy(self.d)
        d["items"][0]["source_url"] = "https://evil.example/x"
        self.assertIn("fichero no válido", self.msgs(d)[0]["Subject"])

    def test_missing(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["ALERT_DIR"] = d
            daily_alert.main(["missing", "2026-10-30"])
            m = json.loads((Path(d) / "0.json").read_text(encoding="utf-8"))
        self.assertEqual(m["Subject"], "Sinopsis diaria 2026-10-30: sin fichero a las 09:30")


if __name__ == "__main__":
    unittest.main()
