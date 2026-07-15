from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ppi_scout.cli import _route_fallback, _safe_job_slug, build_parser, main
from ppi_scout.i18n import Translator, normalize_language


class CLITests(unittest.TestCase):
    SCAN_SEQUENCE = "MSTYQQVADKWQQLDEESGKNPTA"

    @staticmethod
    def fake_scan(sequence: str, flank_size: int = 6) -> dict[str, object]:
        return {
            "scanner": "test AIM/LIR scanner",
            "flank_size": flank_size,
            "candidates": [
                {
                    "candidate_id": "aim-001",
                    "rank": 1,
                    "sequence_score": 9.0,
                    "acidic_flank_count": 5,
                    "serine_threonine_flank_count": 0,
                    "start_1based": 11,
                    "end_1based": 14,
                    "core_sequence": sequence[10:14],
                    "context_sequence": sequence[max(0, 10 - flank_size) : 14 + flank_size],
                }
            ],
        }

    @staticmethod
    def run_cli(argv: list[str], inputs: list[str] | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            if inputs is None:
                exit_code = main(argv)
            else:
                with patch("builtins.input", side_effect=inputs):
                    exit_code = main(argv)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_parser_exposes_complete_command_surface(self) -> None:
        help_text = build_parser().format_help()
        for command in (
            "doctor",
            "plan",
            "design-peptides",
            "scan-motifs",
            "run",
            "run-panel",
            "resume",
            "analyze",
            "report",
            "visualize",
            "import-legacy",
        ):
            self.assertIn(command, help_text)

    def test_run_panel_dry_run_prepares_all_controls_and_reports(self) -> None:
        job = {
            "schema_version": "1.0",
            "name": "atg8-yta7-fdfl",
            "language": "zh-CN",
            "inputs": {
                "organism": "Saccharomyces cerevisiae S288c",
                "proteins": [
                    {
                        "id": "A",
                        "name": "Atg8",
                        "sequence": "MKSTFKSEYPFEKRKAESERIADRFKNRIPVICEKAEKSDIPEIDKRKYLVPADLTVGQFVYVIRKRIMLPPEKAIFIFVNDTLPPTAALMSAIYQEHKDKDGFLYVTYSGENTFGR",
                    },
                    {
                        "id": "B",
                        "name": "Yta7-43-66",
                        "sequence": "KINYAEIEKVFDFLEDDQVMDKDE",
                    },
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
            "execution": {"backend": "boltz2", "status": "planned", "remote_msa": False},
            "privacy": {"local_first": True, "sequence_upload_authorized": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_path = root / "job.json"
            run_dir = root / "run"
            job_path.write_text(json.dumps(job), encoding="utf-8")
            exit_code, stdout, _ = self.run_cli(
                [
                    "--lang",
                    "zh-CN",
                    "run-panel",
                    str(job_path),
                    "--windows",
                    "24",
                    "--design-seed",
                    "7",
                    "--output-dir",
                    str(run_dir),
                    "--dry-run",
                ]
            )

            self.assertEqual(exit_code, 0)
            result = json.loads(stdout)
            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(result["task_count"], 10)
            self.assertEqual(result["msa_mode"], "single_sequence")
            self.assertEqual(len(json.loads((run_dir / "plan.json").read_text())["tasks"]), 10)
            self.assertTrue((run_dir / "panel.json").is_file())
            self.assertTrue((run_dir / "confidence_summary.csv").is_file())
            self.assertTrue((run_dir / "report.md").is_file())
            self.assertTrue((run_dir / "report.html").is_file())

    def test_default_run_directory_slug_cannot_escape_runs(self) -> None:
        self.assertEqual(_safe_job_slug("../../../tmp/secret"), "tmp-secret")
        self.assertEqual(_safe_job_slug(".."), "ppi-job")
        self.assertEqual(_safe_job_slug("Atg8 与 Atg19"), "Atg8-与-Atg19")

    def test_plan_accepts_name_inputs_and_emits_job(self) -> None:
        exit_code, stdout, _ = self.run_cli(
            [
                "--lang",
                "zh-CN",
                "plan",
                "Atg19",
                "Atg8",
                "--organism",
                "Saccharomyces cerevisiae",
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["language"], "zh-CN")
        self.assertEqual(payload["inputs"]["proteins"][0]["name"], "Atg19")
        self.assertEqual(payload["inputs"]["proteins"][1]["name"], "Atg8")
        self.assertEqual(payload["inputs"]["organism"], "Saccharomyces cerevisiae")
        self.assertEqual(payload["routing"]["route"], "needs_review")

    def test_plan_records_motif_evidence_and_routes_accessible_candidate(self) -> None:
        exit_code, stdout, _ = self.run_cli(
            [
                "plan",
                "--sequence-a",
                "MKSTFKSEYPFEKRKAESER",
                "--sequence-b",
                "MSTYQQVADKWQQLDEESGKNPTA",
                "--motif-owner",
                "B",
                "--motif-region",
                "11:14",
                "--motif-sequence",
                "WQQL",
                "--motif-context",
                "disordered",
                "--receptor-has-motif-pocket",
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["routing"]["route"], "motif_peptide")
        self.assertEqual(payload["routing"]["selected_motif"], "WQQL")
        self.assertEqual(payload["routing"]["selected_region"], [11, 14])
        self.assertEqual(payload["hypothesis"]["motif_owner"], "B")
        self.assertEqual(payload["hypothesis"]["coordinate_convention"], "1-based inclusive")

    def test_plan_rejects_motif_coordinate_sequence_mismatch(self) -> None:
        exit_code, _, stderr = self.run_cli(
            [
                "plan",
                "--sequence-a",
                "MKSTFKSEYPFEKRKAESER",
                "--sequence-b",
                "MSTYQQVADKWQQLDEESGKNPTA",
                "--motif-owner",
                "B",
                "--motif-region",
                "11:14",
                "--motif-sequence",
                "WEDL",
            ]
        )

        self.assertEqual(exit_code, 2)
        self.assertIn("does not match", stderr)

    def test_design_peptides_uses_one_based_inclusive_coordinates(self) -> None:
        sequence = "MSTYQQVADKWQQLDEESGKNPTA"
        exit_code, stdout, _ = self.run_cli(
            [
                "design-peptides",
                "--sequence",
                sequence,
                "--motif",
                "11:14",
                "--windows",
                "16,24",
                "--seed",
                "7",
            ]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["coordinate_system"], "1-based inclusive")
        self.assertEqual(
            payload["motif"],
            {"sequence": "WQQL", "start_1based": 11, "end_1based": 14},
        )
        self.assertEqual(payload["window_sizes"], [16, 24])
        self.assertEqual(payload["seed"], 7)

    def test_design_peptides_can_locate_unique_motif(self) -> None:
        exit_code, stdout, _ = self.run_cli(
            [
                "design-peptides",
                "--sequence",
                "MSTYQQVADKWQQLDEESGKNPTA",
                "--motif-sequence",
                "WQQL",
                "--windows",
                "16",
            ]
        )
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["motif"]["start_1based"], 11)
        self.assertEqual(payload["motif"]["end_1based"], 14)

    def test_interactive_start_asks_language_then_two_proteins(self) -> None:
        exit_code, stdout, _ = self.run_cli(
            [],
            inputs=["3", "Atg19", "Atg8", "S. cerevisiae", "auto", ""],
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["language"], "ja")
        self.assertEqual(
            [protein["name"] for protein in payload["inputs"]["proteins"]],
            ["Atg19", "Atg8"],
        )
        self.assertNotIn("motif_scan", payload)

    def test_chinese_interactive_guidance_explains_operational_choices(self) -> None:
        exit_code, stdout, stderr = self.run_cli(
            [],
            inputs=["1", "Atg8", "Atg19", "S. cerevisiae", "", ""],
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout)["language"], "zh-CN")
        self.assertIn("A=已知受体/口袋/参考蛋白", stderr)
        self.assertIn("Atg8/Atg19 示例中：A=Atg8，B=Atg19", stderr)
        self.assertIn("A/B 只是输入标签", stderr)
        self.assertIn("不能留空", stderr)
        self.assertIn("Saccharomyces cerevisiae S288c", stderr)
        self.assertIn("可以留空，默认 auto", stderr)
        self.assertIn("可以留空，默认关闭", stderr)
        self.assertIn("不是结合预测", stderr)

    def test_scan_motifs_lists_candidates_without_implicit_design(self) -> None:
        fake_module = SimpleNamespace(scan_aim_lir=self.fake_scan)
        with patch.dict("sys.modules", {"ppi_scout.motif_scan": fake_module}):
            exit_code, stdout, _ = self.run_cli(
                ["scan-motifs", "--sequence", self.SCAN_SEQUENCE]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["candidates"][0]["candidate_id"], "aim-001")
        self.assertEqual(payload["designed_candidate_ids"], [])
        self.assertEqual(payload["peptide_panels"], [])
        self.assertIn("No peptide candidate was selected", payload["selection_note"])

    def test_real_scanner_integrates_with_cli_and_reports_all_atg19_hits(self) -> None:
        exit_code, stdout, _ = self.run_cli(
            ["scan-motifs", "--sequence", self.SCAN_SEQUENCE]
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(
            [(item["candidate_id"], item["core_sequence"]) for item in payload["candidates"]],
            [("aim-002", "WQQL"), ("aim-001", "YQQV")],
        )
        self.assertEqual(payload["candidates"][0]["rank"], 1)
        self.assertEqual(payload["designed_candidate_ids"], [])
        self.assertEqual(payload["peptide_panels"], [])

    def test_scan_motifs_designs_only_explicit_candidate(self) -> None:
        fake_module = SimpleNamespace(scan_aim_lir=self.fake_scan)
        with patch.dict("sys.modules", {"ppi_scout.motif_scan": fake_module}):
            exit_code, stdout, _ = self.run_cli(
                [
                    "scan-motifs",
                    "--sequence",
                    self.SCAN_SEQUENCE,
                    "--windows",
                    "16,24",
                    "--design-candidate",
                    "aim-001",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["designed_candidate_ids"], ["aim-001"])
        self.assertEqual(len(payload["peptide_panels"]), 1)
        design = payload["peptide_panels"][0]["design"]
        self.assertEqual(design["motif"]["sequence"], "WQQL")
        self.assertEqual(design["window_sizes"], [16, 24])

    def test_interactive_scan_is_opt_in_and_does_not_change_route(self) -> None:
        fake_module = SimpleNamespace(scan_aim_lir=self.fake_scan)
        with patch.dict("sys.modules", {"ppi_scout.motif_scan": fake_module}):
            exit_code, stdout, stderr = self.run_cli(
                [],
                inputs=[
                    "1",
                    "MKSTFKSEYPFEKRKAESER",
                    self.SCAN_SEQUENCE,
                    "S. cerevisiae",
                    "auto",
                    "yes",
                    "B",
                    "aim-001",
                ],
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["motif_scan"]["owner"], "B")
        self.assertEqual(payload["motif_scan"]["status"], "complete")
        self.assertEqual(payload["motif_scan"]["designed_candidate_ids"], ["aim-001"])
        self.assertEqual(payload["peptide_design"]["candidate_ids"], ["aim-001"])
        self.assertEqual(payload["peptide_design"]["windows"], [16, 24])
        self.assertEqual(
            payload["motif_scan"]["peptide_panels"][0]["design"]["window_sizes"],
            [16, 24],
        )
        self.assertNotEqual(payload["routing"]["route"], "motif_peptide")
        self.assertIn("aim-001: WQQL at 11:14; rank 1; sequence score 9.0", stderr)
        self.assertIn("侧翼 D/E=5", stderr)
        self.assertIn("不能证明 motif 可及性", stderr)
        self.assertIn("请选择扫描蛋白 A 还是 B", stderr)
        self.assertIn("Atg8/Atg19 示例选择 B（Atg19）", stderr)
        self.assertIn("可以留空，默认一个也不设计", stderr)
        self.assertIn("排名只用于序列优先级", stderr)

    def test_interactive_scan_name_only_is_skipped_safely(self) -> None:
        exit_code, stdout, stderr = self.run_cli(
            [],
            inputs=["2", "Atg8", "Atg19", "S. cerevisiae", "auto", "y", "B"],
        )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["motif_scan"]["status"], "skipped")
        self.assertIn("requires an amino-acid sequence", payload["motif_scan"]["reason"])
        self.assertIn("requires an amino-acid sequence", stderr)

    def test_fallback_router_never_uses_length_as_route_evidence(self) -> None:
        proteins = [
            {"id": "A", "name": "TinyA", "sequence": "A" * 20},
            {"id": "B", "name": "TinyB", "sequence": "A" * 30},
        ]
        decision = _route_fallback(proteins, "auto")
        self.assertEqual(decision["route"], "needs_review")
        self.assertIn("length", decision["reasons"][0])

    def test_nonstandard_residue_is_rejected(self) -> None:
        exit_code, _, stderr = self.run_cli(
            ["plan", "--sequence-a", "ACDEFGHIKLMB", "--sequence-b", "ACDEFGHIKLMN"]
        )
        self.assertEqual(exit_code, 2)
        self.assertIn("invalid residue", stderr)

    def test_dry_run_is_auditable_and_reportable(self) -> None:
        job = {
            "schema_version": "1.0",
            "name": "smoke-complex",
            "language": "en",
            "inputs": {
                "organism": "synthetic test",
                "proteins": [
                    {
                        "id": "A",
                        "name": "protein-a",
                        "sequence": "ACDEFGHIKLMNPQRSTVWY",
                        "source": "sequence",
                    },
                    {
                        "id": "B",
                        "name": "protein-b",
                        "sequence": "YWVTSRQPNMLKIHGFEDCA",
                        "source": "sequence",
                    },
                ],
            },
            "execution": {"backend": "boltz2", "status": "planned", "remote_msa": False},
            "privacy": {"local_first": True, "sequence_upload_authorized": False},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "input-job.json"
            job_path.write_text(json.dumps(job), encoding="utf-8")
            run_dir = root / "run"

            exit_code, stdout, _ = self.run_cli(
                ["--lang", "zh-CN", "run", str(job_path), "--output-dir", str(run_dir)]
            )
            self.assertEqual(exit_code, 0)
            result = json.loads(stdout)
            self.assertEqual(result["status"], "dry_run")
            for filename in ("job.json", "resolved_input.yaml", "plan.json", "status.json", "report.html"):
                self.assertTrue((run_dir / filename).is_file(), filename)
            self.assertEqual(result["visualization"]["status"], "complete")
            self.assertEqual(result["visualization"]["path"], str(run_dir / "report.html"))
            self.assertIn("PPI Scout 本地结果页", (run_dir / "report.html").read_text(encoding="utf-8"))
            saved_job = json.loads((run_dir / "job.json").read_text(encoding="utf-8"))
            self.assertFalse(saved_job["privacy"]["sequence_upload_authorized"])
            self.assertNotIn("--use_msa_server", result["argv"])

            report_code, report_stdout, _ = self.run_cli(["report", str(run_dir)])
            self.assertEqual(report_code, 0)
            self.assertTrue((run_dir / "report.md").is_file())
            self.assertEqual(json.loads(report_stdout)["status"], "complete")

            visual_code, visual_stdout, _ = self.run_cli(["visualize", str(run_dir)])
            self.assertEqual(visual_code, 0)
            self.assertTrue((run_dir / "report.html").is_file())
            self.assertTrue(json.loads(visual_stdout)["offline"])

    def test_automatic_visualization_failure_does_not_mask_dry_run(self) -> None:
        job = {
            "name": "visualization-failure",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "B", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            run_dir = root / "run"
            job_path.write_text(json.dumps(job), encoding="utf-8")
            run_dir.mkdir()
            (run_dir / "report.html").write_text("stale report", encoding="utf-8")

            with patch(
                "ppi_scout.visualization.write_html_report",
                side_effect=OSError("simulated HTML write failure"),
            ):
                exit_code, stdout, _ = self.run_cli(
                    ["run", str(job_path), "--output-dir", str(run_dir)]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["visualization"]["status"], "failed")
            self.assertTrue(payload["visualization"]["run_status_unchanged"])
            self.assertFalse((run_dir / "report.html").exists())
            saved_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_status["status"], "dry_run")

    def test_live_backend_failure_still_generates_failure_result_page(self) -> None:
        job = {
            "name": "live-failure",
            "language": "zh-CN",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "B", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            run_dir = root / "run"
            job_path.write_text(json.dumps(job), encoding="utf-8")

            with patch(
                "ppi_scout.backends.boltz2.Boltz2Backend.run",
                side_effect=RuntimeError("simulated Boltz failure"),
            ):
                exit_code, _, stderr = self.run_cli(
                    ["run", str(job_path), "--output-dir", str(run_dir), "--live"]
                )

            self.assertEqual(exit_code, 2)
            self.assertIn("simulated Boltz failure", stderr)
            self.assertTrue((run_dir / "report.html").is_file())
            saved_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_status["status"], "failed")
            self.assertEqual(saved_status["visualization"]["status"], "complete")
            page = (run_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn("simulated Boltz failure", page)

    def test_final_status_metadata_write_failure_does_not_mask_dry_run(self) -> None:
        job = {
            "name": "metadata-write-failure",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "B", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
        }
        original_write_text = Path.write_text

        def fail_final_status_write(path: Path, data: str, *args: object, **kwargs: object) -> int:
            if path.name == "status.json" and '"visualization"' in data:
                raise OSError("simulated final status metadata failure")
            return original_write_text(path, data, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            run_dir = root / "run"
            job_path.write_text(json.dumps(job), encoding="utf-8")

            with patch.object(Path, "write_text", autospec=True, side_effect=fail_final_status_write):
                exit_code, stdout, stderr = self.run_cli(
                    ["run", str(job_path), "--output-dir", str(run_dir)]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "dry_run")
            self.assertFalse(payload["visualization"]["metadata_persisted"])
            self.assertIn("status.json", stderr)
            self.assertTrue((run_dir / "report.html").is_file())
            saved_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_status["status"], "dry_run")

    def test_mocked_live_success_generates_report_with_available_metric(self) -> None:
        job = {
            "name": "live-success",
            "language": "en",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "B", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            run_dir = root / "run"
            confidence_dir = run_dir / "predictions"
            confidence_dir.mkdir(parents=True)
            (confidence_dir / "confidence_model_0.json").write_text(
                json.dumps({"iptm": 0.91, "rank_score": 3.2}),
                encoding="utf-8",
            )
            job_path.write_text(json.dumps(job), encoding="utf-8")

            with patch(
                "ppi_scout.backends.boltz2.Boltz2Backend.run",
                return_value={"status": "complete", "returncode": 0},
            ):
                exit_code, stdout, _ = self.run_cli(
                    ["run", str(job_path), "--output-dir", str(run_dir), "--live"]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "complete")
            self.assertEqual(payload["visualization"]["status"], "complete")
            page = (run_dir / "report.html").read_text(encoding="utf-8")
            self.assertIn("0.91", page)
            self.assertIn("3.2", page)

    def test_compile_failure_generates_diagnostic_page(self) -> None:
        job = {
            "name": "compile-failure",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "A", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "job.json"
            run_dir = root / "run"
            job_path.write_text(json.dumps(job), encoding="utf-8")

            exit_code, _, stderr = self.run_cli(
                ["run", str(job_path), "--output-dir", str(run_dir)]
            )

            self.assertEqual(exit_code, 2)
            self.assertIn("Duplicate", stderr)
            saved_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_status["status"], "failed")
            self.assertEqual(saved_status["visualization"]["status"], "complete")
            self.assertTrue((run_dir / "report.html").is_file())
            self.assertIn("Duplicate", (run_dir / "report.html").read_text(encoding="utf-8"))

    def test_visualize_scan_json_without_running_boltz(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scan_path = root / "atg19-scan.json"
            scan_path.write_text(
                json.dumps(
                    {
                        "kind": "aim_lir_scan",
                        "candidates": [
                            {
                                "candidate_id": "aim-002",
                                "core_sequence": "WQQL",
                                "start_1based": 11,
                                "end_1based": 14,
                                "rank": 1,
                                "sequence_score": 9.0,
                            }
                        ],
                        "designed_candidate_ids": [],
                        "peptide_panels": [],
                    }
                ),
                encoding="utf-8",
            )

            exit_code, stdout, _ = self.run_cli(
                ["--lang", "zh-CN", "visualize", str(scan_path)]
            )

            self.assertEqual(exit_code, 0)
            destination = root / "atg19-scan-report.html"
            self.assertTrue(destination.is_file())
            self.assertIn("PPI Scout 本地结果页", destination.read_text(encoding="utf-8"))
            self.assertIn("aim-002", destination.read_text(encoding="utf-8"))
            self.assertTrue(json.loads(stdout)["offline"])

            replace_code, _, replace_stderr = self.run_cli(
                ["visualize", str(scan_path), "-o", str(scan_path)]
            )
            self.assertEqual(replace_code, 2)
            self.assertIn("must not replace", replace_stderr)

    def test_visualize_handles_malformed_nested_job_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_path = root / "odd-job.json"
            job_path.write_text(
                json.dumps({"name": "odd", "inputs": None, "routing": None, "execution": None}),
                encoding="utf-8",
            )

            exit_code, _, stderr = self.run_cli(["visualize", str(job_path)])

            self.assertEqual(exit_code, 0, stderr)
            self.assertTrue((root / "odd-job-report.html").is_file())

    def test_resume_preserves_recorded_remote_msa_and_output_format(self) -> None:
        job = {
            "schema_version": "1.0",
            "name": "resume-smoke",
            "inputs": {
                "proteins": [
                    {"id": "A", "sequence": "ACDEFGHIKLMNPQRSTVWY"},
                    {"id": "B", "sequence": "YWVTSRQPNMLKIHGFEDCA"},
                ]
            },
            "execution": {
                "backend": "boltz2",
                "status": "failed",
                "remote_msa": True,
                "output_format": "mmcif",
            },
            "privacy": {"sequence_upload_authorized": True},
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
            (run_dir / "report.html").write_text("stale report", encoding="utf-8")

            exit_code, stdout, _ = self.run_cli(["resume", str(run_dir), "--dry-run"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout)
            self.assertIn("--use_msa_server", payload["argv"])
            self.assertTrue((run_dir / "report.html").is_file())
            self.assertEqual(payload["visualization"]["status"], "complete")
            self.assertNotIn("stale report", (run_dir / "report.html").read_text(encoding="utf-8"))
            format_index = payload["argv"].index("--output_format")
            self.assertEqual(payload["argv"][format_index + 1], "mmcif")

    def test_language_aliases_and_translations(self) -> None:
        self.assertEqual(normalize_language("中文"), "zh-CN")
        self.assertEqual(normalize_language("jp"), "ja")
        self.assertEqual(Translator.for_language("ja").t("welcome"), "PPI Scout へようこそ。")


if __name__ == "__main__":
    unittest.main()
