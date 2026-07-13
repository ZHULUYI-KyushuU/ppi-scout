import unittest

from ppi_scout.motif_scan import scan_aim_lir


class AimLirScanTests(unittest.TestCase):
    def test_synthetic_fragment_finds_wqql_with_one_based_coordinates(self):
        result = scan_aim_lir("MSTYQQVADKWQQLDEESGKNPTA")

        # The fragment also contains YQQV at 4-7.  Reporting both is important:
        # the scanner must not silently select only the already-known WQQL site.
        self.assertEqual(len(result.candidates), 2)
        candidate = result.candidates[0]
        self.assertEqual(candidate.candidate_id, "aim-002")
        self.assertEqual(candidate.candidate_key, "aim-lir-000011-000014-WQQL")
        self.assertEqual((candidate.start_1based, candidate.end_1based), (11, 14))
        self.assertEqual(candidate.core_sequence, "WQQL")
        self.assertEqual((candidate.flank_start_1based, candidate.flank_end_1based), (5, 20))
        self.assertEqual(candidate.flank_sequence, "QQVADKWQQLDEESGK")
        self.assertEqual(candidate.sequence_score, 8.5)
        self.assertEqual(candidate.acidic_flank_count, 4)
        self.assertEqual(candidate.serine_threonine_flank_count, 1)
        self.assertEqual(candidate.rank, 1)
        self.assertIn("sequence evidence only", candidate.reasons[0])
        self.assertIn("does not establish function", result.warnings[0])
        self.assertEqual(result.to_dict()["candidates"][0]["core_sequence"], "WQQL")

    def test_multiple_tied_candidates_keep_equal_rank_and_coordinate_order(self):
        result = scan_aim_lir("AAAAWQQLAAAAFYAI", flank_size=0)

        self.assertEqual([item.core_sequence for item in result.candidates], ["WQQL", "FYAI"])
        self.assertEqual([item.rank for item in result.candidates], [1, 1])
        self.assertEqual([item.sequence_score for item in result.candidates], [4.0, 4.0])
        self.assertTrue(all("tied" in item.warnings[0] for item in result.candidates))

    def test_sequence_score_orders_explicit_flank_features(self):
        result = scan_aim_lir("DEWQQLDEAAAAFYAI", flank_size=2)

        self.assertEqual(result.candidates[0].core_sequence, "WQQL")
        self.assertGreater(result.candidates[0].sequence_score, result.candidates[1].sequence_score)
        self.assertEqual([item.rank for item in result.candidates], [1, 2])

    def test_overlapping_matches_are_all_reported(self):
        result = scan_aim_lir("WYALI", flank_size=0)

        self.assertEqual(len(result.candidates), 2)
        self.assertEqual([item.core_sequence for item in result.candidates], ["WYAL", "YALI"])
        self.assertEqual(
            [(item.start_1based, item.end_1based) for item in result.candidates],
            [(1, 4), (2, 5)],
        )

    def test_no_hit_is_valid_and_warned(self):
        result = scan_aim_lir("ACDEGHKNPQRSTV")

        self.assertEqual(result.candidates, ())
        self.assertTrue(any("No canonical" in warning for warning in result.warnings))

    def test_invalid_sequence_is_rejected_by_shared_normalizer(self):
        with self.assertRaisesRegex(ValueError, "invalid residues"):
            scan_aim_lir("WQQL!")

    def test_invalid_flank_size_is_rejected(self):
        for value in (-1, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "non-negative integer"):
                    scan_aim_lir("WQQL", flank_size=value)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
