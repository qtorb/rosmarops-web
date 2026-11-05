#!/usr/bin/env python3
"""Decide whether a daily synopsis needs an alert to Albert, and write the Postmark message (GTM-23 §7).

  python3 observatory/daily_alert.py push FILE [FILE...]   alert if a file is invalid, incomplete or has held items
  python3 observatory/daily_alert.py missing YYYY-MM-DD    alert that the day's file does not exist
  python3 observatory/daily_alert.py repeat YYYY-MM-DD     alert if observatory/raw/D.json is missing, or if a source
                                                           has opened false in it and in the day before's (GTM-90)

Writes one JSON message per alert to the folder in $ALERT_DIR (default: ./alerts) and prints how many.
Sending is done by the workflow with curl. The recipient is fixed here; nothing else is ever addressed.
"""

import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_check  # noqa: E402

TO = "albert@rosmarops.com"
FROM = "RosmarOps Observatorio <observatorio@rosmarops.com>"
VIGIL = "https://github.com/qtorb/rosmarops-vigil/blob/master/"
OBS = Path(__file__).resolve().parent
RAW_DIR = OBS / "raw"
SOURCES = OBS / "sources.json"


def message(date, reason, lines, summary_ref=None):
    body = [f"Fecha: {date}", f"Motivo: {reason}", ""] + lines
    if summary_ref:
        body += ["", "Resumen interno: " + VIGIL + summary_ref]
    return {"From": FROM, "To": TO, "Subject": f"Sinopsis diaria {date}: {reason}",
            "TextBody": "\n".join(body) + "\n", "MessageStream": "outbound"}


def for_file(path):
    path = Path(path)
    date = path.stem
    errs = daily_check.check(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    ref = data.get("summary_ref") if isinstance(data, dict) else None
    out = []
    if errs:
        out.append(message(date, "fichero no válido", ["Errores:"] + [f"- {e}" for e in errs], ref))
        return out
    if data.get("status") == "incomplete":
        out.append(message(date, "revisión incompleta", ["Ese día no se publica nada."]
                           + [f"- {h['reason']} ({h['source_url']})" for h in data.get("held", [])], ref))
    elif data.get("held"):
        lines = ["Puntos retenidos:"]
        for h in data["held"]:
            rule = f"regla {h['rule']}" if h.get("rule") else "sin regla"
            lines += [f"- {h['text_en']}", f"  {rule}: {h['reason']}", f"  fuente: {h['source_url']}"]
        out.append(message(date, "retenidos", lines, ref))
    return out


def plain(subject, lines):
    return {"From": FROM, "To": TO, "Subject": subject, "TextBody": "\n".join(lines) + "\n", "MessageStream": "outbound"}


def read_raw(raw_dir, date):
    p = Path(raw_dir) / f"{date}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def for_repeat(date, raw_dir=None, sources_file=SOURCES):
    """GTM-90: no collector data for D, or sources with opened false on D and on the day before."""
    raw_dir = RAW_DIR if raw_dir is None else raw_dir
    today = read_raw(raw_dir, date)
    if today is None:
        return [plain(f"Observatorio: sin datos del recolector ({date})",
                      [f"Fecha: {date}", f"No existe o no se puede leer observatory/raw/{date}.json en main.",
                       "El recolector (observatory-collect.yml) no ha escrito el fichero del día."])]
    prev_date = (datetime.date.fromisoformat(date) - datetime.timedelta(days=1)).isoformat()
    prev = read_raw(raw_dir, prev_date)
    if prev is None:
        return []
    names = {s["id"]: s["name"] for s in json.loads(Path(sources_file).read_text(encoding="utf-8"))["sources"]}
    closed_prev = {s["id"]: s for s in prev.get("sources", []) if s.get("opened") is False}
    lines = []
    for s in today.get("sources", []):
        if s.get("opened") is False and s.get("id") in closed_prev:
            lines.append(f"- {s['id']} {names.get(s['id'], '?')}: {prev_date}: {closed_prev[s['id']].get('reason')} | "
                         f"{date}: {s.get('reason')}")
    if not lines:
        return []
    return [plain(f"Observatorio: fuente que falla 2 días seguidos ({date})",
                  [f"Fecha: {date}", "Fuentes con opened false dos días seguidos:"] + lines)]


def main(argv):
    if len(argv) < 2 or argv[0] not in ("push", "missing", "repeat"):
        sys.exit(__doc__)
    msgs = []
    if argv[0] == "push":
        for f in argv[1:]:
            msgs += for_file(f)
    elif argv[0] == "repeat":
        msgs += for_repeat(argv[1])
    else:
        date = argv[1]
        msgs.append(message(date, "sin fichero a las 15:30",
                            [f"No existe observatory/daily/{date}.json en main.", "Las revisiones de las 08:13 y de las 14:13 no han terminado o no han escrito el fichero."]))
    out = Path(os.environ.get("ALERT_DIR", "alerts"))
    out.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(msgs):
        (out / f"{argv[0]}-{i}.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    print(len(msgs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
