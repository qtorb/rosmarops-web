"""GTM-206: checks that every text of a course lesson is literal in the documents Albert signed.

Run by hand, with a local copy of qtorb/rosmarops-vigil (CI cannot read that repository):

    python3 tools/course/check_signed.py ../rosmarops-vigil

Lesson 2 («The chain»), observatory/data/course/the-chain.json:
- close.footer comes from docs/briefs/GTM-215.md (block 178, B.5);
- the eight retouches of docs/briefs/GTM-217.md (block 188) are listed in RETOUCHES: the new part must be in
  GTM-217.md, and the text with the old part put back must be in the signed lesson documents;
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
RETOUCHES_DOC = ["docs/briefs/GTM-217.md"]
# (path, new part from GTM-217.md, the part it replaced in the lesson documents). Where the brief changes a whole
# text, the new part is the whole text.
RETOUCHES = [
    (("en", "eyebrow"), "Lesson 2 of 5 · 8 minutes of reading, plus 10 on your report", "Lesson 2 of 5 · 8 minutes"),
    (("es", "eyebrow"), "Lección 2 de 5 · 8 minutos de lectura, más 10 en tu informe", "Lección 2 de 5 · 8 minutos"),
    (("ca", "eyebrow"), "Lliçó 2 de 5 · 8 minuts de lectura, més 10 al teu informe", "Lliçó 2 de 5 · 8 minuts"),
    (("en", "game", "always"), "Later you'll see what RosmarOps can know and what it can't.",
     "In lesson 3 you'll see what RosmarOps can know and what it can't."),
    (("es", "game", "always"), "Más adelante verás qué puede saber RosmarOps y qué no.",
     "En la lección 3 verás qué puede saber RosmarOps y qué no."),
    (("ca", "game", "always"), "Més endavant veuràs què pot saber RosmarOps i què no.",
     "A la lliçó 3 veuràs què pot saber RosmarOps i què no."),
    (("en", "test", "all"), "The chain is yours now.", "The chain is yours now. Go on to lesson 3."),
    (("es", "test", "all"), "La cadena ya es tuya.", "La cadena ya es tuya. Sigue con la lección 3."),
    (("ca", "test", "all"), "La cadena ja és teva.", "La cadena ja és teva. Continua amb la lliçó 3."),
    (("en", "idea", "cards", 2, 2), "saved in a `.env` file (a text file where many programs keep their keys), a token, a private key.",
     "saved in a `.env` file, a token, a private key."),
    (("es", "idea", "cards", 2, 2),
     "guardada en un fichero `.env` (un fichero de texto donde muchos programas guardan sus claves), un token, una clave privada.",
     "guardada en un fichero `.env`, un token, una clave privada."),
    (("ca", "idea", "cards", 2, 2),
     "desada en un fitxer `.env` (un fitxer de text on molts programes desen les seves claus), un testimoni (token), una clau privada.",
     "desada en un fitxer `.env`, un testimoni (token), una clau privada."),
    (("es", "game", "title"), "¿Qué se corta?", "¿Qué se rompe?"),
    (("es", "idea", "cards", 3, 2), "El garaje, la caja fuerte, la cuenta del banco.", "El garaje, la caja, la cuenta del banco."),
    (("es", "close", "terms", 0, 0), "Agente de IA", "Agente"),
    (("es", "close", "terms", 2, 0), "Clave o credencial", "Credencial"),
    (("ca", "piece", "detail", 1, 1, 1),
     "Permetre (sense preguntar-te), preguntar (et demana permís cada vegada) i denegar (mai).",
     "Permetre (allow, sense preguntar-te), preguntar (ask, et demana permís cada vegada) i denegar (deny, mai)."),
    (("ca", "game", "items", 0, "expl"),
     "En mode manual, Claude Code et pregunta abans de llegir fora del projecte. En mode auto, ho decideix un altre model d'IA.",
     "En mode manual (Manual mode), Claude Code et pregunta abans de llegir fora del projecte. En mode auto (auto mode), ho decideix un altre model d'IA."),
]


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
    retouch_doc = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in RETOUCHES_DOC))
    retouch = {path: (new, old) for path, new, old in RETOUCHES}
    out = []
    for lang in ("en", "es", "ca"):
        for path, s in strings(data[lang], (lang,)):
            if not s or s.startswith("/"):
                continue
            if path[1:3] == ("close", "terms") and path[-1] == 1:
                continue  # glossary ids, not text
            where = footer if path[1:] == ("close", "footer") else lesson
            if path in retouch:
                new, old = retouch[path]
                if new not in s or norm(new) not in retouch_doc:
                    out.append((path, s))
                    continue
                s = s.replace(new, old)  # the rest of the text must still be the signed one
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
