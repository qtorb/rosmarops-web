#!/usr/bin/env python3
"""The daily writer's view of the collector's raw file (GTM-90).

  python3 observatory/daily_raw.py skeleton YYYY-MM-DD    print checked, not_checked and base status from raw/D.json,
                                                          or the whole no-raw D.json when raw/D.json does not exist
  python3 observatory/daily_raw.py may-write YYYY-MM-DD   exit 0 if daily/D.json may be written (absent) or redone,
                                                          1 if it exists and must not be touched

Rules in observatory/rules/daily.md, section «Fuente de datos (GTM-90)». Standard library only.
"""

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "observatory" / "sources.json"
RAW_DIR = ROOT / "observatory" / "raw"
DAILY_DIR = ROOT / "observatory" / "daily"
REDO_REASONS = ("no raw for {d}", "no summary for {d}")


def load_sources(path=SOURCES):
    return json.loads(Path(path).read_text(encoding="utf-8"))["sources"]


def load_raw(date, raw_dir=RAW_DIR):
    """The raw file for `date`, or None when it does not exist."""
    p = Path(raw_dir) / f"{date}.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def coverage(raw, sources):
    """(checked, not_checked): opened sources with name and public_url from sources.json; closed ones by name.
    page-watch sources (GTM-160) are left out of both.
    A source in sources.json that the raw file does not carry counts as not opened."""
    by_id = {s["id"]: s for s in raw["sources"]}
    checked, not_checked = [], []
    for src in sources:
        if src["method"] == "page-watch":  # GTM-160: watch-only sources are not part of the public review
            continue
        r = by_id.get(src["id"])
        if r and r["opened"]:
            checked.append({"name": src["name"], "url": src["public_url"],
                            "latest_seen": (r["latest"] or "")[:40], "latest_date": r["latest_date"]})
        else:
            not_checked.append(src["name"])
    return checked, not_checked


def status_for(items, not_checked):
    if not_checked:
        return "incomplete"
    return "published" if items else "no_changes"


def build(date, raw, sources, items, held, now=None):
    """A D.json from the raw file plus the items and held the writer decided under R1-R13."""
    checked, not_checked = coverage(raw, sources)
    d = {"date": date, "reviewed_at": stamp(now), "status": status_for(items, not_checked), "items": items,
         "checked": checked}
    if not_checked:
        d["not_checked"] = not_checked
    d["held"] = held
    d["summary_ref"] = f"docs/observatorio/{date}.md"
    return d


def no_raw(date, sources, now=None):
    return {"date": date, "reviewed_at": stamp(now), "status": "incomplete", "items": [], "checked": [],
            "not_checked": [s["name"] for s in sources if s["method"] != "page-watch"],
            "held": [{"text_en": "", "source_url": "", "rule": 10, "reason": f"no raw for {date}"}],
            "summary_ref": f"docs/observatorio/{date}.md"}


def may_redo(existing, date):
    """True when an existing D.json was only a placeholder (held rule 10, no raw or no summary)."""
    reasons = {r.format(d=date) for r in REDO_REASONS}
    return any(isinstance(h, dict) and h.get("rule") == 10 and h.get("reason") in reasons
               for h in existing.get("held") or [])


def may_write(date, daily_dir=DAILY_DIR):
    p = Path(daily_dir) / f"{date}.json"
    if not p.is_file():
        return True
    try:
        existing = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return isinstance(existing, dict) and may_redo(existing, date)


def stamp(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv):
    if len(argv) != 2 or argv[0] not in ("skeleton", "may-write"):
        sys.exit(__doc__)
    date = argv[1]
    if argv[0] == "may-write":
        ok = may_write(date)
        print("write" if ok else f"stop: observatory/daily/{date}.json exists and is not a placeholder")
        return 0 if ok else 1
    sources = load_sources()
    raw = load_raw(date)
    if raw is None:
        out = {"raw": False, "daily": no_raw(date, sources)}
    else:
        checked, not_checked = coverage(raw, sources)
        out = {"raw": True, "checked": checked, "not_checked": not_checked,
               "status_without_items": status_for([], not_checked)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
