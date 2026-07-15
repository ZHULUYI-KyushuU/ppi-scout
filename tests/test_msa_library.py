from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ppi_scout.msa_library import read_a3m_query, resolve_receptor_msa
from ppi_scout.resolver import sequence_hash


class MSALibraryTests(unittest.TestCase):
    RECEPTOR = "ACDEFGHIKLMNPQRSTVWY"

    def test_exact_sequence_hash_resolves_audited_a3m(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / f"{sequence_hash(self.RECEPTOR)}.a3m"
            path.write_text(">query\nACDEFGHIKLMNPQRSTVWY\n>hit\nACDEfFGHIKLMNPQRSTVWY\n")

            resolution = resolve_receptor_msa(root, self.RECEPTOR)

            self.assertTrue(resolution.matched)
            self.assertEqual(resolution.path, path.resolve())
            self.assertEqual(read_a3m_query(path), self.RECEPTOR)

    def test_missing_exact_hash_falls_back_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolution = resolve_receptor_msa(Path(tmp), self.RECEPTOR)
            self.assertFalse(resolution.matched)
            self.assertIsNone(resolution.path)

    def test_hash_named_a3m_with_wrong_query_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / f"{sequence_hash(self.RECEPTOR)}.a3m"
            path.write_text(">query\nACDEFGHIKLMNPQRSTVWX\n")

            with self.assertRaisesRegex(ValueError, "does not exactly match"):
                resolve_receptor_msa(root, self.RECEPTOR)


if __name__ == "__main__":
    unittest.main()
