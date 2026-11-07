"""GTM-105: the data of «The AI agents map» in the agent files (schema v1.8): surfaces[] and reads_from[].

Run from the repository root:  python3 -m unittest observatory/tests/test_map_data.py
"""

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "observatory" / "data" / "agents"
SHARED = ROOT / "observatory" / "data" / "shared-files.json"
CORRECTABLE = ("name", "vendor", "kinds", "platforms", "local_footprint")
PROGRAM = ROOT / "observatory" / "data" / "program-agents.json"


def files():
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(AGENTS.glob("*.json"))}


def check(agents, shared):
    """Problems in surfaces[] and reads_from[] that the schema cannot see."""
    errs = []
    owners = {p["path"]: p["owner"] for p in shared["paths"]}
    for aid, d in agents.items():
        seen = set()
        for s in d.get("surfaces", []):
            where = f"{aid} surface {s['surface']}"
            if s["surface"] in seen:
                errs.append(f"{where}: listed twice")
            seen.add(s["surface"])
            if (s["since"] is None) != (s["since_basis"] is None):
                errs.append(f"{where}: since and since_basis must be both set or both null")
            if s["since_basis"] == "announced" and s["verified"]["how"] == "official_code":
                errs.append(f"{where}: an announced date comes from a changelog or an announcement, not from code")
        pairs = set()
        for r in d.get("reads_from", []):
            where = f"{aid} reads {r['path']}"
            if (r["path"], r["load"], r.get("condition")) in pairs:
                errs.append(f"{where}: listed twice")
            pairs.add((r["path"], r["load"], r.get("condition")))
            if r["path"] not in owners:
                errs.append(f"{where}: path not in shared-files.json")
            elif owners[r["path"]] != r["owner"]:
                errs.append(f"{where}: owner {r['owner']}, shared-files.json says {owners[r['path']]}")
            if r["owner"] != "shared" and r["owner"] not in agents:
                errs.append(f"{where}: owner {r['owner']} has no agent file")
            if r["owner"] == aid:
                errs.append(f"{where}: an agent does not read its own files here")
        for e in d.get("surfaces", []) + d.get("reads_from", []):
            src, ver = e["source"], e["verified"]
            if src.get("official") is not True or not src.get("accessed_at") or not ver.get("at"):
                errs.append(f"{aid}: entry without an official source, its accessed_at or its verification date: {src.get('url')}")
    for p in shared["paths"]:
        if p["owner"] != "shared" and p["owner"] not in agents:
            errs.append(f"shared-files.json: owner {p['owner']} of {p['path']} has no agent file")
    if len({p["path"] for p in shared["paths"]}) != len(shared["paths"]):
        errs.append("shared-files.json: a path is listed twice")
    return errs


def uncited_corrections(base, head):
    """GTM-106: fields of agent.CORRECTABLE that changed from base to head without an agent.sources[] entry."""
    errs = []
    for aid, d in head.items():
        if aid not in base:
            continue  # a new file is opened, not corrected
        cited = {s["field"] for s in d["agent"].get("sources", [])}
        for f in CORRECTABLE:
            if base[aid]["agent"].get(f) != d["agent"].get(f) and f not in cited:
                errs.append(f"{aid}: agent.{f} changed without an agent.sources[] entry for it")
    return errs


def base_files(rev):
    out = {}
    for f in AGENTS.glob("*.json"):
        p = subprocess.run(["git", "show", f"{rev}:observatory/data/agents/{f.name}"], cwd=ROOT, capture_output=True, text=True)
        if p.returncode == 0:
            out[f.stem] = json.loads(p.stdout)
    return out


class MapData(unittest.TestCase):
    def test_repository(self):
        self.assertEqual(check(files(), json.loads(SHARED.read_text(encoding="utf-8"))), [])

    def test_rosmarops_states_come_from_program_agents(self):
        if not PROGRAM.exists():
            self.skipTest("observatory/data/program-agents.json arrives with GTM-99 (#67)")
        mapped = set(json.loads(PROGRAM.read_text(encoding="utf-8"))["knowledge_to_file"].values())
        scored = {a for a, d in files().items() if d["agent"]["rosmarops"]["status"] == "evaluated"}
        self.assertEqual(scored, mapped)

    def test_corrections_are_cited(self):
        rev = os.environ.get("OBS_BASE")
        if not rev or subprocess.run(["git", "cat-file", "-e", rev], cwd=ROOT).returncode:
            self.skipTest("no base commit (OBS_BASE) to compare with; CI sets it")
        self.assertEqual(uncited_corrections(base_files(rev), files()), [])

    def test_correction_rule(self):
        src = {"field": "local_footprint", "source": {"url": "https://example.test", "official": True, "accessed_at": "2026-11-07"},
               "verified": {"by": "advisor", "at": "2026-11-07", "how": "official_doc"}}
        base = {"x": {"agent": {"name": "X", "local_footprint": "no", "kinds": ["cloud"]}}}
        head = {"x": {"agent": {"name": "X", "local_footprint": "partial", "kinds": ["cloud", "cli"], "sources": [src]}},
                "new": {"agent": {"name": "N"}}}
        self.assertEqual(uncited_corrections(base, head), ["x: agent.kinds changed without an agent.sources[] entry for it"])

    def entry(self, **kw):
        e = {"source": {"url": "https://example.test/doc", "official": True, "accessed_at": "2026-11-07"},
             "verified": {"by": "advisor", "at": "2026-11-07", "how": "official_doc"}}
        e.update(kw)
        return e

    def test_failing_cases(self):
        shared = {"paths": [{"path": "AGENTS.md", "owner": "shared"}, {"path": "CLAUDE.md", "owner": "a"}]}
        agents = {
            "a": {"surfaces": [self.entry(surface="mcp", since="2026-01-01", since_basis=None)],
                  "reads_from": [self.entry(path="CLAUDE.md", owner="a", load="default")]},
            "b": {"surfaces": [self.entry(surface="hooks", since=None, since_basis=None),
                               self.entry(surface="hooks", since=None, since_basis=None)],
                  "reads_from": [self.entry(path=".mystery", owner="shared", load="default"),
                                 self.entry(path="CLAUDE.md", owner="shared", load="default"),
                                 dict(self.entry(path="AGENTS.md", owner="shared", load="default"),
                                      source={"url": "https://x.test", "official": False, "accessed_at": "2026-11-07"})]},
        }
        errs = check(agents, shared)
        for want in ["a surface mcp: since and since_basis", "a reads CLAUDE.md: an agent does not read its own files",
                     "b surface hooks: listed twice", "b reads .mystery: path not in shared-files.json",
                     "b reads CLAUDE.md: owner shared, shared-files.json says a", "b: entry without an official source"]:
            self.assertTrue(any(e.startswith(want) for e in errs), (want, errs))

    def test_passing_case(self):
        shared = {"paths": [{"path": "AGENTS.md", "owner": "shared"}, {"path": "CLAUDE.md", "owner": "a"}]}
        agents = {"a": {}, "b": {"surfaces": [self.entry(surface="mcp", since="2026-01-01", since_basis="announced")],
                                 "reads_from": [self.entry(path="CLAUDE.md", owner="a", load="default", condition="only_if_no_agents_md")]}}
        self.assertEqual(check(agents, shared), [])


if __name__ == "__main__":
    unittest.main()
