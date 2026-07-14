import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_helixfold3_panel.py"
MANIFEST = ROOT / "examples" / "helixfold3-yta7-panel.json"


class HelixFold3PanelTests(unittest.TestCase):
    def run_validator(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_authoritative_manifest_is_valid(self) -> None:
        result = self.run_validator(MANIFEST)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "VALID")

    def test_sequence_tampering_is_rejected(self) -> None:
        panel = json.loads(MANIFEST.read_text(encoding="utf-8"))
        panel["jobs"][0]["entity_b"]["sequence"] = "A" * 24
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(json.dumps(panel), encoding="utf-8")
            result = self.run_validator(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("INVALID:", result.stderr)

    def test_jobs_cannot_be_combined(self) -> None:
        panel = json.loads(MANIFEST.read_text(encoding="utf-8"))
        panel["design"]["combine_variants_in_one_complex"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "combined.json"
            path.write_text(json.dumps(panel), encoding="utf-8")
            result = self.run_validator(path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not be combined", result.stderr)


if __name__ == "__main__":
    unittest.main()
