from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zipfile

from scripts.prepare_offline_release import prepare, sha256, split_asset


class PrepareOfflineReleaseTests(unittest.TestCase):
    def test_split_asset_is_ordered_and_reconstructable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            root = Path(tmp_value)
            source = root / "source.bin"
            source.write_bytes(b"abcdefghijklmnopqrstuvwxyz")
            output = root / "out"
            output.mkdir()

            parts = split_asset(source, "models/source.bin", output, 10)

            self.assertEqual([part.index for part in parts], [0, 1, 2])
            self.assertTrue(all(part.total == 3 for part in parts))
            rebuilt = b"".join((output / part.asset).read_bytes() for part in parts)
            self.assertEqual(rebuilt, source.read_bytes())
            self.assertTrue(all(part.final_sha256 == sha256(source) for part in parts))

    def test_prepare_writes_one_click_setup_zips_for_both_platforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_value:
            root = Path(tmp_value)
            bundle = root / "bundle"
            output = root / "release"
            files = (
                "Run-PPI-Scout-macOS.command",
                "Run-PPI-Scout-Windows.cmd",
                "README.md",
                "jobs/current-job.json",
                "msas/README.md",
                "models/SHA256SUMS",
                "models/mols.tar",
                "models/boltz2_conf.ckpt",
                "models/boltz2_aff.ckpt",
                "macos-arm64/ppi-scout-runtime-macos-arm64.tar.gz",
                "windows-wsl2-x64/ppi-scout-runtime-linux-x86_64.tar.gz",
                "windows-wsl2-x64/ubuntu-rootfs.tar.gz",
                "windows-wsl2-x64/install-and-run.ps1",
                "windows-wsl2-x64/install-and-run.sh",
            )
            for index, relative in enumerate(files):
                path = bundle / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((f"payload-{index}-" * 3).encode())

            prepare(
                SimpleNamespace(
                    bundle=bundle,
                    output=output,
                    tag="offline-test",
                    owner="owner",
                    repo="repo",
                    chunk_size=17,
                )
            )

            mac_zip = output / "PPI-Scout-Online-Setup-macOS.zip"
            windows_zip = output / "PPI-Scout-Online-Setup-Windows.zip"
            self.assertTrue(mac_zip.is_file())
            self.assertTrue(windows_zip.is_file())
            self.assertTrue((output / "release-assets.sha256").is_file())
            self.assertFalse((output / "ppi-scout-offline-common.tar.gz").exists())
            with zipfile.ZipFile(mac_zip) as archive:
                script = archive.read("Online-Setup-and-Run-macOS.command").decode()
            self.assertIn("offline-test", script)
            self.assertIn("models/boltz2_conf.ckpt", script)


if __name__ == "__main__":
    unittest.main()
