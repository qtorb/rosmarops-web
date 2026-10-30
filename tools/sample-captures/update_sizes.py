#!/usr/bin/env python3
"""Update the height attributes of the sample report captures (GTM-45).

Reads the height of the four 1x PNG in site/assets/sample/ and, in the six pages that show them, replaces only
the height attribute of the <source> whose srcset contains sample-mobile.<l>.png and of the <img> whose src is
/assets/sample/sample-desktop.<l>.png. If any page does not have exactly one match of each, exits with an error
without writing anything. Standard library only.
"""

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "site" / "assets" / "sample"
PAGES = [
    ("site/index.html", "en"),
    ("site/sample-report/index.html", "en"),
    ("site/es/index.html", "es"),
    ("site/es/informe-de-ejemplo/index.html", "es"),
    ("site/ca/index.html", "es"),
    ("site/ca/informe-dexemple/index.html", "es"),
]


def png_height(path):
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"{path} is not a PNG")
    return struct.unpack(">I", head[20:24])[0]


def set_height(tag, height):
    new, n = re.subn(r'\bheight="\d+"', f'height="{height}"', tag)
    if n != 1:
        raise ValueError(f"expected one height attribute in {tag[:80]}…")
    return new


def main():
    heights = {}
    for l in ("en", "es"):
        heights[("mobile", l)] = png_height(ASSETS / f"sample-mobile.{l}.png")
        heights[("desktop", l)] = png_height(ASSETS / f"sample-desktop.{l}.png")

    out = {}
    errors = []
    for rel, l in PAGES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        source_re = re.compile(r'<source\b[^>]*\bsrcset="[^"]*/sample-mobile\.' + l + r'\.png[\s"][^>]*>')
        img_re = re.compile(r'<img\b[^>]*\bsrc="/assets/sample/sample-desktop\.' + l + r'\.png"[^>]*>')
        for name, rx, key in (("source", source_re, ("mobile", l)), ("img", img_re, ("desktop", l))):
            found = rx.findall(text)
            if len(found) != 1:
                errors.append(f"{rel}: {len(found)} <{name}> matches for sample-{key[0]}.{l}.png (expected 1)")
                continue
            try:
                text = text.replace(found[0], set_height(found[0], heights[key]), 1)
            except ValueError as e:
                errors.append(f"{rel}: {e}")
        out[rel] = text

    if errors:
        print("\n".join(errors))
        sys.exit(1)
    for rel, text in out.items():
        (ROOT / rel).write_text(text, encoding="utf-8")
        print(f"{rel}: heights set")


if __name__ == "__main__":
    main()
