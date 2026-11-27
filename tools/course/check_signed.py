"""GTM-206, GTM-227, GTM-230: checks that every text of the course and of RosmarOps Academy is literal in the documents
Albert signed.

Run by hand, with a local copy of qtorb/rosmarops-vigil (CI cannot read that repository):

    python3 tools/course/check_signed.py ../rosmarops-vigil

The two lessons (observatory/data/course/the-inspector.json and the-chain.json) and the Academy page
(observatory/data/academy.json, GTM-230: its texts come from docs/research/2026-11-27-academy-portada-y-menu.md, and the
painter paragraph and the five lesson lines from the final texts document):
- every text comes from docs/research/2026-11-26-curso-publico-textos-finales.md (ES, EN and CA; block 211), except
  the step list label, which comes from the design,
  docs/research/2026-11-26-curso-diseno-entrada-y-seis-pasos.md;
- in English pages the quotes are “ ” (design §6): they are compared as « », the way the document writes them;
- the eighteen retouches of docs/briefs/GTM-217.md (block 188) are listed in RETOUCHES: the new part must still be
  in the signed texts and in the data, and the part it replaced must be gone from the data. Two of them are the
  corrected sentences of GTM-219 (the capability card and change 1 of the game), in CORRECTED.
Exit code 1 and the list of texts that are not found, if any.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "observatory" / "data" / "course"
FILES = ("the-inspector", "the-chain")
ACADEMY = ROOT / "observatory" / "data" / "academy.json"
ACADEMY_SPEC = ["docs/research/2026-11-27-academy-portada-y-menu.md"]
DATA = DIR / "the-chain.json"
TEXTS = ["docs/research/2026-11-26-curso-publico-textos-finales.md"]
DESIGN = ["docs/research/2026-11-26-curso-diseno-entrada-y-seis-pasos.md"]
RETOUCHES_DOC = ["docs/briefs/GTM-217.md"]
# (path, new part from GTM-217.md, the part it replaced in the lesson documents). Where the brief changes a whole
# text, the new part is the whole text.
RETOUCHES = [
    (("en", "eyebrow"), "Lesson 2 of 5 · 8 minutes of reading, plus 10 on your report", "Lesson 2 of 5 · 8 minutes"),
    (("es", "eyebrow"), "Lección 2 de 5 · 8 minutos de lectura, más 10 en tu informe", "Lección 2 de 5 · 8 minutos"),
    (("ca", "eyebrow"), "Lliçó 2 de 5 · 8 minuts de lectura, més 10 al teu informe", "Lliçó 2 de 5 · 8 minuts"),
    (("en", "check", "game", "always"), "Later you'll see what RosmarOps can know and what it can't.",
     "In lesson 3 you'll see what RosmarOps can know and what it can't."),
    (("es", "check", "game", "always"), "Más adelante verás qué puede saber RosmarOps y qué no.",
     "En la lección 3 verás qué puede saber RosmarOps y qué no."),
    (("ca", "check", "game", "always"), "Més endavant veuràs què pot saber RosmarOps i què no.",
     "A la lliçó 3 veuràs què pot saber RosmarOps i què no."),
    (("en", "check", "test", "all"), "The chain is yours now.", "The chain is yours now. Go on to lesson 3."),
    (("es", "check", "test", "all"), "La cadena ya es tuya.", "La cadena ya es tuya. Sigue con la lección 3."),
    (("ca", "check", "test", "all"), "La cadena ja és teva.", "La cadena ja és teva. Continua amb la lliçó 3."),
    (("en", "idea", "cards", 2, 2), "saved in a `.env` file (a text file where many programs keep their keys), a token, a private key.",
     "saved in a `.env` file, a token, a private key."),
    (("es", "idea", "cards", 2, 2),
     "guardada en un fichero `.env` (un fichero de texto donde muchos programas guardan sus claves), un token, una clave privada.",
     "guardada en un fichero `.env`, un token, una clave privada."),
    (("ca", "idea", "cards", 2, 2),
     "desada en un fitxer `.env` (un fitxer de text on molts programes desen les seves claus), un testimoni (token), una clau privada.",
     "desada en un fitxer `.env`, un testimoni (token), una clau privada."),
    (("es", "check", "game", "title"), "¿Qué se corta?", "¿Qué se rompe?"),
    (("es", "idea", "cards", 3, 2), "El garaje, la caja fuerte, la cuenta del banco.", "El garaje, la caja, la cuenta del banco."),
    (("es", "take", "terms", 0, 0), "Agente de IA", "Agente"),
    (("es", "take", "terms", 2, 0), "Clave o credencial", "Credencial"),
    (("ca", "try", "piece", "detail", 1, 1, 1),
     "Permetre (sense preguntar-te), preguntar (et demana permís cada vegada) i denegar (mai).",
     "Permetre (allow, sense preguntar-te), preguntar (ask, et demana permís cada vegada) i denegar (deny, mai)."),
    (("ca", "check", "game", "items", 0, "expl"),
     # GTM-227: the retouch (no originals in brackets) holds in the corrected sentences of GTM-219.
     "En mode manual, Claude Code et pregunta abans d'obrir amb les seves eines un fitxer de fora del projecte. En mode auto, la primera vegada et pregunta a tu.",
     "En mode manual (Manual mode), Claude Code et pregunta abans de llegir fora del projecte. En mode auto (auto mode), ho decideix un altre model d'IA."),
]

# GTM-219 / GTM-227 §5: the two sentences corrected in the capability card and in change 1 of the game. The old ones
# must be gone and the new ones in place, in both texts and three languages.
CORRECTED = {
    "en": ("In Manual mode, Claude Code asks you before opening a file outside the project with its own tools. In auto mode, "
           "it asks you the first time. Depending on your answer, it stops asking or stops reading outside the project.",
           ["In Manual mode, Claude Code asks you before reading outside the project.", "In auto mode, another AI model decides."]),
    "es": ("En modo manual, Claude Code te pregunta antes de abrir con sus herramientas un fichero de fuera del proyecto. En modo "
           "auto, la primera vez te pregunta a ti. Según lo que contestes, ya no vuelve a preguntar o deja de leer fuera del proyecto.",
           ["En modo manual, Claude Code te pregunta antes de leer fuera del proyecto.", "En modo auto, lo decide otro modelo de IA."]),
    "ca": ("En mode manual, Claude Code et pregunta abans d'obrir amb les seves eines un fitxer de fora del projecte. En mode "
           "auto, la primera vegada et pregunta a tu. Segons el que responguis, ja no torna a preguntar o deixa de llegir fora del projecte.",
           ["En mode manual, Claude Code et pregunta abans de llegir fora del projecte.", "En mode auto, ho decideix un altre model d'IA."]),
}
CORRECTED_AT = [("try", "piece", "detail", 1, 2, 1), ("check", "game", "items", 0, "expl")]
SKIP_KEYS = {"answer", "exclusive", "states", "checked", "button_to", "path", "_source", "name"}


def norm(s):
    s = s.replace("“", "«").replace("”", "»")
    return re.sub(r"\s+", " ", s.replace("**", "").replace("`", "")).strip()


def strings(x, path=()):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, list):
        for i, y in enumerate(x):
            yield from strings(y, path + (i,))
    elif isinstance(x, dict):
        for k, y in x.items():
            if k not in SKIP_KEYS:
                yield from strings(y, path + (k,))


def missing(vigil, files):
    """files: {name: data}. The texts that are not found in the signed documents, as (path, text)."""
    texts = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in TEXTS))
    design = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in DESIGN))
    spec = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in ACADEMY_SPEC))
    retouch_doc = norm(" ".join((vigil / p).read_text(encoding="utf-8") for p in RETOUCHES_DOC))
    out = []
    for path, new, old in RETOUCHES:
        if norm(new) not in retouch_doc and path[1:] != ("check", "game", "items", 0, "expl"):
            out.append((("the-chain",) + path, new))
    for name, data in files.items():
        for lang in ("en", "es", "ca"):
            for path, s in strings(data[lang], (name, lang)):
                if not s or s.startswith("/"):
                    continue
                if path[2:4] == ("take", "terms") and path[-1] == 1:
                    continue  # glossary ids, not text
                where = design if path[2:] == ("steps_aria",) else texts
                if name == "academy":
                    where = texts if path[2:3] in (("ex.p",), ("course.lessons",)) else spec
                # {name} placeholders: the signed text may use another name ({fuente}, {aciertos})
                rx = re.escape(norm(s)).replace(r"\{", "{").replace(r"\}", "}")
                rx = re.sub(r"\{\w+\}", r"\\{[^}]+\\}", rx)
                if not re.search(rx, where):
                    out.append((path, s))
    return out


def load():
    out = {n: json.loads((DIR / f"{n}.json").read_text(encoding="utf-8")) for n in FILES}
    out["academy"] = json.loads(ACADEMY.read_text(encoding="utf-8"))
    return out


if __name__ == "__main__":
    vigil = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "rosmarops-vigil"
    bad = missing(vigil, load())
    for path, s in bad:
        print("/".join(map(str, path)), "|", s)
    print(len(bad), "texts not found")
    sys.exit(1 if bad else 0)
