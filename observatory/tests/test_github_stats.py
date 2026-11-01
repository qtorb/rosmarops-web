"""Tests for observatory/github_stats.py: the shape of observatory/github-stats.json (GTM-61 §3).

Run from the repository root:  python3 -m unittest observatory/tests/test_github_stats.py
"""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "observatory"))
import github_stats  # noqa: E402

VALID = {
    "generated_at": "2026-11-01T06:10:00Z",
    "repo": {"stargazers_count": 3, "subscribers_count": 1, "forks_count": 0, "open_issues_count": 2},
    "open_pulls": 1,
    "releases": [
        {
            "tag_name": "v0.5.2",
            "published_at": "2026-10-29T17:52:58Z",
            "draft": False,
            "assets": [{"name": "rosmarops-windows-amd64.zip", "download_count": 7}],
        }
    ],
    "latest_tag": "v0.5.2",
}


class GithubStatsShape(unittest.TestCase):
    def broken(self, mutate, expect):
        d = copy.deepcopy(VALID)
        mutate(d)
        errs = github_stats.check(d)
        self.assertTrue(any(expect in e for e in errs), f"expected {expect!r} in {errs}")

    def test_valid(self):
        self.assertEqual(github_stats.check(VALID), [])

    def test_no_releases(self):
        d = copy.deepcopy(VALID)
        d["releases"] = []
        self.assertEqual(github_stats.check(d), [])

    def test_extra_root_key(self):
        self.broken(lambda d: d.update(extra=1), "(root): keys")

    def test_missing_root_key(self):
        self.broken(lambda d: d.pop("latest_tag"), "(root): keys")

    def test_extra_repo_key(self):
        self.broken(lambda d: d["repo"].update(watchers_count=1), "repo: keys")

    def test_repo_not_int(self):
        self.broken(lambda d: d["repo"].update(forks_count="0"), "repo.forks_count")

    def test_bool_is_not_int(self):
        self.broken(lambda d: d.update(open_pulls=True), "open_pulls")

    def test_generated_at_not_utc(self):
        self.broken(lambda d: d.update(generated_at="2026-11-01T07:10:00+01:00"), "generated_at")

    def test_release_extra_key(self):
        self.broken(lambda d: d["releases"][0].update(name="x"), "releases[0]: keys")

    def test_draft_not_bool(self):
        self.broken(lambda d: d["releases"][0].update(draft="false"), "releases[0].draft")

    def test_published_at_null(self):
        self.broken(lambda d: d["releases"][0].update(published_at=None), "releases[0].published_at")

    def test_asset_extra_key(self):
        self.broken(lambda d: d["releases"][0]["assets"][0].update(size=1), "releases[0].assets[0]: keys")

    def test_download_count_not_int(self):
        self.broken(lambda d: d["releases"][0]["assets"][0].update(download_count=1.0), "download_count")

    def test_latest_tag_empty(self):
        self.broken(lambda d: d.update(latest_tag=""), "latest_tag")

    def test_committed_file(self):
        f = ROOT / "observatory" / "github-stats.json"
        if not f.exists():
            self.skipTest("observatory/github-stats.json not generated yet")
        self.assertEqual(github_stats.check(json.loads(f.read_text(encoding="utf-8"))), [])


if __name__ == "__main__":
    unittest.main()
