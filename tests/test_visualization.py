import unittest

from ppi_scout.visualization import build_html_report


class VisualizationTests(unittest.TestCase):
    def test_builds_offline_chinese_result_page(self) -> None:
        job = {
            "name": "Atg8--Atg19",
            "language": "zh-CN",
            "inputs": {
                "proteins": [
                    {"id": "A", "name": "Atg8", "sequence": "M" * 117, "source": "fasta"},
                    {"id": "B", "name": "Atg19", "sequence": "MSTYQQVADKWQQLDEESGKNPTA", "source": "fasta"},
                ]
            },
            "routing": {"route": "motif_peptide"},
            "execution": {"status": "complete"},
        }
        scan = {
            "designed_candidate_ids": ["aim-002"],
            "candidates": [
                {
                    "candidate_id": "aim-002",
                    "core_sequence": "WQQL",
                    "start_1based": 11,
                    "end_1based": 14,
                    "rank": 1,
                    "sequence_score": 9.0,
                    "acidic_flank_count": 5,
                    "serine_threonine_flank_count": 0,
                    "warnings": ["The requested flank was truncated by a sequence terminus."],
                }
            ],
            "peptide_panels": [],
            "warnings": ["Sequence scores are heuristic, not probabilities."],
        }
        page = build_html_report(
            job,
            [{"source": "confidence_model_0.json", "iptm": 0.917, "rank_score": 3.1}],
            scan=scan,
        )

        self.assertIn("PPI Scout 本地结果页", page)
        self.assertIn("Atg8--Atg19", page)
        self.assertIn("aim-002", page)
        self.assertIn("WQQL", page)
        self.assertIn("width:91.7%", page)
        self.assertIn("不是实验结合证明", page)
        self.assertIn("ipTM / protein_ipTM", page)
        self.assertIn("不是结合概率", page)
        self.assertIn("序列分数只是启发式优先级", page)
        self.assertIn("aim-002: 要求的侧翼被序列末端截短", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("fetch(", page)

    def test_escapes_untrusted_names_and_sequences(self) -> None:
        page = build_html_report(
            {
                "name": "<script>alert(1)</script>",
                "inputs": {
                    "proteins": [
                        {"id": "A", "name": "<img src=x onerror=alert(1)>", "sequence": "AAAA"}
                    ]
                },
            },
            [],
            language="en",
        )

        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_scan_only_page_still_explains_future_metrics_and_control_types(self) -> None:
        page = build_html_report(
            None,
            [],
            scan={
                "candidates": [],
                "peptide_panels": [
                    {
                        "candidate_id": "aim-001",
                        "design": {
                            "panel": {
                                "variants": [
                                    {
                                        "variant_id": "w16-anchor-1-to-a",
                                        "kind": "anchor_1_to_a",
                                        "actual_window": 16,
                                        "sequence": "AAAA",
                                        "mutation": "WQQL->ADFL",
                                    }
                                ]
                            }
                        },
                    }
                ],
            },
            language="zh-CN",
        )

        self.assertIn("没有发现置信度文件", page)
        self.assertIn("ipTM / protein_ipTM", page)
        self.assertIn("第一个锚点突变为 A", page)


if __name__ == "__main__":
    unittest.main()
