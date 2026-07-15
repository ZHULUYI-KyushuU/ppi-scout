"""Resolve audited receptor MSAs from a sequence-addressed local library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .resolver import normalize_sequence, sequence_hash


@dataclass(frozen=True)
class LocalMSAResolution:
    """Outcome of an exact-sequence lookup in a local A3M library."""

    library: Path
    receptor_sequence_sha256: str
    path: Path | None

    @property
    def matched(self) -> bool:
        return self.path is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "library": str(self.library),
            "receptor_sequence_sha256": self.receptor_sequence_sha256,
            "matched": self.matched,
            "path": str(self.path) if self.path is not None else None,
        }


def read_a3m_query(path: Path) -> str:
    """Read and normalize the first (query) sequence in an A3M file."""

    saw_header = False
    chunks: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(">"):
            if saw_header:
                break
            saw_header = True
            continue
        if not saw_header:
            raise ValueError(f"A3M sequence appeared before a header: {path}")
        chunks.append(line)
    if not saw_header or not chunks:
        raise ValueError(f"A3M file has no query sequence: {path}")

    # A3M lowercase characters are insertions relative to the query. Dots and
    # dashes are alignment gaps and are not part of the ungapped query.
    ungapped = "".join(
        character
        for character in "".join(chunks)
        if not character.islower() and character not in {".", "-"}
    )
    try:
        return normalize_sequence(ungapped)
    except ValueError as exc:
        raise ValueError(f"Invalid A3M query in {path}: {exc}") from exc


def resolve_receptor_msa(library: Path, receptor_sequence: str) -> LocalMSAResolution:
    """Return ``<sequence-sha256>.a3m`` only when its query is an exact match."""

    root = library.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Local MSA library directory does not exist: {root}")
    normalized = normalize_sequence(receptor_sequence)
    digest = sequence_hash(normalized)
    candidate = root / f"{digest}.a3m"
    if not candidate.is_file():
        return LocalMSAResolution(root, digest, None)
    query = read_a3m_query(candidate)
    if query != normalized:
        raise ValueError(
            "Local MSA query does not exactly match the receptor sequence "
            f"for hash {digest}: {candidate}"
        )
    return LocalMSAResolution(root, digest, candidate.resolve())
