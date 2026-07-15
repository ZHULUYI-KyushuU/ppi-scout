from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ppi_scout.panel_execution import build_panel_manifest


class PanelExecutionTests(unittest.TestCase):
    RECEPTOR = "MKSTFKSEYPFEKRKAESERIADRFKNRIPVICEKAEKSDIPEIDKRKYLVPADLTVGQFVYVIRKRIMLPPEKAIFIFVNDTLPPTAALMSAIYQEHKDKDGFLYVTYSGENTFGR"
    PEPTIDE = "KINYAEIEKVFDFLEDDQVMDKDE"

    @classmethod
    def job(cls) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "name": "atg8-yta7-fdfl",
            "inputs": {
                "organism": "Saccharomyces cerevisiae S288c",
                "proteins": [
                    {"id": "A", "name": "Atg8", "sequence": cls.RECEPTOR},
                    {"id": "B", "name": "Yta7-43-66", "sequence": cls.PEPTIDE},
                ],
            },
            "routing": {
                "route": "motif_peptide",
                "selected_region": [11, 14],
                "selected_motif": "FDFL",
            },
            "hypothesis": {
                "motif_owner": "B",
                "motif_sequence": "FDFL",
                "motif_region": [11, 14],
                "motif_context": "exposed",
                "receptor_has_motif_pocket": True,
                "coordinate_convention": "1-based inclusive",
            },
        }

    def test_builds_complete_independent_control_panel(self) -> None:
        manifest = build_panel_manifest(
            self.job(),
            windows=(24,),
            design_seed=7,
            prediction_seed=11,
            accelerator="cpu",
            no_kernels=True,
        )

        tasks = manifest["prediction_jobs"]
        self.assertEqual(len(tasks), 10)
        self.assertEqual(
            [task["variant"]["kind"] for task in tasks],
            [
                "wt",
                "anchor_1_to_a",
                "anchor_2_to_a",
                "double_anchor_to_a",
                "core_to_aaaa",
                "reverse_decoy",
                "flank_scramble",
                "clean_scramble",
                "clean_scramble",
                "clean_scramble",
            ],
        )
        self.assertTrue(all(task["chains"][0]["sequence"] == self.RECEPTOR for task in tasks))
        self.assertTrue(all(task["chains"][0]["msa"] == "empty" for task in tasks))
        self.assertTrue(all(task["chains"][1]["msa"] == "empty" for task in tasks))
        self.assertEqual(manifest["msa"]["mode"], "single_sequence")
        self.assertFalse(manifest["privacy"]["external_sequence_upload"])
        self.assertIn("--no_kernels", manifest["engine_args"])
        self.assertIn("11", manifest["engine_args"])

    def test_remote_msa_is_recorded_only_when_explicit(self) -> None:
        manifest = build_panel_manifest(self.job(), windows=(24,), remote_msa=True)
        self.assertEqual(manifest["msa"]["mode"], "remote")
        self.assertTrue(manifest["remote_msa_allowed"])
        self.assertTrue(manifest["privacy"]["sequence_upload_authorized"])
        self.assertTrue(
            all(task["chains"][0]["msa"] == "remote" for task in manifest["prediction_jobs"])
        )

    def test_local_msa_and_remote_msa_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "either --remote-msa or --receptor-msa"):
                build_panel_manifest(
                    self.job(),
                    windows=(24,),
                    remote_msa=True,
                    receptor_msa=str(Path(tmp) / "receptor.a3m"),
                )

    def test_rejects_unreviewed_or_mismatched_job(self) -> None:
        unreviewed = self.job()
        unreviewed["routing"]["route"] = "needs_review"
        with self.assertRaisesRegex(ValueError, "routing.route=motif_peptide"):
            build_panel_manifest(unreviewed, windows=(24,))

        mismatched = self.job()
        mismatched["hypothesis"]["motif_sequence"] = "AAAA"
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_panel_manifest(mismatched, windows=(24,))


if __name__ == "__main__":
    unittest.main()
