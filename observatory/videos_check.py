"""GTM-199: marks a video public when it appears in the channel's public list.

Reads the channel's public RSS feed (only public videos are listed there) and, for each data file in
observatory/data/videos/ whose youtube_id is in the feed:
- sets "public" to true and "public_since" to today if it wasn't public yet;
- fills "upload_date" from the feed if it is empty;
- downloads the thumbnail to site/assets/video/ if it isn't there yet (from i.ytimg.com, by the repository, never by a
  visitor).
Prints what changed. The workflow then rebuilds the site and opens a pull request; nothing is deployed until Albert
approves it.

Usage: python3 observatory/videos_check.py --feed feed.xml [--today 2026-11-22] [--no-thumbs]
"""

import argparse
import datetime
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "observatory" / "data" / "videos"
SITE = ROOT / "site"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def feed_videos(xml_text):
    """{youtube_id: published date (YYYY-MM-DD)} from the channel's feed."""
    root = ET.fromstring(xml_text)
    out = {}
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS)
        pub = e.findtext("a:published", default="", namespaces=NS)[:10]
        if YT_ID.match(vid):
            out[vid] = pub
    return out


def fetch_thumb(vid, dest):
    for size in ("maxresdefault", "hqdefault"):
        try:
            with urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{size}.jpg", timeout=20) as r:
                data = r.read()
            if len(data) > 5000:
                dest.write_bytes(data)
                return True
        except Exception:
            continue
    return False


def update(feed, today, folder=DATA, site=SITE, thumbs=True):
    changes = []
    for p in sorted(Path(folder).glob("*.json")):
        text = p.read_text(encoding="utf-8")
        v = json.loads(text)
        ids = v.get("youtube_id")
        ids = list(ids.values()) if isinstance(ids, dict) else [ids]  # GTM-236: one id per language
        found = [i for i in ids if i and i in feed]
        if not found:
            continue
        vid = found[0]
        new = text
        if not v.get("public"):
            new = re.sub(r'"public": false', '"public": true', new, count=1)
            changes.append(f"{p.stem}: now public")
        if not v.get("public_since"):
            new = re.sub(r'"public_since": null', f'"public_since": "{today}"', new, count=1)
        if not v.get("upload_date") and feed[vid]:
            new = re.sub(r'"upload_date": null', f'"upload_date": "{feed[vid]}"', new, count=1)
            changes.append(f"{p.stem}: upload_date {feed[vid]}")
        thumb = None if isinstance(v["thumb"], dict) else Path(site) / v["thumb"].lstrip("/")  # per-language thumbs are in the repository
        if thumbs and thumb and not thumb.exists():
            if fetch_thumb(vid, thumb):
                changes.append(f"{p.stem}: thumbnail {v['thumb']}")
            else:
                changes.append(f"{p.stem}: thumbnail NOT downloaded")
        if new != text:
            json.loads(new)
            p.write_text(new, encoding="utf-8")
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", required=True)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--no-thumbs", action="store_true")
    a = ap.parse_args()
    for c in update(feed_videos(Path(a.feed).read_text(encoding="utf-8")), a.today, thumbs=not a.no_thumbs):
        print(c)


if __name__ == "__main__":
    main()
