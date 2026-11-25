"""GTM-206: checks that every text of a course lesson is literal in the documents Albert signed.

Run by hand, with a local copy of qtorb/rosmarops-vigil (CI cannot read that repository):

    python3 tools/course/check_signed.py ../rosmarops-vigil

Lesson 2 («The chain»), observatory/data/course/the-chain.json:
- close.footer comes from docs/briefs/GTM-215.md (block 178, B.5);
- every other text comes from docs/research/2026-11-24-curso-publico-leccion-piloto.md (ES) and
  docs/research/2026-11-24-curso-publico-leccion-2-en-ca.md (EN, CA).
Exit code 1 and the list of texts that are not found, if any.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "observatory" / "data" / "course" / "the-chain.json"
LESSON = ["docs/research/2026-11-24-curso-publico-leccion-piloto.md",
          "docs/research/2026-11-24-curso-publico-leccion-2-en-ca.md"]
FOOTER = ["docs/briefs/GTM-215.md"]


def norm(s):
    return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()


def strings(x, path=()):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, list):
        for i, y in enumerate(x):
            yield from strings(y, path + (i,))
    elif isinstance(x, dict):
        for k, y in x.items():
            yield from strings(y, path + (k,))


def missing(vigil, data):
    lesson = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in LESSON))
    footer = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in FOOTER))
    out = []
    for lang in ("en", "es", "ca"):
        for path, s in strings(data[lang], (lang,)):
            if not s or s.startswith("/"):
                continue
            if path[1:3] == ("close", "terms") and path[-1] == 1:
                continue  # glossary ids, not text
            where = footer if path[1:] == ("close", "footer") else lesson
            # {name} placeholders: the signed text may use another name ({fuente}, {aciertos})
            rx = re.escape(norm(s)).replace(r"\{", "{").replace(r"\}", "}")
            rx = re.sub(r"\{\w+\}", r"\\{\\w+\\}", rx)
            if not re.search(rx, where):
                out.append((path, s))
    return out


if __name__ == "__main__":
    vigil = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "rosmarops-vigil"
    bad = missing(vigil, json.loads(DATA.read_text(encoding="utf-8")))
    for path, s in bad:
        print("/".join(map(str, path)), "|", s)
    print(len(bad), "texts not found")
    sys.exit(1 if bad else 0)
