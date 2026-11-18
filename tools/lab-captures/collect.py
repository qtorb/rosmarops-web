#!/usr/bin/env python3
"""BV-250 / CTO-61 §4, places of GTM-182: bring a sandbox lab release into the guide.

usage: collect.py current                         prints the release already imported, or nothing
       collect.py import RELEASE_DIR TAG          imports RELEASE_DIR (the release's files, downloaded)

Imports the same way GTM-182 did by hand (GTM-183):
- every file the release's manifest.json lists (its meta files and each entry's files) is checked against its SHA-256;
  any mismatch, missing or unsafe name stops it before anything is written;
- the manifest is copied unchanged to observatory/data/lab/manifest.json;
- only the PNGs of «concluyente» entries are copied, to site/assets/sandbox-lab/, which is emptied of PNGs first; the
  .txt files and the «no_concluyente» or «inesperado» entries are not published (the «inesperado» ones are printed,
  for the pull request).
The guide (observatory/build.py) then places each capture in its box.
"""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "observatory" / "data" / "lab" / "manifest.json"
IMAGES = ROOT / "site" / "assets" / "sandbox-lab"


def current(manifest=MANIFEST):
    """The release already imported (the `release` of the manifest in use), or None."""
    try:
        return json.loads(Path(manifest).read_text(encoding="utf-8")).get("release")
    except (OSError, ValueError, AttributeError):
        return None


def check(src, name, want):
    path = os.path.join(src, name)
    if os.path.basename(name) != name or name.startswith(".") or not os.path.isfile(path):
        raise SystemExit(f"missing or unsafe file: {name}")
    with open(path, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != want:
            raise SystemExit(f"SHA-256 mismatch: {name}")


def import_release(src, tag, manifest=MANIFEST, images=IMAGES):
    """Checks and imports a downloaded release. Returns (published PNGs, «inesperado» entries)."""
    raw = Path(src, "manifest.json").read_bytes()
    m = json.loads(raw)
    if m.get("release") != tag:
        raise SystemExit(f"manifest.json is for {m.get('release')}, not {tag}")
    for name, want in m.get("meta", {}).items():
        check(src, name, want)
    for e in m["entries"]:
        for name, want in e["files"].items():
            check(src, name, want)
    kept = [n for e in m["entries"] if e["result"] == "concluyente" for n in e["files"] if n.endswith(".png")]
    unexpected = [e for e in m["entries"] if e["result"] == "inesperado"]
    images = Path(images)
    images.mkdir(parents=True, exist_ok=True)
    for old in images.glob("*.png"):
        old.unlink()
    for name in kept:
        shutil.copyfile(os.path.join(src, name), images / name)
    Path(manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(manifest).write_bytes(raw)  # unchanged, so its SHA-256 can be checked against the release
    return kept, unexpected


def main(argv):
    if argv[1:2] == ["current"] and len(argv) == 2:
        print(current() or "")
    elif argv[1:2] == ["import"] and len(argv) == 4:
        kept, unexpected = import_release(argv[2], argv[3])
        print(f"concluyente: {len(kept)}")
        for e in unexpected:
            png = next(n for n in e["files"] if n.endswith(".png"))
            print(f"INESPERADO {png}: {e['command']}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
