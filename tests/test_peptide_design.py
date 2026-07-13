from collections import Counter
import re
import unittest

from ppi_scout.peptide_design import design_peptide_panel


ATG19_24MER = "MSTYQQVADKWQQLDEESGKNPTA"


class PeptideDesignTests(unittest.TestCase):
    def test_atg19_standard_and_short_windows(self) -> None:
        panel = design_peptide_panel(ATG19_24MER, 11, 14, window_sizes=(16, 24), seed=7)
        wt = {variant.requested_window: variant for variant in panel.variants if variant.kind == "wt"}
        self.assertEqual(wt[16].sequence, "QQVADKWQQLDEESGK")
        self.assertEqual(wt[24].sequence, ATG19_24MER)
        self.assertEqual(panel.motif_sequence, "WQQL")

    def test_mechanistic_controls_are_generated(self) -> None:
        panel = design_peptide_panel(ATG19_24MER, 11, 14, window_sizes=(24,), seed=7)
        cores = {
            variant.kind: variant.sequence[variant.motif_start_in_peptide - 1 : variant.motif_end_in_peptide]
            for variant in panel.variants
        }
        self.assertEqual(cores["anchor_1_to_a"], "AQQL")
        self.assertEqual(cores["anchor_2_to_a"], "WQQA")
        self.assertEqual(cores["double_anchor_to_a"], "AQQA")
        self.assertEqual(cores["core_to_aaaa"], "AAAA")
        self.assertEqual(cores["reverse_decoy"], "LQQW")

    def test_clean_scrambles_preserve_composition_and_exclude_canonical_aim(self) -> None:
        panel = design_peptide_panel(ATG19_24MER, 11, 14, window_sizes=(24,), seed=7)
        scrambles = [variant.sequence for variant in panel.variants if variant.kind == "clean_scramble"]
        self.assertEqual(len(scrambles), 3)
        for sequence in scrambles:
            self.assertEqual(Counter(sequence), Counter(ATG19_24MER))
            self.assertIsNone(re.search(r"[WFY]..[LIV]", sequence))

    def test_seed_is_reproducible(self) -> None:
        first = design_peptide_panel(ATG19_24MER, 11, 14, window_sizes=(16,), seed=19)
        second = design_peptide_panel(ATG19_24MER, 11, 14, window_sizes=(16,), seed=19)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
