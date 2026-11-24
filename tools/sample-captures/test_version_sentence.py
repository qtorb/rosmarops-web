import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import version_sentence as vs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


class VersionSentence(unittest.TestCase):
    def test_sentences(self):
        s = vs.sentences("v0.18.0\n", 2026, 11, 22)
        self.assertEqual(s["en"], "It was made by RosmarOps 0.18.0 on 22 November 2026.")
        self.assertEqual(s["es"], "Lo generó RosmarOps 0.18.0 el 22 de noviembre de 2026.")
        self.assertEqual(s["ca"], "El va generar RosmarOps 0.18.0 el 22 de novembre de 2026.")
        self.assertEqual(vs.sentences("v1.0.0", 2027, 4, 3)["ca"], "El va generar RosmarOps 1.0.0 el 3 d'abril de 2027.")

    def test_run_on_a_copy_of_the_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = pathlib.Path(tmp)
            for lang, (path, _, _) in vs.PAGES.items():
                (site / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / "site" / path, site / path)
            (site / "sample-report/VERSION").write_text("v0.18.0\n")
            (site / "sample-report/sample-report.en.html").write_text("<p>2026-11-22 21:25 · Windows · 5 agents</p>")
            vs.run(site)
            en = (site / "sample-report/index.html").read_text()
            self.assertIn("It was made by RosmarOps 0.18.0 on 22 November 2026.", en)
            self.assertNotIn("0.12.1", en)
            self.assertNotIn("0.12.1", (site / "es/informe-de-ejemplo/index.html").read_text())
            self.assertNotIn("0.12.1", (site / "ca/informe-dexemple/index.html").read_text())


if __name__ == "__main__":
    unittest.main()
