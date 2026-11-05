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
            m = json.loads((Path(d) / "missing-0.json").read_text(encoding="utf-8"))
        self.assertEqual(m["Subject"], "Sinopsis diaria 2026-10-30: sin fichero a las 15:30")


def raw_file(folder, date, closed):
    """A raw file with F1 and F22; `closed` maps a source id to its reason."""
    srcs = [{"id": i, "opened": i not in closed, "reason": closed.get(i), "latest": None, "latest_date": None,
             "new": [], "ids": [], "read_with": "git"} for i in ("F1", "F22")]
    (Path(folder) / f"{date}.json").write_text(json.dumps({"date": date, "sources": srcs}), encoding="utf-8")


class Repeat(unittest.TestCase):
    """GTM-90: a source closed two days in a row, and a day without collector data."""

    def run_repeat(self, days):
        with tempfile.TemporaryDirectory() as d:
            for date, closed in days.items():
                raw_file(d, date, closed)
            return daily_alert.for_repeat("2026-11-05", raw_dir=d)

    def test_two_days_in_a_row(self):
        m = self.run_repeat({"2026-11-04": {"F22": "HTTP 502"}, "2026-11-05": {"F22": "new version without notes"}})
        self.assertEqual([x["Subject"] for x in m], ["Observatorio: fuente que falla 2 días seguidos (2026-11-05)"])
        self.assertEqual(m[0]["To"], "albert@rosmarops.com")
        self.assertIn("- F22 OpenClaw: 2026-11-04: HTTP 502 | 2026-11-05: new version without notes", m[0]["TextBody"])
        self.assertNotIn("F1 ", m[0]["TextBody"])

    def test_one_day_only(self):
        self.assertEqual(self.run_repeat({"2026-11-04": {}, "2026-11-05": {"F22": "HTTP 502"}}), [])
        self.assertEqual(self.run_repeat({"2026-11-04": {"F22": "HTTP 502"}, "2026-11-05": {}}), [])

    def test_different_sources(self):
        self.assertEqual(self.run_repeat({"2026-11-04": {"F1": "x"}, "2026-11-05": {"F22": "y"}}), [])

    def test_no_previous_day(self):
        self.assertEqual(self.run_repeat({"2026-11-05": {"F22": "HTTP 502"}}), [])

    def test_raw_missing(self):
        m = self.run_repeat({"2026-11-04": {"F22": "HTTP 502"}})
        self.assertEqual([x["Subject"] for x in m], ["Observatorio: sin datos del recolector (2026-11-05)"])
        self.assertEqual(m[0]["To"], "albert@rosmarops.com")

    def test_cli_missing_and_repeat_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as out:
            old = daily_alert.RAW_DIR
            daily_alert.RAW_DIR = Path(raw)
            os.environ["ALERT_DIR"] = out
            try:
                daily_alert.main(["missing", "2026-11-05"])
                daily_alert.main(["repeat", "2026-11-05"])
            finally:
                daily_alert.RAW_DIR = old
            self.assertEqual(sorted(p.name for p in Path(out).iterdir()), ["missing-0.json", "repeat-0.json"])
            m = json.loads((Path(out) / "repeat-0.json").read_text(encoding="utf-8"))
        self.assertEqual(m["Subject"], "Observatorio: sin datos del recolector (2026-11-05)")


if __name__ == "__main__":
    unittest.main()
