#!/usr/bin/env python3
"""BV-250 / CTO-61 §4: take the «concluyente» captures of a lab release.

usage: collect.py RELEASE_DIR DEST_DIR TAG

RELEASE_DIR holds the release's manifest.json and files (downloaded by the
workflow). Every file listed in the manifest is checked against its SHA-256;
any mismatch or missing file stops it. Only the PNGs of entries with result
«concluyente» are copied to DEST_DIR, with a manifest.json that lists only
those entries (their date and versions go next to each capture). The
«inesperado» ones are printed for the PR, not copied.
"""

import hashlib
import json
import os
import shutil
import sys

src, dest, tag = sys.argv[1:4]
manifest = json.load(open(os.path.join(src, "manifest.json")))
if manifest.get("release") != tag:
    sys.exit(f"manifest.json is for {manifest.get('release')}, not {tag}")


def check(name, want):
    path = os.path.join(src, name)
    if os.path.basename(name) != name or not os.path.isfile(path):
        sys.exit(f"missing or unsafe file: {name}")
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != want:
        sys.exit(f"SHA-256 mismatch: {name}")


for name, want in manifest.get("meta", {}).items():
    check(name, want)
kept, unexpected = [], []
for e in manifest["entries"]:
    for name, want in e["files"].items():
        check(name, want)
    if e["result"] == "concluyente":
        kept.append(e)
    elif e["result"] == "inesperado":
        unexpected.append(e)

os.makedirs(dest, exist_ok=True)
for name in os.listdir(dest):
    if name.endswith(".png") or name == "manifest.json":
        os.remove(os.path.join(dest, name))
for e in kept:
    for name in e["files"]:
        if name.endswith(".png"):
            shutil.copyfile(os.path.join(src, name), os.path.join(dest, name))
json.dump({"schema": manifest["schema"], "release": tag, "entries": kept},
          open(os.path.join(dest, "manifest.json"), "w"), indent=2, ensure_ascii=False)
with open(os.path.join(dest, "VERSION"), "w") as f:
    f.write(tag + "\n")
print(f"concluyente: {len(kept)}")
for e in unexpected:
    png = next(n for n in e["files"] if n.endswith(".png"))
    print(f"INESPERADO {png}: {e['command']}")
