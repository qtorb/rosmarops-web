"""Tests for wp/mu-plugins/rosmarops-categories-gtm94.php, the one-time category migration (GTM-94).

Run from the repository root:  python3 -m unittest wp/tests/test_categories_gtm94.py   (needs php on PATH)
"""

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ES = "https://rosmarops.com/es"
ES_MOVES = {
    "modo-auto-claude-code-que-puede-leer": "modos-y-aprobaciones",
    "que-claves-puede-leer-tu-agente-de-ia": "claves-de-api-y-env",
    "puede-un-agente-de-ia-cambiar-la-configuracion-de-otro": "claude-md-agents-md-y-reglas",
    "antes-de-decirle-a-tu-agente-que-lo-instale": "servidores-mcp",
    "servidores-mcp-de-markdown-que-buscaban-credenciales-en-la-nube": "servidores-mcp",
    "herramientas-que-revisan-a-que-llegan-tus-agentes-de-ia": "nota-de-exposicion",
}


def es_db():
    terms = [
        {"term_id": 1, "name": "Novedades de RosmarOps", "slug": "novedades-de-rosmarops", "description": ""},
        {"term_id": 2, "name": "Qué puede hacer tu agente", "slug": "que-puede-hacer-tu-agente", "description": ""},
        {"term_id": 3, "name": "Metodología", "slug": "metodologia", "description": ""},
        {"term_id": 9, "name": "SEO Adversarial", "slug": "seo-adversarial", "description": ""},
    ]
    posts, n = [], 100
    for slug in ES_MOVES:
        n += 1
        posts.append({"ID": n, "post_name": slug, "post_status": "publish", "cats": [2]})
    for slug in ("lo-que-no-se-leyo-no-cuenta-como-limpio", "como-funciona-la-nota-de-exposicion", "mi-maquina-saco-un-18-de-100"):
        n += 1
        posts.append({"ID": n, "post_name": slug, "post_status": "publish", "cats": [3]})
    posts.append({"ID": 200, "post_name": "rosmarops-0-4-0", "post_status": "publish", "cats": [1]})
    posts.append({"ID": 300, "post_name": "seo-legacy", "post_status": "draft", "cats": [9]})
    return {"options": {"default_category": 1}, "terms": terms, "posts": posts, "termmeta": {}}


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbf = Path(self.tmp.name) / "db.json"
        self.content = Path(self.tmp.name) / "wp-content"
        self.content.mkdir()

    def run_once(self, db=None, home=ES):
        if db is not None:
            self.dbf.write_text(json.dumps(db, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, GTM94_DB=str(self.dbf), GTM94_CONTENT=str(self.content))
        p = subprocess.run(["php", str(TESTS / "gtm94-stub.php"), "run", home], env=env, capture_output=True, text=True, check=True)
        return json.loads(p.stdout), json.loads(self.dbf.read_text(encoding="utf-8"))

    @staticmethod
    def term(db, slug):
        return next((t for t in db["terms"] if t["slug"] == slug), None)

    @staticmethod
    def post(db, slug):
        return next(p for p in db["posts"] if p["post_name"] == slug)

    def test_first_run(self):
        log, db = self.run_once(es_db())
        nota = self.term(db, "nota-de-exposicion")
        self.assertEqual((nota["term_id"], nota["name"]), (3, "Nota de exposición"))
        self.assertTrue(nota["description"].startswith("Cómo se calcula la nota de 0 a 100"))
        self.assertIsNone(self.term(db, "metodologia"))
        modos = self.term(db, "modos-y-aprobaciones")
        self.assertEqual(modos["description"], "Qué decide tu agente sin preguntarte y qué te pide aprobar: modo auto, listas de "
                         "permitidos y sandbox, agente por agente. Con los cambios de cada versión, fechados y con su fuente.")
        self.assertIn("dónde guardan los agentes las suyas", self.term(db, "claves-de-api-y-env")["description"])
        for slug, cat in ES_MOVES.items():
            self.assertEqual(self.post(db, slug)["cats"], [self.term(db, cat)["term_id"]], slug)
        self.assertEqual(self.post(db, "mi-maquina-saco-un-18-de-100")["cats"], [3])
        self.assertEqual(self.post(db, "rosmarops-0-4-0")["cats"], [1])
        self.assertEqual(len(db["posts"]), 11)  # no post deleted
        self.assertIsNone(self.term(db, "que-puede-hacer-tu-agente"))
        self.assertIsNotNone(self.term(db, "seo-adversarial"))
        for slug in ("modos-y-aprobaciones", "claves-de-api-y-env", "claude-md-agents-md-y-reglas", "servidores-mcp"):
            self.assertEqual(db["termmeta"][str(self.term(db, slug)["term_id"])]["autodescription-term-settings"], {"noindex": 1}, slug)
        self.assertNotIn("3", db["termmeta"])
        self.assertEqual(sum(l.startswith("B done") for l in log), 4)
        self.assertEqual(sum(l.startswith("C done") for l in log), 6)
        self.assertIn("D done: empty category que-puede-hacer-tu-agente deleted (no post deleted)", log)
        self.assertFalse([l for l in log if "failed" in l or "skipped" in l], log)
        self.assertEqual((self.content / "rosmarops-private" / "gtm94-es.log").read_text(encoding="utf-8").splitlines(), log)
        self.assertEqual((self.content / "rosmarops-private" / ".htaccess").read_text(), "Require all denied\n")
        self.assertIn("rosmarops_gtm94_done", db["options"])
        self.assertNotIn("rosmarops_gtm94_lock", db["options"])

    def test_second_run_changes_nothing(self):
        _, first = self.run_once(es_db())
        log, second = self.run_once()
        self.assertIsNone(log)
        self.assertEqual(first, second)

    def test_missing_and_misplaced_posts_are_left_alone(self):
        db = es_db()
        db["posts"] = [p for p in db["posts"] if p["post_name"] != "que-claves-puede-leer-tu-agente-de-ia"]
        self.post(db, "modo-auto-claude-code-que-puede-leer")["cats"] = [1]  # not where the table expects
        db["posts"].append({"ID": 400, "post_name": "unexpected", "post_status": "publish", "cats": [2]})
        log, out = self.run_once(db)
        self.assertIn("C skipped: published post que-claves-puede-leer-tu-agente-de-ia not found", log)
        self.assertIn("C skipped: modo-auto-claude-code-que-puede-leer is not in que-puede-hacer-tu-agente; left as it is", log)
        self.assertEqual(self.post(out, "modo-auto-claude-code-que-puede-leer")["cats"], [1])
        self.assertIn("D skipped: que-puede-hacer-tu-agente still has posts; not deleted", log)
        self.assertIsNotNone(self.term(out, "que-puede-hacer-tu-agente"))
        self.assertEqual(self.post(out, "unexpected")["cats"], [2])
        self.assertEqual(sum(l.startswith("C done") for l in log), 4)

    def test_existing_target_category_is_not_renamed_twice(self):
        db = es_db()
        db["terms"].append({"term_id": 20, "name": "Servidores MCP", "slug": "servidores-mcp", "description": "old"})
        log, out = self.run_once(db)
        self.assertIn("B skipped: category servidores-mcp already exists", log)
        self.assertEqual(self.term(out, "servidores-mcp")["description"], "old")
        self.assertEqual(self.post(out, "antes-de-decirle-a-tu-agente-que-lo-instale")["cats"], [20])

    def test_recent_lock_waits(self):
        db = es_db()
        db["options"]["rosmarops_gtm94_lock"] = 9999999999
        log, out = self.run_once(db)
        self.assertIsNone(log)
        self.assertIsNotNone(self.term(out, "metodologia"))

    def test_other_sites(self):
        self.assertEqual(self.run_once(es_db(), home="https://example.com")[0], None)
        db = {"options": {"default_category": 1}, "termmeta": {}, "terms": [
            {"term_id": 1, "name": "RosmarOps news", "slug": "field-notes", "description": ""},
            {"term_id": 2, "name": "What your agent can do", "slug": "ai-agents", "description": ""},
            {"term_id": 3, "name": "Methodology", "slug": "methodology", "description": ""}],
            "posts": [{"ID": 1, "post_name": "which-keys-can-your-ai-coding-agent-read", "post_status": "publish", "cats": [2]}]}
        log, out = self.run_once(db, home="https://rosmarops.com/")
        self.assertEqual(self.term(out, "agent-posture-score")["description"],
                         "How RosmarOps calculates the 0–100 score it gives each agent, what counts and what doesn't, and why what wasn't read doesn't count as clean.")
        self.assertEqual(out["posts"][0]["cats"], [self.term(out, "api-keys-and-env-files")["term_id"]])
        self.assertIn("C skipped: published post claude-code-auto-mode-what-it-can-read not found", log)
        ca = copy.deepcopy(db)
        ca["terms"] = [{"term_id": 2, "name": "Què pot fer el teu agent", "slug": "agents-ia", "description": ""},
                       {"term_id": 3, "name": "Metodologia", "slug": "metodologia", "description": ""}]
        ca["posts"] = []
        ca["options"]["default_category"] = 2
        log, out = self.run_once(ca, home="https://rosmarops.com/ca")
        self.assertEqual(self.term(out, "nota-dexposicio")["name"], "Nota d'exposició")
        self.assertIn("D skipped: agents-ia is the site's default category; not deleted", log)


if __name__ == "__main__":
    unittest.main()
