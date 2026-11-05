"""GTM-90: the daily writer works from the collector's raw file. Run: python3 -m unittest observatory/tests/test_daily_raw.py"""

import copy
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import daily_check  # noqa: E402
import daily_raw  # noqa: E402

D = "2026-01-15"
NOW = datetime.datetime(2026, 1, 15, 7, 20, tzinfo=datetime.timezone.utc)
ITEMS = json.loads((ROOT / "observatory" / "tests" / "daily" / f"{D}.json").read_text(encoding="utf-8"))["items"][:1]
SOURCES = daily_raw.load_sources()


def raw(closed=()):
    srcs = []
    for s in SOURCES:
        shut = s["id"] in closed
        srcs.append({"id": s["id"], "opened": not shut, "reason": "HTTP 503" if shut else None,
                     "latest": None if shut else "1.0.0", "latest_date": None if shut else "2026-01-14",
                     "new": [], "ids": [], "read_with": "curl"})
    return {"date": D, "collected_at": "2026-01-15T05:30:00Z", "sources": srcs,
            "opened": len(srcs) - len(closed), "total": len(srcs)}


def check(data):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / f"{D}.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return daily_check.check(p)


class FromRaw(unittest.TestCase):
    def test_all_open_published_without_not_checked(self):
        d = daily_raw.build(D, raw(), SOURCES, copy.deepcopy(ITEMS), [], NOW)
        self.assertEqual(d["status"], "published")
        self.assertNotIn("not_checked", d)
        self.assertEqual(len(d["checked"]), len(SOURCES))
        self.assertEqual(d["checked"][0], {"name": "Claude Code", "url": SOURCES[0]["public_url"],
                                           "latest_seen": "1.0.0", "latest_date": "2026-01-14"})
        self.assertEqual(check(d), [])

    def test_all_open_no_items_no_changes(self):
        d = daily_raw.build(D, raw(), SOURCES, [], [], NOW)
        self.assertEqual(d["status"], "no_changes")
        self.assertEqual(check(d), [])

    def test_one_closed_incomplete_with_items(self):
        d = daily_raw.build(D, raw(closed=("F22",)), SOURCES, copy.deepcopy(ITEMS), [], NOW)
        self.assertEqual(d["status"], "incomplete")
        self.assertEqual(d["not_checked"], ["OpenClaw"])
        self.assertEqual(len(d["items"]), 1)
        self.assertNotIn("OpenClaw", [c["name"] for c in d["checked"]])
        self.assertEqual(check(d), [])

    def test_source_missing_from_raw_is_not_checked(self):
        r = raw()
        r["sources"] = [s for s in r["sources"] if s["id"] != "F5"]
        self.assertIn("Hermes Agent", daily_raw.coverage(r, SOURCES)[1])

    def test_no_raw(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(daily_raw.load_raw(D, d))
        d = daily_raw.no_raw(D, SOURCES, NOW)
        self.assertEqual((d["status"], d["items"], d["checked"]), ("incomplete", [], []))
        self.assertEqual(d["held"], [{"text_en": "", "source_url": "", "rule": 10, "reason": f"no raw for {D}"}])
        self.assertEqual(d["not_checked"], [s["name"] for s in SOURCES])
        self.assertEqual(check(d), [])

    def test_every_public_url_passes_the_host_check(self):
        for s in SOURCES:
            self.assertTrue(daily_check.host_allowed(s["public_url"]), s["id"])


class Idempotence(unittest.TestCase):
    def write(self, folder, data):
        (Path(folder) / f"{D}.json").write_text(json.dumps(data), encoding="utf-8")

    def test_absent_may_write(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(daily_raw.may_write(D, d))

    def test_redo_only_placeholders(self):
        for reason, ok in ((f"no raw for {D}", True), (f"no summary for {D}", True),
                           ("no raw for 2026-01-14", False), ("fuera por tope", False)):
            with tempfile.TemporaryDirectory() as d:
                self.write(d, {"held": [{"text_en": "", "source_url": "", "rule": 10, "reason": reason}]})
                self.assertEqual(daily_raw.may_write(D, d), ok, reason)

    def test_rule_must_be_10(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, {"held": [{"text_en": "", "source_url": "", "rule": 9, "reason": f"no raw for {D}"}]})
            self.assertFalse(daily_raw.may_write(D, d))

    def test_published_day_is_left_alone(self):
        with tempfile.TemporaryDirectory() as d:
            self.write(d, daily_raw.build(D, raw(closed=("F22",)), SOURCES, copy.deepcopy(ITEMS), [], NOW))
            self.assertFalse(daily_raw.may_write(D, d))


class RawSchema(unittest.TestCase):
    """GTM-90 §3: raw.v1 already requires id, opened and reason (a string when opened is false)."""

    def errors(self, data):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema is not installed")
        schema = json.loads((ROOT / "observatory" / "schema" / "raw.v1.schema.json").read_text(encoding="utf-8"))
        return list(Draft202012Validator(schema).iter_errors(data))

    def test_valid(self):
        self.assertEqual(self.errors(raw(closed=("F22",))), [])

    def test_each_source_needs_id_opened_reason(self):
        for key in ("id", "opened", "reason"):
            r = raw()
            del r["sources"][0][key]
            self.assertTrue(self.errors(r), key)

    def test_closed_needs_reason(self):
        r = raw(closed=("F22",))
        next(s for s in r["sources"] if s["id"] == "F22")["reason"] = None
        self.assertTrue(self.errors(r))


if __name__ == "__main__":
    unittest.main()
