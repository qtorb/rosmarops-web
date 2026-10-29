#!/usr/bin/env python3
"""RosmarOps Observatory: mechanical checks for a daily synopsis file (GTM-23).

Usage:  python3 observatory/daily_check.py observatory/daily/2026-10-30.json [...]

Checks the parts of the publication rules (GTM-22 §1) that a machine can check:
the JSON schema, word limits, forbidden words, the same numbers, versions and
identifiers in EN/ES/CA, no links or markup in the texts, allowed source hosts,
no tracking parameters. Prints one line per error and exits 1 if there is any.

Standard library only, except `jsonschema` for the schema step (installed in CI).
"""

import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "observatory" / "schema" / "daily.v1.schema.json"

MAX_WORDS = {"en": 30, "es": 40, "ca": 40}
FORBIDDEN = [
    "seguro", "segura", "protege", "garantiza", "safe", "secure", "protect", "protects",
    "guarantee", "guarantees", "segur", "protegeix", "garanteix", "debes", "recomendamos",
    "should", "recommend", "has de", "recomanem",
    "grave", "critico", "critica", "critical", "critic", "peligroso", "dangerous", "perillos",
    "importante", "important",
]
FORBIDDEN_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in FORBIDDEN) + r")\b")
SEVERITY_RE = re.compile(r"\b(severidad|severity|severitat)\b.*?\b(segun|according to|segons)\b")
ALLOWED_HOSTS = [
    "anthropic.com", "claude.com", "cursor.com", "openai.com", "github.com", "github.blog",
    "antigravity.google", "nousresearch.com", "cline.bot", "continue.dev", "osv.dev",
    "nvd.nist.gov", "npmjs.com", "pypi.org",
]
ID_RE = re.compile(r"MAL-\d{4}-\d+|GHSA(?:-[23456789cfghjmpqrvwx]{4}){3}|CVE-\d{4}-\d{4,}")
VERSION_RE = re.compile(r"\d+(?:\.\d+)+")
NUMBER_RE = re.compile(r"\d+")
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def fold(s):
    """Lower case, accents removed, so «Crítico» and «critico» match the same word."""
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def forbidden_words(text):
    t = fold(text)
    allowed = [m.span() for m in SEVERITY_RE.finditer(t)]
    hits = []
    for m in FORBIDDEN_RE.finditer(t):
        if not any(a <= m.start() and m.end() <= b for a, b in allowed):
            hits.append(m.group(1))
    return hits


def tokens(text):
    """Identifiers, versions and plain numbers in a text, as a set."""
    out = set(ID_RE.findall(text))
    rest = ID_RE.sub(" ", text)
    out |= {"v:" + v for v in VERSION_RE.findall(rest)}
    rest = VERSION_RE.sub(" ", rest)
    out |= {"n:" + n for n in NUMBER_RE.findall(rest)}
    return out


def host_allowed(url):
    host = (urlsplit(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def url_errors(url, where):
    errs = []
    parts = urlsplit(url)
    if parts.scheme != "https":
        errs.append(f"{where}: not https")
    if not host_allowed(url):
        errs.append(f"{where}: host {parts.hostname!r} is not in the allowed list")
    q = parts.query.lower()
    if re.search(r"(^|&)utm_", q) or re.search(r"(^|&)ref=", q):
        errs.append(f"{where}: tracking parameter in the query")
    if url.endswith("#"):
        errs.append(f"{where}: empty fragment")
    return errs


def schema_errors(data):
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        return ["jsonschema is not installed: pip install 'jsonschema[format-nongpl]'"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    return [f"schema: {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in sorted(v.iter_errors(data), key=lambda e: list(e.path))]


def check(path):
    path = Path(path)
    errs = []
    if not NAME_RE.match(path.name):
        errs.append("file name must be AAAA-MM-DD.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"cannot read JSON: {e}"]
    errs += schema_errors(data)
    if errs and not isinstance(data, dict):
        return errs
    if data.get("date") != path.stem:
        errs.append(f"date {data.get('date')!r} does not match the file name")
    for i, it in enumerate(data.get("items") or []):
        if not isinstance(it, dict):
            continue
        text = it.get("text") or {}
        sets = {}
        for lang, limit in MAX_WORDS.items():
            s = text.get(lang)
            if not isinstance(s, str):
                continue
            where = f"items/{i}/text/{lang}"
            n = len(s.split())
            if n > limit:
                errs.append(f"{where}: {n} words (max {limit})")
            for w in forbidden_words(s):
                errs.append(f"{where}: forbidden word {w!r}")
            low = s.lower()
            if "http" in low or "www." in low or "`" in s or "<" in s:
                errs.append(f"{where}: link, code or markup in the text")
            sets[lang] = tokens(s)
        if len(sets) == 3 and not (sets["en"] == sets["es"] == sets["ca"]):
            errs.append(f"items/{i}/text: numbers, versions or identifiers differ between languages: "
                        + "; ".join(f"{l}={sorted(v)}" for l, v in sets.items()))
        if isinstance(it.get("source_url"), str):
            errs += url_errors(it["source_url"], f"items/{i}/source_url")
    for i, c in enumerate(data.get("checked") or []):
        if isinstance(c, dict) and isinstance(c.get("url"), str):
            errs += url_errors(c["url"], f"checked/{i}/url")
    if data.get("status") == "no_changes" and any(isinstance(h, dict) and h.get("rule") == 10 for h in data.get("held") or []):
        errs.append("status no_changes but the review is incomplete (held item with rule 10)")
    return errs


def main(argv):
    if not argv:
        sys.exit(__doc__)
    bad = 0
    for f in argv:
        errs = check(f)
        for e in errs:
            print(f"{f}: {e}")
        print(("FAIL " if errs else "ok   ") + f)
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
