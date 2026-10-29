"""Tests for observatory/daily_check.py: one valid fixture and one broken variant per check (GTM-23 §2).

Run from the repository root:  python3 -m unittest observatory/tests/test_daily_check.py
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import daily_check  # noqa: E402

VALID = ROOT / "observatory" / "tests" / "daily" / "2026-01-15.json"


def run(data, name="2026-01-15.json"):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / name
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return daily_check.check(p)


class DailyCheck(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(VALID.read_text(encoding="utf-8"))

    def broken(self, mutate, expect, name="2026-01-15.json"):
        d = copy.deepcopy(self.d)
        mutate(d)
        errs = run(d, name)
        self.assertTrue(any(expect in e for e in errs), f"expected {expect!r} in {errs}")

    def test_valid(self):
        self.assertEqual(daily_check.check(VALID), [])

    def test_schema(self):
        self.broken(lambda d: d.update(status="maybe"), "schema:")

    def test_six_items(self):
        self.broken(lambda d: d.update(items=d["items"] * 3), "schema: items")

    def test_published_needs_items(self):
        self.broken(lambda d: d.update(items=[]), "schema:")

    def test_bad_identifier(self):
        self.broken(lambda d: d["items"][0].update(identifier="MAL-1"), "schema: items/0/identifier")

    def test_date_mismatch(self):
        self.broken(lambda d: None, "does not match the file name", name="2026-01-16.json")

    def test_file_name(self):
        self.broken(lambda d: None, "file name", name="daily.json")

    def test_words_en(self):
        self.broken(lambda d: d["items"][1]["text"].update(en=" ".join(["word"] * 31)), "words (max 30)")

    def test_words_es(self):
        self.broken(lambda d: d["items"][1]["text"].update(es=" ".join(["palabra"] * 41)), "words (max 40)")

    def test_forbidden_word(self):
        self.broken(lambda d: d["items"][1]["text"].update(en="Example Agent 2.4.0 is now secure, released 14 January 2026."), "forbidden word 'secure'")

    def test_forbidden_word_accents(self):
        self.broken(lambda d: d["items"][1]["text"].update(es="Fallo Crítico en Example Agent 2.4.0, 14 de enero de 2026."), "forbidden word 'critico'")

    def test_severity_quote_allowed(self):
        d = copy.deepcopy(self.d)
        d["items"][0]["text"] = {
            "en": "MAL-2026-1 in example-mcp-package 1.0.2, severity critical according to OSV, 14 January 2026.",
            "es": "MAL-2026-1 en example-mcp-package 1.0.2, severidad crítica según OSV, 14 de enero de 2026.",
            "ca": "MAL-2026-1 a example-mcp-package 1.0.2, severitat crítica segons OSV, 14 de gener de 2026.",
        }
        self.assertEqual(run(d), [])

    def test_tokens_differ(self):
        self.broken(lambda d: d["items"][1]["text"].update(ca="Example Agent 2.4.1, publicat el 14 de gener de 2026."), "differ between languages")

    def test_link_in_text(self):
        self.broken(lambda d: d["items"][1]["text"].update(en="See https://x 2.4.0 14 2026"), "link, code or markup")

    def test_markup_in_text(self):
        self.broken(lambda d: d["items"][1]["text"].update(en="<b>Example Agent</b> 2.4.0 14 2026"), "link, code or markup")

    def test_host_not_allowed(self):
        self.broken(lambda d: d["items"][1].update(source_url="https://blog.example.net/x"), "is not in the allowed list")

    def test_http(self):
        self.broken(lambda d: d["items"][1].update(source_url="http://github.com/example"), "schema: items/1/source_url")

    def test_tracking(self):
        self.broken(lambda d: d["items"][1].update(source_url="https://github.com/example?utm_source=x"), "tracking parameter")

    def test_empty_fragment(self):
        self.broken(lambda d: d["checked"][0].update(url="https://github.com/example#"), "empty fragment")

    def test_no_changes_but_incomplete(self):
        def m(d):
            d.update(status="no_changes", items=[])
            d["held"].append({"text_en": "", "source_url": "", "rule": 10, "reason": "osv.dev did not open"})
        self.broken(m, "review is incomplete")


if __name__ == "__main__":
    unittest.main()
