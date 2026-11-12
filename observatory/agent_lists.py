#!/usr/bin/env python3
"""GTM-99: one source for the agents RosmarOps scores and detects, and the checks that keep the web from contradicting it.

The source is agent.rosmarops of each observatory/data/agents/<id>.json: status "evaluated" (scored), "detected" or
"not_supported", with since_version (decision of Albert, 07-11: no new field). observatory/data/program-agents.json
maps the program's knowledge files (internal/knowledge/<id>.json in qtorb/rosmarops) to agent files.

  python3 observatory/agent_lists.py render              rewrite the lists between the markers in the 13 pages
  python3 observatory/agent_lists.py check               checks a-d; reads the latest release through the public API
  python3 observatory/agent_lists.py release TAG         set scored agents from the knowledge files of TAG (release PR)

Markers, in each page: <!-- agents:scored --> ... <!-- /agents:scored --> (and agents:detected). An optional style
after the name, e.g. <!-- agents:scored chips -->, renders chips instead of a sentence list. The sentence around the
markers stays literal: only the names between them are generated.
"""

import hashlib
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "observatory" / "data" / "agents"
PROGRAM = ROOT / "observatory" / "data" / "program-agents.json"
EXCLUSIONS = ROOT / "observatory" / "data" / "agent-list-exclusions.json"
CANDIDATES = ROOT / "observatory" / "data" / "candidates.json"
SAMPLE = ROOT / "site" / "sample-report"
REPO = "qtorb/rosmarops"
API = "https://api.github.com/repos/" + REPO

# The 13 pages with the agent lists, and their language.
PAGES = {
    "site/index.html": "en", "site/es/index.html": "es", "site/ca/index.html": "ca",
    "site/methodology/index.html": "en", "site/es/metodologia/index.html": "es", "site/ca/metodologia/index.html": "ca",
    "site/faq/index.html": "en", "site/es/preguntas-frecuentes/index.html": "es", "site/ca/preguntes-frequents/index.html": "ca",
    "site/llms.txt": "en",
    "wp/pages/about-en.html": "en", "wp/pages/que-es-rosmarops-es.html": "es", "wp/pages/que-es-rosmarops-ca.html": "ca",
}
# GTM-137 (12-11): the homes have no generated list; their list of the nine scored agents is a literal sentence signed
# by Albert (T3), allowed in agent-list-exclusions.json. render() leaves them alone; check_pages() still reads them.
NO_MARKERS = {"site/index.html", "site/es/index.html", "site/ca/index.html"}
AND = {"en": " and ", "es": " y ", "ca": " i "}
KINDS = {"scored": "evaluated", "detected": "detected"}
MARKER = re.compile(r"<!-- agents:(scored|detected)(?: (\w+))? -->(.*?)<!-- /agents:\1 -->", re.S)
OTHER_GENERATED = re.compile(r"<!-- observatory agents:start -->.*?<!-- observatory agents:end -->", re.S)  # build.py


def version_key(s):
    return [int(p) if p.isdigit() else p for p in re.findall(r"\d+|\D+", s or "")]


def load_agents(folder=AGENTS):
    return [json.loads(f.read_text(encoding="utf-8"))["agent"] for f in sorted(folder.glob("*.json"))]


def list_names(root=ROOT):
    """Names some agents take in the list of scored agents, per language (program-agents.json, signed by Albert):
    e.g. GitHub Copilot is scored only in VS Code."""
    f = root / "observatory" / "data" / "program-agents.json"
    return json.loads(f.read_text(encoding="utf-8")).get("scored_list_names", {}) if f.exists() else {}


def names(agents, kind, lang="en", overrides=None):
    """Names of the agents with that status, oldest since_version first, then by name. In the scored list, an agent
    with a name in scored_list_names takes that name in the page's language."""
    overrides = list_names() if overrides is None else overrides
    sel = [a for a in agents if a["rosmarops"]["status"] == KINDS[kind]]
    sel.sort(key=lambda a: (version_key(a["rosmarops"].get("since_version", "")), a["name"].lower()))
    if kind != "scored":
        return [a["name"] for a in sel]
    return [overrides.get(a["id"], {}).get(lang, a["name"]) for a in sel]


def join(items, lang):
    if len(items) < 2:
        # A single name would need a singular sentence around it: that is a wording change for Albert, not ours.
        raise ValueError(f"an agent list needs at least two names, got {items}")
    return ", ".join(items[:-1]) + AND[lang] + items[-1]


def render_list(items, lang, kind, style, page):
    if style == "chips":
        cls = "chip on" if kind == "scored" else "chip"
        return "".join(f'<span class="{cls}">{html.escape(n)}</span>' for n in items)
    text = join(items, lang)
    return text if page.endswith(".txt") else html.escape(text, quote=False)


def render_text(text, lang, agents, page):
    """Rewrite the lists between the markers. The same list repeated elsewhere in the page (its meta description or
    JSON-LD, where a comment cannot go) is a mirror: the old text of each sentence-style marker is replaced there too,
    so the copies change together."""
    mirrors = []
    for m in MARKER.finditer(text):
        if m.group(2) == "chips":
            olds = [html.unescape(n) for n in re.findall(r"<span[^>]*>([^<]*)</span>", m.group(3))]
            old = join(olds, lang) if len(olds) >= 2 else ""
        else:
            old = html.unescape(m.group(3)).strip()
        new = join(names(agents, m.group(1), lang), lang)
        if old and old != new:
            mirrors.append((old, new))

    def sub(m):
        kind, style = m.group(1), m.group(2)
        body = render_list(names(agents, kind, lang), lang, kind, style, page)
        head = f"<!-- agents:{kind}{' ' + style if style else ''} -->"
        return f"{head}{body}<!-- /agents:{kind} -->"

    parts, last = [], 0
    for m in MARKER.finditer(text):
        outside = text[last:m.start()]
        for old, new in mirrors:
            outside = outside.replace(old, new)
        parts += [outside, sub(m)]
        last = m.end()
    outside = text[last:]
    for old, new in mirrors:
        outside = outside.replace(old, new)
    parts.append(outside)
    return "".join(parts)


def render(root=ROOT, agents=None):
    agents = agents if agents is not None else load_agents(root / "observatory" / "data" / "agents")
    changed = []
    for page, lang in PAGES.items():
        f = root / page
        old = f.read_text(encoding="utf-8")
        if not MARKER.search(old):
            if page in NO_MARKERS:
                continue
            raise SystemExit(f"{page}: no <!-- agents:... --> markers")
        new = render_text(old, lang, agents, page)
        if new != old:
            f.write_text(new, encoding="utf-8")
            changed.append(page)
    return changed


# ------------------------------------------------------------------------------------------------------------ checks

def check_candidates(agents, candidates):
    """a. No agent with a file appears in candidates.json (by name, any case)."""
    have = {a["name"].lower() for a in agents} | {a["id"].lower() for a in agents}
    return [f"candidates.json: {c['name']} has an agent file" for c in candidates if c["name"].lower() in have]


def check_scored(agents, knowledge, program):
    """b. The scored set equals the program's knowledge files at the latest release, through program-agents.json."""
    errs = []
    mapping, not_agents = program["knowledge_to_file"], set(program["not_agents"])
    ids = {a["id"] for a in agents}
    expected = set()
    for k in knowledge:
        if k in not_agents:
            continue
        if k not in mapping:
            errs.append(f"knowledge file {k}.json has no entry in program-agents.json")
            continue
        if mapping[k] not in ids:
            errs.append(f"program-agents.json maps {k} to {mapping[k]}, which has no agent file")
            continue
        expected.add(mapping[k])
    scored = {a["id"] for a in agents if a["rosmarops"]["status"] == "evaluated"}
    errs += [f"{i} is scored in the program's release but not evaluated in its agent file" for i in sorted(expected - scored)]
    errs += [f"{i} is evaluated in its agent file but has no knowledge file in the program's release" for i in sorted(scored - expected)]
    return errs


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_sample(tag, digests, sample=SAMPLE):
    """c. site/sample-report is the latest release's: VERSION is its tag and both reports match its assets."""
    errs = []
    version = (sample / "VERSION").read_text(encoding="utf-8").strip()
    if version != tag:
        errs.append(f"site/sample-report/VERSION is {version}, the latest release is {tag}")
    for name in ("sample-report.en.html", "sample-report.es.html"):
        want = digests.get(name)
        if not want:
            errs.append(f"release {tag} has no {name}")
        elif sha256(sample / name) != want:
            errs.append(f"site/sample-report/{name} is not the one in release {tag}")
    return errs


def split(text):
    out = []
    for line in text.splitlines():
        for s in re.split(r"(?<=[.!?])\s+|\",\s*\"", line):
            s = re.sub(r"\s+", " ", s).strip()
            if s:
                out.append(s)
    return out


def segments(text):
    """(segment, mirror_zone) pairs of a page outside the generated blocks: sentences and lines of the visible text
    (chips of one row stay together), and the meta descriptions and JSON-LD, where a comment marker cannot go and the
    generated list may only appear as an exact copy (mirror_zone True)."""
    text = MARKER.sub(" ", text)
    text = OTHER_GENERATED.sub(" ", text)
    zone = [html.unescape(c) for c in re.findall(r'<meta\b[^>]*\bcontent="([^"]*)"', text, flags=re.I)]
    zone += [html.unescape(c) for c in re.findall(r"<script\b[^>]*>(.*?)</script>", text, flags=re.S | re.I)]
    zone += [html.unescape(c) for c in re.findall(r"<title>(.*?)</title>", text, flags=re.S | re.I)]
    text = re.sub(r"<(script|style|title)\b.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"</?(p|div|li|ul|ol|h[1-6]|br|tr|td|th|section|header|footer|nav|table|dd|dt|summary)\b[^>]*>",
                  "\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return [(s, False) for s in split(text)] + [(s, True) for z in zone for s in split(z)]


def check_pages(agents, exclusions, root=ROOT):
    """d. In the 13 pages, no visible segment outside the markers names two or more agents with a file, unless it is a
    prose mention listed in agent-list-exclusions.json. In the meta descriptions and JSON-LD, only an exact copy of
    the generated list is allowed (render keeps those copies in step)."""
    rx = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in sorted({a["name"] for a in agents}, key=len, reverse=True))
                    + r")(?![\w-])")
    errs = []
    for page, lang in PAGES.items():
        generated = [join(names(agents, k, lang), lang) for k in KINDS]
        allowed = [e["contains"] for e in exclusions if e["page"] == page]
        for seg, mirror_zone in segments((root / page).read_text(encoding="utf-8")):
            if any(a in seg for a in allowed):
                continue
            rest = seg
            if mirror_zone:
                for g in generated:
                    rest = rest.replace(g, " ")
            if len(set(rx.findall(rest))) >= 2:
                where = "a copy in the meta or JSON-LD that differs from the generated list" if mirror_zone else "a list outside the markers"
                errs.append(f"{page}: {where}: «{seg[:160]}»")
    return errs


# --------------------------------------------------------------------------------------------- the program release

def api_get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": "RosmarOps-Observatory/1 (+https://rosmarops.com)"})
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def latest_release():
    """(tag, {asset name: sha256}) of the latest release of qtorb/rosmarops."""
    rel = api_get("/releases/latest")
    digests = {a["name"]: (a.get("digest") or "").removeprefix("sha256:") for a in rel.get("assets", [])}
    return rel["tag_name"], digests


def knowledge_files(tag):
    items = api_get(f"/contents/internal/knowledge?ref={tag}")
    return sorted(i["name"][:-5] for i in items if i["type"] == "file" and i["name"].endswith(".json"))


def run_checks(tag, digests, knowledge, root=ROOT):
    agents = load_agents(root / "observatory" / "data" / "agents")
    errs = check_candidates(agents, json.loads((root / "observatory" / "data" / "candidates.json").read_text(encoding="utf-8")))
    errs += check_scored(agents, knowledge, json.loads((root / "observatory" / "data" / "program-agents.json").read_text(encoding="utf-8")))
    errs += check_sample(tag, digests, root / "site" / "sample-report")
    errs += check_pages(agents, json.loads((root / "observatory" / "data" / "agent-list-exclusions.json").read_text(encoding="utf-8")), root)
    return errs


def release(tag, knowledge, root=ROOT):
    """Set agent.rosmarops for the release: mapped knowledge files become evaluated since TAG (if not already). Returns
    notes for the PR: what changed and what needs Albert (unmapped files, agents no longer scored)."""
    program = json.loads((root / "observatory" / "data" / "program-agents.json").read_text(encoding="utf-8"))
    folder = root / "observatory" / "data" / "agents"
    version = tag.lstrip("v")
    notes, expected = [], set()
    for k in knowledge:
        if k in program["not_agents"]:
            continue
        fid = program["knowledge_to_file"].get(k)
        if not fid or not (folder / f"{fid}.json").exists():
            notes.append(f"needs Albert: knowledge file {k}.json has no agent file mapped in program-agents.json")
            continue
        expected.add(fid)
        f = folder / f"{fid}.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["agent"]["rosmarops"]["status"] != "evaluated":
            d["agent"]["rosmarops"] = {"status": "evaluated", "since_version": version}
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            notes.append(f"{fid}: now evaluated since {version}")
    for a in load_agents(folder):
        if a["rosmarops"]["status"] == "evaluated" and a["id"] not in expected:
            notes.append(f"needs Albert: {a['id']} is evaluated but has no knowledge file in {tag}; left as it is")
    return notes


def main(argv):
    if not argv or argv[0] not in ("render", "check", "release"):
        sys.exit(__doc__)
    if argv[0] == "render":
        for p in render():
            print("updated", p)
        return 0
    if argv[0] == "check":
        try:
            tag, digests = latest_release()
            knowledge = knowledge_files(tag)
        except Exception as e:  # noqa: BLE001 - not reading the release is a failed check, never a pass
            print(f"{'::error::' if os.environ.get('GITHUB_ACTIONS') else 'FAIL '}cannot read the latest release of {REPO}: {e}")
            return 1
        errs = run_checks(tag, digests, knowledge)
        for e in errs:
            print("::error::" + e if os.environ.get("GITHUB_ACTIONS") else "FAIL " + e)
        print(f"agent lists: {len(errs)} problem(s) against {REPO} {tag}")
        return 1 if errs else 0
    tag = argv[1]
    for n in release(tag, knowledge_files(tag)):
        print(n)
    render()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
