#!/usr/bin/env python3
"""Write observatory/github-stats.json with the public GitHub figures of qtorb/rosmarops (GTM-61).

Reads four public resources with the token in GH_TOKEN (the workflow's own GITHUB_TOKEN). If any read does not
return 200, exits with an error and writes nothing. Standard library only.

    python3 observatory/github_stats.py [output]      # default: observatory/github-stats.json
    python3 observatory/github_stats.py --check FILE  # validate the shape of an existing file
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "observatory" / "github-stats.json"
API = "https://api.github.com"
REPO = "qtorb/rosmarops"
REPO_KEYS = ("stargazers_count", "subscribers_count", "forks_count", "open_issues_count")


def get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "rosmarops-web-github-stats",
    })
    token = os.environ.get("GH_TOKEN", "")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                sys.exit(f"{path}: HTTP {r.status}")
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code}")


def build(now=None):
    repo = get(f"/repos/{REPO}")
    pulls = get(f"/repos/{REPO}/pulls?state=open&per_page=100")
    releases = get(f"/repos/{REPO}/releases?per_page=100")
    latest = get(f"/repos/{REPO}/releases/latest")
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": {k: repo[k] for k in REPO_KEYS},
        "open_pulls": len(pulls),
        "releases": [
            {
                "tag_name": r["tag_name"],
                "published_at": r["published_at"],
                "draft": r["draft"],
                "assets": [{"name": a["name"], "download_count": a["download_count"]} for a in r["assets"]],
            }
            for r in releases
        ],
        "latest_tag": latest["tag_name"],
    }


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(d):
    """Errors for anything that is not exactly the GTM-61 shape."""
    errs = []

    def keys(obj, want, where):
        if not isinstance(obj, dict):
            errs.append(f"{where}: not an object")
            return False
        if set(obj) != set(want):
            errs.append(f"{where}: keys {sorted(obj)} != {sorted(want)}")
            return False
        return True

    if not keys(d, ("generated_at", "repo", "open_pulls", "releases", "latest_tag"), "(root)"):
        return errs
    try:
        datetime.datetime.strptime(d["generated_at"], "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        errs.append("generated_at: not UTC RFC 3339 (YYYY-MM-DDTHH:MM:SSZ)")
    if keys(d["repo"], REPO_KEYS, "repo"):
        errs += [f"repo.{k}: not an integer" for k in REPO_KEYS if not _is_int(d["repo"][k])]
    if not _is_int(d["open_pulls"]):
        errs.append("open_pulls: not an integer")
    if not isinstance(d["latest_tag"], str) or not d["latest_tag"]:
        errs.append("latest_tag: not a non-empty string")
    if not isinstance(d["releases"], list):
        errs.append("releases: not a list")
        return errs
    for i, r in enumerate(d["releases"]):
        w = f"releases[{i}]"
        if not keys(r, ("tag_name", "published_at", "draft", "assets"), w):
            continue
        if not isinstance(r["tag_name"], str):
            errs.append(f"{w}.tag_name: not a string")
        if not isinstance(r["published_at"], str):
            errs.append(f"{w}.published_at: not a string")
        if not isinstance(r["draft"], bool):
            errs.append(f"{w}.draft: not a boolean")
        if not isinstance(r["assets"], list):
            errs.append(f"{w}.assets: not a list")
            continue
        for j, a in enumerate(r["assets"]):
            if keys(a, ("name", "download_count"), f"{w}.assets[{j}]"):
                if not isinstance(a["name"], str):
                    errs.append(f"{w}.assets[{j}].name: not a string")
                if not _is_int(a["download_count"]):
                    errs.append(f"{w}.assets[{j}].download_count: not an integer")
    return errs


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        errs = check(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
        print("\n".join(errs) or "ok")
        sys.exit(1 if errs else 0)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    d = build()
    errs = check(d)
    if errs:
        sys.exit("\n".join(errs))
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{out}: {len(d['releases'])} releases, latest {d['latest_tag']}")


if __name__ == "__main__":
    main()
