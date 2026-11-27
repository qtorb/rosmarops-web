"""The RosmarOps Control Baseline (GTM-223, block 206): results on disk, the rules the schema does not cover, and which
results are published.

A result is observatory/data/minimum/<id>/<measured_at>.json, valid against observatory/schema/minim-result.v2.schema.json
(a copy of vigil docs/research/minim/schema/, unchanged). The pages and the public copies are written by build.py.

Rules checked here (vigil docs/research/2026-11-25-minim-de-control-v4-canvis.md, signed 25-11; GTM-223 point 1):
- the folder is candidate.id and the file name is measured_at;
- the seven criteria, M1 to M7, once each and in that order;
- F1 (applies.third_party_agents) is yes or no, F2 (applies.runs_on) is user_machine or vendor_cloud;
- M2 is not_applicable exactly when F1 is no, M3 exactly when F2 is vendor_cloud, and no other criterion is;
- total = the criteria that apply, met = those with yes, passes = (met == total);
- vendor.publish_after >= vendor.notified_at + 14 days, expires_at = measured_at + 90 days;
- a reply other than none has reply_at; a disputed reply has reply_url.
And what the page needs to say it with the signed texts (GTM-223 point 7: a missing text stops the build):
- installed by whoever uses it (F2 user_machine) needs tested_version, the vendor's cloud needs tested_plan;
- a criterion never has how = none (there is no text for it).
"""

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "observatory" / "data" / "minimum"
SCHEMA = ROOT / "observatory" / "schema" / "minim-result.v2.schema.json"
SCHEMA_NAME = SCHEMA.name
# GTM-232: the families, each with the kinds it groups and its address in each language (spec
# vigil docs/research/2026-11-27-minimo-de-control-fichas-de-familia.md §1).
FAMILIES = ROOT / "observatory" / "data" / "minimum-families.json"
# The criteria version the criterion page states (the v4 criteria, signed by Albert on 25-11).
CRITERIA_VERSION = 4
IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]


def day(s):
    return datetime.date.fromisoformat(s)


def problems(r, path=None):
    """What breaks the rules in one result (an empty list if nothing)."""
    out = []
    path = Path(path) if path else None
    if path is not None:
        if path.parent.name != r["candidate"]["id"]:
            out.append(f"folder {path.parent.name!r} is not candidate.id {r['candidate']['id']!r}")
        if path.stem != r["measured_at"]:
            out.append(f"file name {path.stem!r} is not measured_at {r['measured_at']!r}")
    crit = r["criteria"]
    if [c["id"] for c in crit] != IDS:
        out.append("criteria are not M1 to M7, once each and in order")
    f1 = r["applies"]["third_party_agents"]["value"]
    f2 = r["applies"]["runs_on"]["value"]
    if f1 not in ("yes", "no"):
        out.append(f"applies.third_party_agents is {f1!r}, not yes or no")
    if f2 not in ("user_machine", "vendor_cloud"):
        out.append(f"applies.runs_on is {f2!r}, not user_machine or vendor_cloud")
    na = {"M2": f1 == "no", "M3": f2 == "vendor_cloud"}
    for c in crit:
        should = na.get(c["id"], False)
        if (c["result"] == "not_applicable") != should:
            out.append(f"{c['id']} is {c['result']!r}; it {'must' if should else 'must not'} be not_applicable")
        if c["how"] == "none":
            out.append(f"{c['id']}: how is none, and the page has no text for it")
    applicable = [c for c in crit if c["result"] != "not_applicable"]
    met = sum(1 for c in applicable if c["result"] == "yes")
    if r["total"] != len(applicable):
        out.append(f"total is {r['total']}, the criteria that apply are {len(applicable)}")
    if r["met"] != met:
        out.append(f"met is {r['met']}, the criteria with yes are {met}")
    if r["passes"] != (met == len(applicable)):
        out.append(f"passes is {r['passes']}, it should be {met == len(applicable)}")
    v = r["vendor"]
    if day(v["publish_after"]) < day(v["notified_at"]) + datetime.timedelta(days=14):
        out.append("vendor.publish_after is less than 14 days after vendor.notified_at")
    if day(r["expires_at"]) != day(r["measured_at"]) + datetime.timedelta(days=90):
        out.append("expires_at is not measured_at + 90 days")
    if v["reply"] != "none" and not v.get("reply_at"):
        out.append(f"vendor.reply is {v['reply']!r} without reply_at")
    if v["reply"] == "disputed" and not v.get("reply_url"):
        out.append("vendor.reply is disputed without reply_url")
    if f2 == "user_machine" and not r.get("tested_version"):
        out.append("installed by whoever uses it, without tested_version")
    if f2 == "vendor_cloud" and not r.get("tested_plan"):
        out.append("in the vendor's cloud, without tested_plan")
    return out


def files(data=DATA):
    return sorted(Path(data).glob("*/*.json"))


def load(data=DATA):
    """Every result on disk, as (path, result). Stops on a broken rule."""
    out = []
    for f in files(data):
        r = json.loads(f.read_text(encoding="utf-8"))
        bad = problems(r, f)
        if bad:
            raise SystemExit(f"{f}: " + "; ".join(bad))
        out.append((f, r))
    return out


def published(results, today):
    """Only the results whose vendor.publish_after is today or earlier, by id, oldest first."""
    by = {}
    for f, r in results:
        if day(r["vendor"]["publish_after"]) <= day(today):
            by.setdefault(r["candidate"]["id"], []).append(r)
    return {k: sorted(v, key=lambda r: r["measured_at"]) for k, v in sorted(by.items())}


def owner_agent(rid, agent_ids):
    """Which Observatory product a result belongs to: the same id, or the id with «-cloud» at the end (n8n-cloud is
    n8n in the vendor's cloud; GTM-221 §4). None if there is no such product."""
    if rid in agent_ids:
        return rid
    if rid.endswith("-cloud") and rid[: -len("-cloud")] in agent_ids:
        return rid[: -len("-cloud")]
    return None


def families(path=FAMILIES):
    """The families, in their order. Stops if two families share a kind or an address."""
    fams = json.loads(Path(path).read_text(encoding="utf-8"))["families"]
    kinds = [k for f in fams for k in f["kinds"]]
    if len(kinds) != len(set(kinds)):
        raise SystemExit(f"{path}: a kind is in two families")
    paths = [p for f in fams for p in f["path"].values()]
    if len(paths) != len(set(paths)):
        raise SystemExit(f"{path}: two families share an address")
    return fams


def family_of(r, fams):
    """The family a result belongs to, by its kind; None for a kind no family groups (agent_framework)."""
    return next((f for f in fams if r["kind"] in f["kinds"]), None)


def clashes(fams, results, crit_path):
    """Addresses a family page and a result page would share: a family's folder under the criterion page that is the
    candidate.id of some result on disk (published or not). Empty when there is none."""
    ids = {r["candidate"]["id"] for _, r in results}
    out = []
    for f in fams:
        for lang, p in f["path"].items():
            slug = p[len(crit_path[lang]):].strip("/")
            if not p.startswith(crit_path[lang]) or "/" in slug or not slug:
                out.append(f"{p} is not one folder under {crit_path[lang]}")
            elif slug in ids:
                out.append(f"{p} is also the page of the result {slug!r}")
    return out
