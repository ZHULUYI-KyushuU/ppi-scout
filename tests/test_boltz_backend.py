from pathlib import Path
import tempfile
import unittest

from ppi_scout.backends.boltz2 import Boltz2Backend


class BoltzBackendTests(unittest.TestCase):
    def test_compile_input_with_chain_specific_msa(self) -> None:
        payload = Boltz2Backend.compile_input(
            [
                {"id": "A", "sequence": "ACDEFG", "msa": "/tmp/receptor.a3m"},
                {"id": "B", "sequence": "WQQL", "msa": "empty"},
            ]
        )
        self.assertEqual(payload["sequences"][0]["protein"]["msa"], "/tmp/receptor.a3m")
        self.assertEqual(payload["sequences"][1]["protein"]["msa"], "empty")

    def test_invalid_sequence_fails_before_execution(self) -> None:
        with self.assertRaises(ValueError):
            Boltz2Backend.compile_input(
                [
                    {"id": "A", "sequence": "ACD*"},
                    {"id": "B", "sequence": "WQQL"},
                ]
            )

    def test_dry_run_never_executes(self) -> None:
        backend = Boltz2Backend(executable="definitely-not-installed-boltz")
        with tempfile.TemporaryDirectory() as tmp:
            argv = backend.command(Path(tmp) / "job.yaml", Path(tmp) / "out")
            result = backend.run(argv, live=False)
        self.assertEqual(result["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
