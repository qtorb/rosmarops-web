#!/usr/bin/env python3
"""Decide whether a daily synopsis needs an alert to Albert, and write the Postmark message (GTM-23 §7).

  python3 observatory/daily_alert.py push FILE [FILE...]   alert if a file is invalid, incomplete or has held items
  python3 observatory/daily_alert.py missing YYYY-MM-DD    alert that the day's file does not exist

Writes one JSON message per alert to the folder in $ALERT_DIR (default: ./alerts) and prints how many.
Sending is done by the workflow with curl. The recipient is fixed here; nothing else is ever addressed.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_check  # noqa: E402

TO = "albert@rosmarops.com"
FROM = "RosmarOps Observatorio <observatorio@rosmarops.com>"
VIGIL = "https://github.com/qtorb/rosmarops-vigil/blob/master/"


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


def main(argv):
    if len(argv) < 2 or argv[0] not in ("push", "missing"):
        sys.exit(__doc__)
    msgs = []
    if argv[0] == "push":
        for f in argv[1:]:
            msgs += for_file(f)
    else:
        date = argv[1]
        msgs.append(message(date, "sin fichero a las 09:30",
                            [f"No existe observatory/daily/{date}.json en main.", "La revisión de las 08:13 no ha terminado o no ha escrito el fichero."]))
    out = Path(os.environ.get("ALERT_DIR", "alerts"))
    out.mkdir(parents=True, exist_ok=True)
    for i, m in enumerate(msgs):
        (out / f"{i}.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    print(len(msgs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
