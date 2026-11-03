#!/usr/bin/env python3
"""Daily collector of the Observatory's fixed sources, without a model (GTM-75).

Reads every source in observatory/sources.json and writes observatory/raw/<date>.json (date in Madrid) with, per
source, whether it opened, its latest version and date, the entries newer than L and the new advisory ids that match
scope_terms. L is the date of the latest raw file before today, or seven days ago if there is none; "newer than L"
means dated L or later, as the annex says «desde L», so an entry published on L after the previous run is not lost.

Standard library only. It never runs anything it reads: pages are parsed as text, and third-party repositories are
only queried with git ls-remote and with tag or branch fetches using --filter=blob:none into an empty temporary
repository, never checked out.

    python3 observatory/collect.py                 # write observatory/raw/<today>.json
    python3 observatory/collect.py --out FILE      # write elsewhere (the output dir still sets L)
"""

import csv
import datetime
import fnmatch
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "observatory" / "sources.json"
RAW_DIR = ROOT / "observatory" / "raw"
UA = "RosmarOps-Observatory/1 (+https://rosmarops.com)"
MADRID = ZoneInfo("Europe/Madrid")
RETRIES = 2
PAUSE = 10
TEXT_MAX = 600
TIMEOUT = 60
DISCARD = re.compile(r"alpha|beta|rc|nightly|preview|canary|dev", re.I)
ADVISORY = re.compile(r"\b(?:MAL-\d{4}-\d+|GHSA(?:-[0-9a-z]{4}){3}|CVE-\d{4}-\d{4,})\b")

sleep = time.sleep  # replaced in tests
TODAY = None  # the collection day (Madrid), set by collect(); entries dated after it are ignored


class ReadError(Exception):
    pass


# --------------------------------------------------------------------------------------------- reading, with retries

def retry(what, fn):
    """Run fn; on failure retry RETRIES times with PAUSE seconds between attempts."""
    last = None
    for attempt in range(RETRIES + 1):
        if attempt:
            sleep(PAUSE)
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - any failure of a read is retried, then reported
            last = e
    raise ReadError(f"{what}: {last}")


def http_get(url):
    """Body of url as text (UTF-8, errors replaced). Raises on anything but 200."""
    def once():
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.status != 200:
                raise ReadError(f"HTTP {r.status}")
            return r.read().decode("utf-8", errors="replace")
    return retry(url, once)


GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
GIT_SAFE = ["-c", "core.hooksPath=" + os.devnull, "-c", "protocol.file.allow=never", "-c", f"http.userAgent={UA}"]


def run_git(args, cwd=None):
    env = dict(os.environ, **GIT_ENV)

    def once():
        p = subprocess.run(["git", *GIT_SAFE, *args], cwd=cwd, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        if p.returncode != 0:
            raise ReadError((p.stderr or p.stdout).strip()[-300:])
        return p.stdout
    return retry("git " + " ".join(a for a in args if not a.startswith("refs/tags/")), once)


def ls_remote_tags(url):
    out = run_git(["ls-remote", "--tags", "--refs", url])
    return [line.split("refs/tags/", 1)[1] for line in out.splitlines() if "refs/tags/" in line]


def tag_info(url, tag):
    """(date YYYY-MM-DD, annotated tag text or '') of one tag, fetched alone into an empty repository."""
    with tempfile.TemporaryDirectory() as d:
        run_git(["init", "-q", d])
        ref = f"refs/tags/{tag}"
        run_git(["fetch", "-q", "--depth=1", "--filter=blob:none", "--no-tags", url, f"{ref}:{ref}"], cwd=d)
        out = run_git(["for-each-ref", ref, "--format=%(creatordate:short)%00%(objecttype)%00%(contents)"], cwd=d)
    date, objtype, contents = (out.split("\0", 2) + ["", ""])[:3]
    text = contents.strip() if objtype.strip() == "tag" else ""
    text = re.sub(r"-----BEGIN (?:PGP|SSH) SIGNATURE-----.*", "", text, flags=re.S).strip()
    return date.strip(), text


# ------------------------------------------------------------------------------------------------ text from pages

BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "section", "article", "header", "ul", "ol",
         "pre", "dt", "dd", "summary", "details", "table", "time"}
SKIP = {"script", "style", "noscript", "svg", "template", "head"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
            return
        if tag in BLOCK:
            self.out.append("\n")
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4"):
            self.out.append("#" * int(tag[1]) + " ")
        if tag == "time":
            dt = dict(attrs).get("datetime") or ""
            if re.match(r"\d{4}-\d{2}-\d{2}", dt):
                self.out.append(dt[:10] + "\n")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def page_lines(body):
    """Text lines of an HTML page, or of a Markdown/plain file as it is."""
    if re.search(r"<html|<body|<div|<p[ >]", body[:5000], re.I):
        p = _Text()
        p.feed(body)
        body = "".join(p.out)
    body = html.unescape(body) if "&#" in body or "&amp;" in body else body
    lines = []
    for line in body.splitlines():
        line = re.sub(r"[ \t\r\f\v​ ]+", " ", line).strip()
        if line:
            lines.append(line)
    return lines


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MON = r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
DATE_RES = [
    (re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)"), lambda m: (m[1], m[2], m[3])),
    (re.compile(_MON + r"\s*(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)"), lambda m: (m[3], MONTHS[m[1].lower()], m[2])),
    (re.compile(r"(?<!\d)(\d{1,2})\s+" + _MON + r",?\s+(20\d\d)"), lambda m: (m[3], MONTHS[m[2].lower()], m[1])),
]
VERSION_RE = re.compile(r"(?<![\w.])v?\d+(?:\.\d+){1,3}(?![\d]|\.\d)")
CALVER_HEADING = re.compile(r"#+\s*(v?(20\d\d)\.(\d{1,2})\.(\d{1,2}))")
ANCHOR_WORDS = re.compile(r"release date|released|announcements|latest|stable|changelog|version|[#·:|—–\-,()]", re.I)


def find_date(line):
    for rx, parts in DATE_RES:
        m = rx.search(line)
        if m:
            try:
                y, mo, d = parts(m)
                return datetime.date(int(y), int(mo), int(d)).isoformat(), m
            except ValueError:
                continue
    return None, None


def _short_version(line):
    """Version of a short line that is essentially a version (heading or label), else None."""
    if len(line) > 60:
        return None
    m = VERSION_RE.search(line)
    if not m:
        return None
    rest = ANCHOR_WORDS.sub("", line.replace(m.group(0), "")).strip()
    return m.group(0) if len(rest) <= 40 else None


def entries(lines):
    """Dated entries of a changelog: [{'date','version','title','text'}], one per anchor line.

    An anchor is a line made of a date plus at most a version and a few label words. The version is read from the
    anchor itself or from a short version-only line just before or after it; the text runs to the next anchor."""
    anchors = []
    for i, line in enumerate(lines):
        if len(line) > 90:
            continue
        cal = CALVER_HEADING.fullmatch(line)
        if cal:  # a heading that is only a calendar version (Cursor CLI "## v2026.10.22") dates itself
            try:
                anchors.append((i, datetime.date(*map(int, cal.group(2, 3, 4))).isoformat(), cal.group(1)))
            except ValueError:
                pass
            continue
        date, m = find_date(line)
        if not date:
            continue
        rest = line[:m.start()] + line[m.end():]
        v = VERSION_RE.search(rest)
        rest_wo = ANCHOR_WORDS.sub("", rest.replace(v.group(0), "") if v else rest).strip()
        if len(rest_wo) > 30:
            continue
        anchors.append((i, date, v.group(0) if v else None))
    out = []
    for k, (i, date, version) in enumerate(anchors):
        end = anchors[k + 1][0] if k + 1 < len(anchors) else min(len(lines), i + 200)
        if version is None:
            for j in (i - 1, i - 2, i + 1, i + 2):
                if 0 <= j < len(lines) and (k == 0 or j > anchors[k - 1][0]) and j < end:
                    version = _short_version(lines[j])
                    if version:
                        break
        body = [ln for ln in lines[i + 1:end] if ln != version]
        if k + 1 < len(anchors):  # drop the next entry's version line, if it sits just before its anchor
            nv = anchors[k + 1][2]
            while body and (_short_version(body[-1]) and (nv is None or _short_version(body[-1]) != nv) and len(body[-1]) < 25):
                body.pop()
        title = body[0].lstrip("# ").strip() if body else ""
        out.append({"date": date, "version": version, "title": title, "text": " ".join(body)})
    out = [e for e in out if e["text"]]  # date lists (tables of contents, filters) carry no text
    best = {}
    for e in out:  # pages that render twice, or list dates in a table of contents: keep the fullest text
        key = (e["date"], e["version"], e["title"][:60] if e["version"] is None else "")
        if key not in best or len(e["text"]) > len(best[key]["text"]):
            best[key] = e
    return sorted(best.values(), key=lambda e: e["date"], reverse=True)


def trim(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= TEXT_MAX else text[:TEXT_MAX - 1].rstrip() + "…"


def section_for(lines, version):
    """Lines of the section of a changelog (Markdown or page text) that names `version`, or None."""
    num = re.sub(r"^[A-Za-z_-]*?v?(?=\d)", "", version)
    rx = re.compile(r"(?<![\w.])v?" + re.escape(num) + r"(?![\w]|\.\d)")
    for i, line in enumerate(lines):
        if len(line) <= 200 and rx.search(line) and (line.startswith("#") or line.startswith("- [") or _short_version(line)
                                                     or find_date(line)[0]):
            body = []
            for nxt in lines[i + 1:i + 300]:
                if (nxt.startswith("#") and len(nxt) <= 120 and VERSION_RE.search(nxt)
                        and not rx.search(nxt) and nxt.count("#") <= max(1, line.count("#") or 2)):
                    break
                if nxt.startswith("- [") and VERSION_RE.search(nxt) and line.startswith("- ["):
                    break
                body.append(nxt)
            return line, body
    return None


# ------------------------------------------------------------------------------------------------------ tag helpers

def tag_matcher(pattern, ignore):
    if pattern is None:
        rx = None
    elif pattern == "N.N.N":
        rx = re.compile(r"^\d+\.\d+\.\d+$")
    elif pattern.endswith("*"):
        rx = re.compile("^" + re.escape(pattern[:-1]) + r"\d")
    else:
        rx = re.compile("^" + re.escape(pattern) + "$")

    def ok(tag):
        if any(fnmatch.fnmatchcase(tag, g) for g in ignore or []):
            return False
        if DISCARD.search(tag):
            return False
        return rx is None or bool(rx.search(tag))
    return ok


def version_key(s):
    """Close to GNU sort -V: digit runs compare as numbers, other runs as text."""
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.findall(r"\d+|\D+", s)]


def sorted_tags(url, pattern, ignore=None):
    ok = tag_matcher(pattern, ignore)
    return sorted((t for t in ls_remote_tags(url) if ok(t)), key=version_key, reverse=True)


# ------------------------------------------------------------------------------------------------- per method

def today():
    return TODAY or datetime.datetime.now(MADRID).date().isoformat()


def blank(src, read_with):
    return {"id": src["id"], "opened": False, "reason": None, "latest": None, "latest_date": None, "new": [],
            "ids": [], "read_with": read_with}


def scope_match(text, terms):
    t = (text or "").lower()
    return any(term in t for term in terms)


def read_changelog_web(src, since, terms):
    r = src["read"]
    res = blank(src, "curl")
    try:
        all_entries = []
        for url in r["urls"]:
            all_entries += entries(page_lines(http_get(url)))
        all_entries.sort(key=lambda e: e["date"], reverse=True)
    except ReadError as e:
        fb = r.get("fallback")
        if not fb:
            res["reason"] = str(e)
            return res
        res = read_tags(src, fb, since, terms)
        res["reason"] = (res["reason"] + "; " if res["reason"] else "") + "changelog page failed, read from git tags"
        return res
    all_entries = [e for e in all_entries if e["date"] <= today()]
    only = r.get("only_entries_with")
    if only:
        all_entries = [e for e in all_entries if only.lower() in (e["title"] + " " + e["text"]).lower()]
    if not all_entries and not only:
        res["reason"] = "no dated entries found in the page"
        return res
    res["opened"] = True
    if all_entries:
        top = max(e["date"] for e in all_entries)
        res["latest_date"] = top
        res["latest"] = next((e["version"] for e in all_entries if e["date"] == top and e["version"]), None)
    res["new"] = [{"date": e["date"], "version": e["version"], "text": trim(e["text"])}
                  for e in all_entries if e["date"] >= since]
    res["ids"] = sorted({i for e in all_entries if e["date"] >= since for i in ADVISORY.findall(e["text"])})
    return res


def notes_for(version, tag_text, notes):
    """Notes of one version following the notes rule: raw CHANGELOG, then web changelog, then tag text."""
    for n in notes:
        if n == "tag":
            if tag_text:
                return tag_text
            continue
        kind, url = next(iter(n.items()))
        try:
            lines = page_lines(http_get(url))
        except ReadError:
            continue
        if kind == "web":
            num = re.sub(r"^[A-Za-z_-]*?v?(?=\d)", "", version)
            rx = re.compile(r"(?<![\w.])v?" + re.escape(num) + r"(?![\w]|\.\d)")
            for e in entries(lines):
                if (e["version"] and rx.search(e["version"])) or rx.search(e["title"]):
                    return e["text"]
            continue
        sec = section_for(lines, version)
        if not sec:
            continue
        head, body = sec
        link = re.search(r"\]\(([^)\s]+\.md)\)", head)
        if link and not body_has_text(body) and not link.group(1).startswith(("http:", "https:", "/")):
            try:
                sub = http_get(url.rsplit("/", 1)[0] + "/" + link.group(1).lstrip("./"))
                return " ".join(page_lines(sub)[1:])
            except ReadError:
                continue
        if body_has_text(body):
            return " ".join(body)
    return ""


def body_has_text(body):
    return any(not (ln.startswith("- [") and "](" in ln) for ln in body)


def read_tags(src, r, since, terms):
    res = blank(src, "git")
    try:
        tags = sorted_tags(r["git"], r.get("tags"), r.get("ignore"))
    except ReadError as e:
        res["reason"] = str(e)
        return res
    if not tags:
        res["reason"] = "no tags match the pattern"
        return res
    missing = []
    try:
        for n, tag in enumerate(tags[:10]):
            date, text = tag_info(r["git"], tag)
            if n == 0:
                res["latest"], res["latest_date"] = tag, date
            if date < since:
                break
            notes = notes_for(tag, text, r.get("notes", []))
            if notes:
                res["new"].append({"date": date, "version": tag, "text": trim(notes)})
            else:
                res["new"].append({"date": date, "version": tag,
                                   "text": "notes not available" if r.get("notes") else ""})
                if r.get("notes"):
                    missing.append(tag)
        also = r.get("also")
        if also:  # a second repository noted alongside (F25: AutoGen); its latest tag goes in "new" when it is new
            atags = sorted_tags(also["git"], also.get("tags"), also.get("ignore"))
            if atags:
                adate, atext = tag_info(also["git"], atags[0])
                if adate >= since:
                    name = also["git"].rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
                    res["new"].append({"date": adate, "version": f"{name} {atags[0]}", "text": trim(atext)})
    except ReadError as e:
        res["reason"] = str(e)
        return res
    res["ids"] = sorted({i for e in res["new"] for i in ADVISORY.findall(e["text"])})
    if missing and not src.get("fragile"):
        res["reason"] = "new version without notes: " + ", ".join(missing)
        return res
    res["opened"] = True  # a fragile source opens with version and date; its entries say "notes not available"
    return res


def read_git_tags(src, since, terms):
    return read_tags(src, src["read"], since, terms)


def package_names(rec):
    return [a.get("package", {}).get("name", "") for a in rec.get("affected", []) if isinstance(a, dict)]


def read_ossf(src, since, terms):
    r = src["read"]
    res = blank(src, "git")
    try:
        found = ossf_read(r["git"], r.get("branch", "main"), since, r["paths"])
    except ReadError as e:
        res["reason"] = str(e)
        return res
    res["opened"] = True
    latest = ""
    for path, rec in found:
        pub = (rec.get("published") or "")[:10]
        latest = max(latest, pub)
        if pub >= since and any(scope_match(n, terms) for n in package_names(rec)):
            rid = rec.get("id") or Path(path).stem
            res["ids"].append(rid)
            res["new"].append({"date": pub, "version": None,
                               "text": trim(f"{rid} {', '.join(package_names(rec))}: {rec.get('summary') or rec.get('details') or ''}")})
    res["latest_date"] = latest or None
    res["ids"] = sorted(set(res["ids"]))
    return res


def ossf_read(url, branch, since, globs):
    """[(path, parsed record)] for files matching globs added or modified on branch since `since`.

    Fetches the branch history from the day before `since` with --filter=blob:none, lists the files each commit added
    or modified (the shallow boundary commit is left out: its diff against a missing parent would list every file),
    then fetches only the blobs of those files, by id and in batches, and reads them with git cat-file."""
    before = (datetime.date.fromisoformat(since) - datetime.timedelta(days=1)).isoformat()
    ref = f"refs/remotes/origin/{branch}"
    with tempfile.TemporaryDirectory() as d:
        run_git(["init", "-q", d])
        run_git(["fetch", "-q", "--filter=blob:none", f"--shallow-since={before}", "--no-tags", url,
                 f"refs/heads/{branch}:{ref}"], cwd=d)
        shallow = Path(d, ".git", "shallow")
        boundary = shallow.read_text().split() if shallow.exists() else []
        log = run_git(["log", "--format=", "--raw", "--no-abbrev", "--diff-filter=AM", ref, "--not", *boundary], cwd=d)
        blobs = {}
        for line in log.splitlines():  # ":000000 100644 <old> <new> A\tpath"; the newest change of a path comes first
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) >= 4 and path not in blobs and any(fnmatch.fnmatchcase(path, g) for g in globs):
                blobs[path] = parts[3]
        oids = list(dict.fromkeys(blobs.values()))
        for i in range(0, len(oids), 500):
            run_git(["-c", "fetch.negotiationAlgorithm=noop", "fetch", "-q", "--no-tags", "--no-write-fetch-head",
                     "--filter=blob:none", url, *oids[i:i + 500]], cwd=d)
        found = []
        for path, oid in sorted(blobs.items()):
            try:
                found.append((path, json.loads(run_git(["cat-file", "blob", oid], cwd=d))))
            except (ReadError, ValueError):
                continue
        return found


def read_osv(src, since, terms):
    r = src["read"]
    res = blank(src, "curl")
    try:
        ids = []
        for url in r["urls"]:
            for row in csv.reader(io.StringIO(http_get(url))):
                if len(row) >= 2 and row[0][:10] >= since:
                    ids.append(row[1])
        latest = ""
        with ThreadPoolExecutor(max_workers=8) as pool:  # a few hundred records a day: read them eight at a time
            recs = list(pool.map(lambda rid: (rid, json.loads(http_get(r["record_url"].replace("<id>", rid)))),
                                 dict.fromkeys(ids)))
        for rid, rec in recs:
            pub = (rec.get("published") or "")[:10]
            latest = max(latest, pub)
            if pub >= since and any(scope_match(n, terms) for n in package_names(rec)):
                res["ids"].append(rid)
                res["new"].append({"date": pub, "version": None,
                                   "text": trim(f"{rid} {', '.join(package_names(rec))}: {rec.get('summary') or rec.get('details') or ''}")})
    except (ReadError, ValueError) as e:
        res["reason"] = str(e)
        return res
    res["opened"] = True
    res["latest_date"] = latest or None
    res["ids"] = sorted(set(res["ids"]))
    return res


def read_nvd(src, since, terms):
    r = src["read"]
    res = blank(src, "curl")
    seen = {}
    try:
        for n, term in enumerate(r["terms"]):
            if n:
                sleep(r.get("pause_seconds", 7))
            url = (r["url"].replace("<term>", urllib.request.quote(term)).replace("<L>", since)
                   .replace("<today>", today()))
            for v in json.loads(http_get(url)).get("vulnerabilities", []):
                cve = v.get("cve", {})
                desc = next((d.get("value", "") for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
                seen.setdefault(cve.get("id"), (cve.get("published", "")[:10], desc, term))
    except (ReadError, ValueError) as e:
        res["reason"] = str(e)
        return res
    res["opened"] = True
    for cid, (pub, desc, term) in sorted(seen.items(), key=lambda kv: kv[1][0], reverse=True):
        if cid and pub >= since and scope_match(desc, terms):
            res["ids"].append(cid)
            res["new"].append({"date": pub, "version": None, "text": trim(f"{cid} [{term}]: {desc}")})
    res["latest_date"] = max((p for p, _, _ in seen.values()), default=None) or None
    res["ids"] = sorted(set(res["ids"]))
    return res


def kev_match(v, r):
    vendor, product = v.get("vendorProject", ""), v.get("product", "")
    if vendor in r["vendors"]:
        return True
    if any(p.lower() in product.lower() for p in r.get("vendor_products", {}).get(vendor, [])):
        return True
    return any(re.search(r"\b" + re.escape(p) + r"\b", product) for p in r.get("products", []))


def read_kev(src, since, terms):
    r = src["read"]
    res = blank(src, "curl")
    try:
        k = json.loads(http_get(r["url"]))
    except (ReadError, ValueError) as e:
        res["reason"] = str(e)
        return res
    res["opened"] = True
    res["latest"] = k.get("catalogVersion")
    res["latest_date"] = (k.get("dateReleased") or "")[:10] or None
    for v in k.get("vulnerabilities", []):
        if v.get("dateAdded", "") >= since and kev_match(v, r):
            res["ids"].append(v["cveID"])
            res["new"].append({"date": v["dateAdded"], "version": None,
                               "text": trim(f"{v['cveID']} {v.get('vendorProject')} {v.get('product')}: "
                                            f"{v.get('vulnerabilityName', '')}. {v.get('shortDescription', '')}")})
    res["ids"] = sorted(set(res["ids"]))
    return res


METHODS = {"changelog-web": read_changelog_web, "git-tags": read_git_tags, "ossf": read_ossf, "osv-csv": read_osv,
           "nvd": read_nvd, "kev": read_kev}


def collect_source(src, since, terms):
    try:
        res = METHODS[src["method"]](src, since, terms)
    except Exception as e:  # noqa: BLE001 - an unexpected failure closes one source, never the day
        res = blank(src, "git" if src["method"] in ("git-tags", "ossf") else "curl")
        res["reason"] = f"collector error: {type(e).__name__}: {e}"[:300]
    if res["reason"]:
        res["reason"] = res["reason"][:300]
    return res


# ------------------------------------------------------------------------------------------------------------- run

def last_raw_date(raw_dir, day):
    """L: the date of the latest raw file before `day`, or seven days before `day` if there is none."""
    dates = sorted(p.stem for p in Path(raw_dir).glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)
                   and p.stem < day)
    return dates[-1] if dates else (datetime.date.fromisoformat(day) - datetime.timedelta(days=7)).isoformat()


def collect(sources_file=SOURCES, raw_dir=RAW_DIR, now=None, progress=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    global TODAY
    TODAY = now.astimezone(MADRID).date().isoformat()
    cfg = json.loads(Path(sources_file).read_text(encoding="utf-8"))
    terms = [t.lower() for t in cfg["scope_terms"]]
    since = last_raw_date(raw_dir, TODAY)
    out = []
    for s in cfg["sources"]:
        t0 = time.monotonic()
        out.append(collect_source(s, since, terms))
        if progress:
            progress(f"{s['id']}: {time.monotonic() - t0:.0f} s")
    return {
        "date": TODAY,
        "collected_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": out,
        "opened": sum(1 for s in out if s["opened"]),
        "total": len(out),
    }


def main():
    args = sys.argv[1:]
    out = None
    if args[:1] == ["--out"] and len(args) == 2:
        out = Path(args[1])
    elif args:
        sys.exit(__doc__)
    d = collect(progress=lambda m: print(m, file=sys.stderr, flush=True))
    out = out or RAW_DIR / f"{d['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for s in d["sources"]:
        print(f"{s['id']:>4} {'open' if s['opened'] else 'NOT ':4} {s['latest'] or '-'} {s['latest_date'] or '-'} "
              f"new={len(s['new'])} ids={len(s['ids'])} {s['reason'] or ''}")
    print(f"{out}: {d['opened']}/{d['total']} opened")


if __name__ == "__main__":
    main()
