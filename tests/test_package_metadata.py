from __future__ import annotations

from pathlib import Path
import re
import unittest

from ppi_scout import __version__


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def test_runtime_version_matches_pyproject(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(
            r'^version\s*=\s*"(?P<version>\d+\.\d+\.\d+)"',
            pyproject,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(match, "pyproject.toml must declare a package version.")
        assert match is not None
        self.assertEqual(__version__, match.group("version"))

    def test_readme_install_tag_matches_runtime_version(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"ppi-scout\.git@v(?P<version>\d+\.\d+\.\d+)", readme)
        self.assertIsNotNone(match, "README must contain a version-pinned install command.")
        assert match is not None
        self.assertEqual(match.group("version"), __version__)


if __name__ == "__main__":
    unittest.main()
