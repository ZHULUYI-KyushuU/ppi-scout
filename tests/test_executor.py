import json
from pathlib import Path
import tempfile
import unittest

from ppi_scout.executor import execute_prepared, prepare_workspace, run_manifest


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

    def test_resume_skips_tasks_already_marked_complete(self) -> None:
        manifest = {
            "prediction_jobs": [
                {
                    "id": "wt",
                    "chains": [
                        {"id": "A", "sequence": "ACDEFG"},
                        {"id": "B", "sequence": "WQQL"},
                    ],
                },
                {
                    "id": "mutant",
                    "chains": [
                        {"id": "A", "sequence": "ACDEFG"},
                        {"id": "B", "sequence": "AQQL"},
                    ],
                },
            ]
        }

        class FakeBackend:
            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def run(self, argv, *, live, log_path, stream):
                self.calls.append(argv)
                return {"status": "complete", "argv": argv, "returncode": 0}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = prepare_workspace(manifest, root)
            (root / "status.json").write_text(
                json.dumps(
                    {
                        "status": "interrupted",
                        "tasks": {"wt": {"status": "complete", "returncode": 0}},
                    }
                ),
                encoding="utf-8",
            )
            backend = FakeBackend()
            result = execute_prepared(
                tasks,
                root,
                live=True,
                backend=backend,
                resume=True,
                stream=True,
            )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["skipped_on_resume"], ["wt"])
        self.assertEqual(len(backend.calls), 1)

    def test_resume_refuses_changed_manifest(self) -> None:
        first = {
            "name": "first",
            "chains": [
                {"id": "A", "sequence": "ACDEFG"},
                {"id": "B", "sequence": "WQQL"},
            ],
        }
        changed = {
            **first,
            "chains": [
                {"id": "A", "sequence": "ACDEFG"},
                {"id": "B", "sequence": "AQQL"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare_workspace(first, root, resume=True)
            with self.assertRaisesRegex(ValueError, "different panel manifest"):
                prepare_workspace(changed, root, resume=True)


if __name__ == "__main__":
    unittest.main()
