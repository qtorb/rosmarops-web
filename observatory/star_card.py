"""GTM-206: after a click on «Download», a small card asks for a star on GitHub.

Texts and design: vigil docs/research/2026-11-24-estrella-en-github.md §2-§4 (signed by Albert, block 166).

A page takes part when one of its download blocks carries data-star-block (data-star-block="inside" when the card
has to go inside the block, as on the map, whose block sits in a row). apply() then adds, once per page:
the stylesheet, one hidden card right after the first block, and the script. The script shows the card under the
block that was clicked, the first time only. Nothing is stored in the browser and nothing is sent.

Generated pages get it through observatory/build.py (write), sandbox_section.py and course_pages.py.
The hand-written pages (homes, macOS and Linux pages) carry the same markup; `python3 observatory/star_card.py`
adds it to them if it is missing.
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
REPO = "https://github.com/qtorb/rosmarops"
V = "1"

TEXT = {
    "es": ("Gracias por probarlo. Si te resulta útil, una estrella en GitHub ayuda a que otros lo encuentren.",
           "Poner una estrella en GitHub"),
    "en": ("Thanks for trying it. If you find it useful, a star on GitHub helps others find it.",
           "Star on GitHub"),
    "ca": ("Gràcies per provar-lo. Si et resulta útil, una estrella a GitHub ajuda que altres el trobin.",
           "Posa una estrella a GitHub"),
}

STAR = ('<svg class="star-ico" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
        '<path d="M8 1.5l1.9 4.1 4.4.5-3.3 3 .9 4.4L8 11.3l-3.9 2.2.9-4.4-3.3-3 4.4-.5z" fill="none" '
        'stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>')

# Hand-written pages and the class of their download block. «.get» on the homes holds the Store badge and the
# GitHub link; «.dl» on the macOS and Linux pages holds the two buttons.
HAND = {
    "index.html": "get", "es/index.html": "get", "ca/index.html": "get",
    "macos/index.html": "dl", "es/macos/index.html": "dl", "ca/macos/index.html": "dl",
    "linux/index.html": "dl", "es/linux/index.html": "dl", "ca/linux/index.html": "dl",
}

CSS_LINK = f'<link rel="stylesheet" href="/assets/star/star.css?v={V}">'
SCRIPT = f'<script src="/assets/star/star.js?v={V}" defer></script>'
BLOCK = re.compile(r'<[a-z]+ [^>]*data-star-block(?:="inside")?[^>]*>')


def card(lang):
    text, button = TEXT[lang]
    return (f'<div class="star-card" id="star-card" role="status" hidden><p>{html.escape(text)}</p>'
            f'<a class="star-btn" href="{REPO}" target="_blank" rel="noopener">{STAR}{html.escape(button)}</a></div>')


def lang_of(page):
    m = re.search(r'<html lang="([a-z]{2})"', page)
    return m.group(1) if m else None


def end_of_element(page, start):
    """Index just after the element that opens at start (counting nested tags of the same name)."""
    name = re.match(r"<([a-z]+)", page[start:]).group(1)
    depth, pos = 0, start
    rx = re.compile(r"<(/?)%s\b[^>]*>" % name)
    for m in rx.finditer(page, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
        pos = m.end()
    raise ValueError("unclosed <%s>" % name)


def apply(page, lang=None):
    """The page with the stylesheet, one hidden card and the script, if it has a marked download block."""
    m = BLOCK.search(page)
    lang = lang or lang_of(page)
    if not m or lang not in TEXT or 'id="star-card"' in page:
        return page
    if 'data-star-block="inside"' in m.group(0):
        at = end_of_element(page, m.start())
        close = page.rfind("</", 0, at)
        page = page[:close] + card(lang) + page[close:]
    else:
        at = end_of_element(page, m.start())
        page = page[:at] + card(lang) + page[at:]
    page = page.replace("</head>", CSS_LINK + "\n</head>", 1)
    return page.replace("</body>", SCRIPT + "\n</body>", 1)


def mark_hand(page, cls):
    """Adds data-star-block to every download block of a hand-written page."""
    return re.sub(r'<div class="%s">' % cls, f'<div class="{cls}" data-star-block>', page)


def hand_pages(site=SITE):
    out = {}
    for rel, cls in HAND.items():
        f = Path(site) / rel
        s = f.read_text(encoding="utf-8")
        out[rel] = apply(mark_hand(s, cls))
    return out


if __name__ == "__main__":
    for rel, text in hand_pages().items():
        f = SITE / rel
        if f.read_text(encoding="utf-8") != text:
            f.write_text(text, encoding="utf-8")
            print("updated", rel)
    sys.exit(0)
