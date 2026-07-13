import json
from pathlib import Path
import tempfile
import unittest

from ppi_scout.resolver import (
    parse_fasta,
    resolve_fasta,
    resolve_uniprot_accession,
    search_uniprot_gene,
)


class ResolverTests(unittest.TestCase):
    def test_parse_single_fasta(self) -> None:
        header, sequence = parse_fasta(">Atg8 example\nACDE\nFG\n")
        self.assertEqual(header, "Atg8 example")
        self.assertEqual(sequence, "ACDEFG")

    def test_multiple_fasta_records_are_not_silently_merged(self) -> None:
        with self.assertRaises(ValueError):
            parse_fasta(">A\nACD\n>B\nEFG\n")

    def test_resolve_fasta_records_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "protein.fa"
            path.write_text(">protein one\nACDEFG\n", encoding="utf-8")
            resolved = resolve_fasta(path)
        self.assertEqual(resolved.name, "protein")
        self.assertEqual(len(resolved.sequence_sha256), 64)

    def test_uniprot_accession_can_be_tested_without_network(self) -> None:
        def fake_fetch(_: str):
            return {
                "primaryAccession": "P00001",
                "uniProtkbId": "TEST_YEAST",
                "organism": {"scientificName": "Saccharomyces cerevisiae"},
                "genes": [{"geneName": {"value": "TEST"}}],
                "sequence": {"value": "ACDEFG"},
            }

        resolved = resolve_uniprot_accession("P00001", fetch_json=fake_fetch)
        self.assertEqual(resolved.name, "TEST")
        self.assertEqual(resolved.sequence, "ACDEFG")

    def test_gene_search_returns_candidates_instead_of_guessing(self) -> None:
        def fake_fetch(_: str):
            return {
                "results": [
                    {
                        "primaryAccession": "P00001",
                        "uniProtkbId": "TEST_YEAST",
                        "organism": {"scientificName": "Saccharomyces cerevisiae"},
                        "sequence": {"value": "ACDEFG", "length": 6},
                    },
                    {
                        "primaryAccession": "Q00002",
                        "uniProtkbId": "TEST2_YEAST",
                        "organism": {"scientificName": "Saccharomyces cerevisiae"},
                        "sequence": {"value": "ACDEFGH", "length": 7},
                    },
                ]
            }

        candidates = search_uniprot_gene("TEST", 1, fetch_json=fake_fetch)
        self.assertEqual([row["accession"] for row in candidates], ["P00001", "Q00002"])


if __name__ == "__main__":
    unittest.main()
