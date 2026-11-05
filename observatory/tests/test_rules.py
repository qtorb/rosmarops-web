"""GTM-89: the daily task reads its rules from observatory/rules/daily.md; it must exist and carry R1 to R13.

Run from the repository root:  python3 -m unittest observatory/tests/test_rules.py
"""

import re
import unittest
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / "rules" / "daily.md"


class Rules(unittest.TestCase):
    def test_file_and_rules(self):
        self.assertTrue(RULES.is_file(), "observatory/rules/daily.md is missing")
        text = RULES.read_text(encoding="utf-8")
        for i in range(1, 14):
            self.assertRegex(text, re.compile(rf"^R{i} \S", re.M), f"R{i} missing")
        self.assertIn("## Reglas de la sinopsis diaria (R1–R13)", text)
        self.assertIn("## Registro de cambios (GTM-89)", text)
        self.assertIn("## Fuente de datos (GTM-90)", text)
        self.assertLess(text.index("## Fuente de datos (GTM-90)"), text.index("## Reglas de la sinopsis diaria (R1–R13)"))
        self.assertNotIn("«Revisado» del resumen", text)
        self.assertIn("R11 Alcance: solo los agentes de observatory/data/agents/*.json", text)


if __name__ == "__main__":
    unittest.main()
