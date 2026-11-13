"""GTM-152: the share image (og:image, 1200x630) of the AI agent map, one per language.

Only signed texts from observatory/i18n/map.json (eyebrow, H1 and the four class names) and no agent data, so the
image does not go out of date with each release. Rendered with Chromium (Python Playwright) and the Inter font.

Run from the repository root:  python3 observatory/map_social.py
"""

import base64
import html
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "assets" / "brand" / "observatory"
MARK = (OUT / "observatory-mark.svg").read_bytes()
TEXTS = json.loads((ROOT / "observatory" / "i18n" / "map.json").read_text(encoding="utf-8"))["texts"]
COLORS = {"A": ("#E7EFE9", "#3F5E49"), "B": ("#FBF0D9", "#8A5A00"), "C": ("#FBEAE5", "#A3361F"), "D": ("#A3361F", "#FFFFFF")}


def page(lang):
    t = TEXTS[lang]
    e = html.escape
    mark = "data:image/svg+xml;base64," + base64.b64encode(MARK).decode()
    classes = "".join(
        f'<div class="c"><span class="b" style="background:{COLORS[c][0]};color:{COLORS[c][1]}">{c}</span>{e(t["class." + c])}</div>'
        for c in "ABCD")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1200px;height:630px;background:#F6F5F2;color:#1B1A18;font-family:Inter,sans-serif;padding:64px 72px;display:flex;flex-direction:column;justify-content:space-between}}
.top{{display:flex;align-items:center;gap:18px;font-size:24px;font-weight:600;color:#4F4C46;letter-spacing:.01em}}
.top img{{width:56px;height:56px}}
h1{{font-size:60px;line-height:1.08;font-weight:700;letter-spacing:-.02em;max-width:1000px}}
.cls{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 40px;font-size:24px;color:#3A3833}}
.c{{display:flex;align-items:center;gap:16px}}
.b{{display:inline-grid;place-items:center;width:44px;height:44px;border-radius:11px;font-weight:800;font-size:22px;flex:none}}
.foot{{font-size:22px;color:#4F4C46}}
</style></head><body>
<div class="top"><img src="{mark}" alt="">{e(t["b1.eyebrow"])}</div>
<h1>{e(t["b1.h1"])}</h1>
<div class="cls">{classes}</div>
<div class="foot">rosmarops.com</div>
</body></html>"""


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ("en", "es", "ca"):
            pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
            pg.set_content(page(lang))
            pg.screenshot(path=str(OUT / f"map-social-{lang}.png"))
            pg.close()
        b.close()


if __name__ == "__main__":
    main()
