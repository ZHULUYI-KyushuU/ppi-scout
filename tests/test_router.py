import unittest

from ppi_scout.models import InteractionQuery, ProteinEvidence
from ppi_scout.router import route_interaction


class RouterTests(unittest.TestCase):
    def test_accessible_motif_routes_to_peptide(self) -> None:
        decision = route_interaction(
            InteractionQuery(
                ProteinEvidence("Atg8", sequence="ACDEFG"),
                ProteinEvidence("Atg19", sequence="A" * 200),
                motif_sequence="WQQL",
                motif_region=(53, 56),
                motif_in_disorder=True,
                receptor_has_motif_pocket=True,
            )
        )
        self.assertEqual(decision.route, "motif_peptide")
        self.assertEqual(decision.selected_region, (53, 56))

    def test_membrane_context_routes_complete_protein_not_peptide(self) -> None:
        decision = route_interaction(
            InteractionQuery(
                ProteinEvidence("Atg44", sequence="A" * 73, membrane_dependent=True),
                ProteinEvidence("Partner", sequence="ACDEFG"),
            )
        )
        self.assertEqual(decision.route, "full_length")
        self.assertTrue(decision.warnings)

    def test_length_alone_never_creates_a_peptide_route(self) -> None:
        decision = route_interaction(
            InteractionQuery(
                ProteinEvidence("Large", sequence="A" * 2000),
                ProteinEvidence("Partner", sequence="ACDEFG"),
            )
        )
        self.assertNotEqual(decision.route, "motif_peptide")

    def test_unresolved_name_requires_review(self) -> None:
        decision = route_interaction(
            InteractionQuery(ProteinEvidence("Atg19"), ProteinEvidence("Atg8"))
        )
        self.assertEqual(decision.route, "needs_review")


if __name__ == "__main__":
    unittest.main()
