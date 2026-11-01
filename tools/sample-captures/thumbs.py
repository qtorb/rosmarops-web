#!/usr/bin/env python3
"""Cut the eight home thumbnails of the sample report from the current captures (GTM-66).

The top 640 px (1x) or 1280 px (2x) of sample-desktop.<l>[@2x].png and sample-mobile.<l>[@2x].png in
site/assets/sample/ become sample-thumb.<l>[@2x].png and sample-thumb-mobile.<l>[@2x].png, for l in en and es.
The full width of each capture is kept (1000 px today for desktop, 390 for mobile; the automatic workflow captures
desktop at 1280). Exits with an error, writing nothing, if a capture is shorter than the cut. Needs Pillow.
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "site" / "assets" / "sample"
TOP = 640
OUT = {"desktop": "sample-thumb", "mobile": "sample-thumb-mobile"}


def main():
    jobs = []
    for kind in ("desktop", "mobile"):
        for lang in ("en", "es"):
            for scale, sfx in ((1, ""), (2, "@2x")):
                src = ASSETS / f"sample-{kind}.{lang}{sfx}.png"
                im = Image.open(src)
                w, h = im.size
                want_h = TOP * scale
                if h < want_h:
                    sys.exit(f"{src.name}: {w}×{h}, shorter than {want_h}")
                jobs.append((im, (0, 0, w, want_h), ASSETS / f"{OUT[kind]}.{lang}{sfx}.png"))
    for im, box, dst in jobs:
        im.crop(box).save(dst, optimize=True)
        print(f"{dst.relative_to(ROOT)}: {box[2]}×{box[3]}")


if __name__ == "__main__":
    main()
