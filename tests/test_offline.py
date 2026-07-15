from __future__ import annotations

import subprocess
import sys
import unittest

from ppi_scout import offline


class OfflineEntryPointTests(unittest.TestCase):
    def test_remote_msa_is_refused_before_cli_import(self) -> None:
        self.assertEqual(offline.main(["run-panel", "job.json", "--remote-msa"]), 2)

    def test_disable_network_sets_offline_environment(self) -> None:
        code = """
import os
import socket
from ppi_scout import offline
offline.disable_network()
assert os.environ["PPI_SCOUT_OFFLINE"] == "1"
assert os.environ["HF_HUB_OFFLINE"] == "1"
try:
    socket.create_connection(("127.0.0.1", 9))
except offline.NetworkDisabledError:
    print("blocked")
else:
    raise SystemExit("network was not blocked")
"""
        completed = subprocess.run(
            [sys.executable, "-c", code],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "blocked")


if __name__ == "__main__":
    unittest.main()
