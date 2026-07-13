import json
from pathlib import Path
import tempfile
import unittest

from ppi_scout.executor import prepare_workspace, run_manifest


class ExecutorTests(unittest.TestCase):
    def test_prepare_workspace_writes_auditable_files(self) -> None:
        manifest = {
            "name": "example",
            "chains": [
                {"id": "A", "sequence": "ACDEFG", "msa": "empty"},
                {"id": "B", "sequence": "WQQL", "msa": "empty"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = prepare_workspace(manifest, root)
            self.assertEqual(len(tasks), 1)
            self.assertTrue((root / "manifest.resolved.json").exists())
            self.assertTrue((root / "plan.json").exists())
            self.assertTrue((root / "inputs" / "example.yaml").exists())

    def test_remote_msa_requires_explicit_permission(self) -> None:
        manifest = {
            "name": "remote",
            "remote_msa": True,
            "chains": [
                {"id": "A", "sequence": "ACDEFG", "msa": "remote"},
                {"id": "B", "sequence": "WQQL", "msa": "empty"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prepare_workspace(manifest, Path(tmp))

    def test_manifest_run_defaults_to_dry_run(self) -> None:
        manifest = {
            "name": "safe",
            "chains": [
                {"id": "A", "sequence": "ACDEFG"},
                {"id": "B", "sequence": "WQQL"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "job.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            result = run_manifest(path, root / "run")
        self.assertEqual(result["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
