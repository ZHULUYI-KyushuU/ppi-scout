"""Hard-offline entry point for portable PPI Scout bundles."""

from __future__ import annotations

import errno
import os
import socket
import sys
from typing import NoReturn, Sequence


class NetworkDisabledError(OSError):
    """Raised when a portable offline run attempts an IP network operation."""


_ORIGINAL_SOCKET = socket.socket
_NETWORK_DISABLED = False


def _blocked(*_args: object, **_kwargs: object) -> NoReturn:
    raise NetworkDisabledError(errno.ENETDOWN, "PPI Scout portable offline mode blocks network access")


class _OfflineSocket(_ORIGINAL_SOCKET):
    """Socket that preserves local IPC but rejects IPv4 and IPv6 traffic."""

    def _is_ip(self) -> bool:
        return self.family in {socket.AF_INET, socket.AF_INET6}

    def connect(self, address: object) -> None:
        if self._is_ip():
            _blocked(address)
        return super().connect(address)  # type: ignore[arg-type]

    def connect_ex(self, address: object) -> int:
        if self._is_ip():
            return errno.ENETDOWN
        return super().connect_ex(address)  # type: ignore[arg-type]

    def sendto(self, *args: object, **kwargs: object) -> int:
        if self._is_ip():
            _blocked(*args, **kwargs)
        return super().sendto(*args, **kwargs)  # type: ignore[arg-type]


def disable_network() -> None:
    """Disable Python IPv4/IPv6 networking for the current process."""

    global _NETWORK_DISABLED
    if _NETWORK_DISABLED:
        return
    os.environ.update(
        {
            "PPI_SCOUT_OFFLINE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "WANDB_MODE": "offline",
            "WANDB_DISABLED": "true",
        }
    )
    socket.socket = _OfflineSocket  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    _NETWORK_DISABLED = True


def main(argv: Sequence[str] | None = None) -> int:
    """Run the normal CLI after enforcing a process-wide network deny policy."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--remote-msa" in arguments:
        print("Portable offline mode refuses --remote-msa.", file=sys.stderr)
        return 2
    disable_network()
    from .cli import main as cli_main

    return cli_main(arguments)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
