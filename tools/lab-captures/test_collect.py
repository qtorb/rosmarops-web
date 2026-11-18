"""Tests for tools/lab-captures/collect.py and the daily flow .github/workflows/lab-captures.yml (GTM-183): a lab release
is imported to the same places and with the same rules as GTM-182, and no PR is opened for a release already imported.

Run from the repository root:  python3 -m unittest tools/lab-captures/test_collect.py
"""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("collect_lab", HERE / "collect.py")
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)
FLOW = ROOT / ".github" / "workflows" / "lab-captures.yml"


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Import(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = Path(self.tmp.name)
        self.rel, self.manifest, self.images = t / "release", t / "data" / "lab" / "manifest.json", t / "sandbox-lab"
        self.rel.mkdir()
        files = {"a-1-fichero1-despues.png": b"PNG-a1", "a-1-fichero1-despues.txt": b"txt", "a-3-ls-antes.png": b"PNG-ls",
                 "a-3-red-antes.png": b"PNG-red", "a-3-red-antes.txt": b"txt2", "a-3-x-despues.png": b"PNG-x", "meta.json": b"{}"}
        for n, b in files.items():
            (self.rel / n).write_bytes(b)
        h = {n: sha(b) for n, b in files.items()}
        self.m = {"schema": 1, "release": "lab-test-1", "meta": {"meta.json": h["meta.json"]}, "entries": [
            {"agent": "a", "test": "fichero1", "result": "concluyente", "command": "cat f",
             "files": {"a-1-fichero1-despues.png": h["a-1-fichero1-despues.png"], "a-1-fichero1-despues.txt": h["a-1-fichero1-despues.txt"]}},
            {"agent": "a", "test": "ls", "result": "concluyente", "command": "ls ~", "files": {"a-3-ls-antes.png": h["a-3-ls-antes.png"]}},
            {"agent": "a", "test": "red", "result": "inesperado", "command": "curl -I https://example.com",
             "files": {"a-3-red-antes.png": h["a-3-red-antes.png"], "a-3-red-antes.txt": h["a-3-red-antes.txt"]}},
            {"agent": "a", "test": "x", "result": "no_concluyente", "command": "x", "files": {"a-3-x-despues.png": h["a-3-x-despues.png"]}},
        ]}
        self.raw = json.dumps(self.m, indent=2).encode()
        (self.rel / "manifest.json").write_bytes(self.raw)

    def run_import(self, tag="lab-test-1"):
        return collect.import_release(str(self.rel), tag, self.manifest, self.images)

    def test_same_places_and_rules_as_gtm182(self):
        self.images.mkdir()
        (self.images / "old-release.png").write_bytes(b"old")
        kept, unexpected = self.run_import()
        self.assertEqual(self.manifest.read_bytes(), self.raw)  # unchanged
        self.assertEqual(sorted(p.name for p in self.images.iterdir()), ["a-1-fichero1-despues.png", "a-3-ls-antes.png"])
        self.assertEqual(sorted(kept), ["a-1-fichero1-despues.png", "a-3-ls-antes.png"])
        self.assertEqual([e["test"] for e in unexpected], ["red"])
        self.assertEqual(collect.current(self.manifest), "lab-test-1")

    def test_a_sha256_mismatch_writes_nothing(self):
        (self.rel / "a-3-red-antes.txt").write_bytes(b"changed")  # even a file that is not published
        with self.assertRaises(SystemExit) as e:
            self.run_import()
        self.assertIn("SHA-256 mismatch", str(e.exception))
        self.assertFalse(self.manifest.exists())
        self.assertFalse(self.images.exists())

    def test_missing_unsafe_or_other_release(self):
        with self.assertRaises(SystemExit):
            self.run_import("lab-test-2")
        (self.rel / "meta.json").unlink()
        with self.assertRaises(SystemExit):
            self.run_import()
        self.m["entries"][1]["files"] = {"../x.png": "0" * 64}
        (self.rel / "manifest.json").write_text(json.dumps(self.m))
        with self.assertRaises(SystemExit):
            self.run_import()

    def test_current(self):
        self.assertIsNone(collect.current(Path(self.tmp.name) / "none.json"))
        self.assertEqual(collect.current(), "lab-20261118-2")  # the release GTM-182 imported


class Flow(unittest.TestCase):
    text = FLOW.read_text(encoding="utf-8")

    def test_imports_to_the_guide_places(self):
        self.assertIn("DEST: site/assets/sandbox-lab\n", self.text)
        self.assertNotIn("sandbox/lab", self.text)
        self.assertIn('python3 tools/lab-captures/collect.py import "$dir" "$TAG"', self.text)
        self.assertIn("python3 observatory/build.py", self.text)
        self.assertIn('git add -A "$DEST" observatory/data/lab site', self.text)
        self.assertFalse((ROOT / "site" / "assets" / "sandbox" / "lab").exists())

    def test_no_pr_for_the_release_already_imported(self):
        self.assertIn("current=$(python3 tools/lab-captures/collect.py current)", self.text)
        i = self.text.index('if [ "$tag" = "$current" ]; then')
        self.assertIn('echo "new=false" >> "$GITHUB_OUTPUT"; exit 0', self.text[i:i + 200])
        self.assertNotIn("VERSION", self.text)


if __name__ == "__main__":
    unittest.main()
