"""GTM-88 (signed by Albert 23-11): the version and date sentence of the three sample report pages comes from the
release, not from hand. The version is site/sample-report/VERSION; the date is the run date printed in the header
of site/sample-report/sample-report.en.html («2026-11-22 21:25 · Windows · …»).

Usage: python3 tools/sample-captures/version_sentence.py [site folder]
"""
import pathlib
import re
import sys

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"],
    "ca": ["de gener", "de febrer", "de març", "d'abril", "de maig", "de juny", "de juliol", "d'agost",
           "de setembre", "d'octubre", "de novembre", "de desembre"],
}
PAGES = {
    "en": ("sample-report/index.html", r"It was made by RosmarOps [0-9][0-9.]* on [0-9]+ [A-Z][a-z]+ [0-9]{4}\.",
           "It was made by RosmarOps {v} on {d} {m} {y}."),
    "es": ("es/informe-de-ejemplo/index.html", r"Lo generó RosmarOps [0-9][0-9.]* el [0-9]+ de [a-z]+ de [0-9]{4}\.",
           "Lo generó RosmarOps {v} el {d} de {m} de {y}."),
    "ca": ("ca/informe-dexemple/index.html",
           r"El va generar RosmarOps [0-9][0-9.]* el [0-9]+ (?:de |d'|d&#x27;)[a-zç]+ de [0-9]{4}\.",
           "El va generar RosmarOps {v} el {d} {m} de {y}."),
}
DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2}) \d{2}:\d{2} · ")


def sentences(version, year, month, day):
    v = version.strip().lstrip("v")
    return {lang: PAGES[lang][2].format(v=v, d=day, m=MONTHS[lang][month - 1], y=year) for lang in PAGES}


def run(site):
    site = pathlib.Path(site)
    version = (site / "sample-report/VERSION").read_text(encoding="utf-8")
    m = DATE.search((site / "sample-report/sample-report.en.html").read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no run date in the header of sample-report.en.html")
    new = sentences(version, int(m.group(1)), int(m.group(2)), int(m.group(3)))
    for lang, (path, pattern, _) in PAGES.items():
        p = site / path
        text = p.read_text(encoding="utf-8")
        text, n = re.subn(pattern, lambda _m: new[lang], text)
        if n == 0:
            raise SystemExit(f"{path}: version sentence not found")
        p.write_text(text, encoding="utf-8")
        print(f"{path}: {n} × {new[lang]}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "site")
