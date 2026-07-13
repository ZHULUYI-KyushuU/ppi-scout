"""Resolve explicit protein inputs without silently guessing identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AA_ALPHABET = frozenset("ACDEFGHIKLMNPQRSTVWYX")


@dataclass(frozen=True)
class ResolvedProtein:
    name: str
    sequence: str
    source_type: str
    source_value: str
    accession: str | None = None
    organism: str | None = None
    sequence_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_sequence(sequence: str) -> str:
    normalized = "".join(sequence.split()).upper()
    if not normalized:
        raise ValueError("Protein sequence is empty.")
    invalid = sorted(set(normalized) - AA_ALPHABET)
    if invalid:
        raise ValueError(f"Protein sequence contains invalid residues: {', '.join(invalid)}")
    return normalized


def sequence_hash(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def parse_fasta(text: str) -> tuple[str, str]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    chunks: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            if header is not None:
                records.append((header, normalize_sequence("".join(chunks))))
            header = stripped[1:].strip() or "unnamed"
            chunks = []
        else:
            if header is None:
                raise ValueError("FASTA sequence appeared before a header line.")
            chunks.append(stripped)
    if header is not None:
        records.append((header, normalize_sequence("".join(chunks))))
    if len(records) != 1:
        raise ValueError(f"Expected exactly one FASTA record, found {len(records)}.")
    return records[0]


def resolve_inline(name: str, sequence: str, organism: str | None = None) -> ResolvedProtein:
    normalized = normalize_sequence(sequence)
    return ResolvedProtein(
        name=name,
        sequence=normalized,
        source_type="sequence",
        source_value="inline",
        organism=organism,
        sequence_sha256=sequence_hash(normalized),
    )


def resolve_fasta(path: Path, organism: str | None = None) -> ResolvedProtein:
    header, sequence = parse_fasta(path.read_text(encoding="utf-8"))
    return ResolvedProtein(
        name=header.split()[0],
        sequence=sequence,
        source_type="fasta",
        source_value=str(path),
        organism=organism,
        sequence_sha256=sequence_hash(sequence),
    )


def _default_json_get(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ppi-scout/0.1"})
    with urlopen(request, timeout=20) as response:  # nosec: B310 - fixed HTTPS service below
        return json.loads(response.read().decode("utf-8"))


def resolve_uniprot_accession(
    accession: str,
    *,
    fetch_json: Callable[[str], dict[str, Any]] = _default_json_get,
) -> ResolvedProtein:
    clean = accession.strip()
    if not clean:
        raise ValueError("UniProt accession is empty.")
    payload = fetch_json(f"https://rest.uniprot.org/uniprotkb/{clean}.json")
    sequence = normalize_sequence(payload["sequence"]["value"])
    genes = payload.get("genes") or []
    gene_name = None
    if genes:
        gene_name = genes[0].get("geneName", {}).get("value")
    organism = payload.get("organism", {}).get("scientificName")
    resolved_accession = payload.get("primaryAccession", clean)
    return ResolvedProtein(
        name=gene_name or payload.get("uniProtkbId", resolved_accession),
        sequence=sequence,
        source_type="uniprot",
        source_value=clean,
        accession=resolved_accession,
        organism=organism,
        sequence_sha256=sequence_hash(sequence),
    )


def search_uniprot_gene(
    gene: str,
    organism_id: int | str,
    *,
    fetch_json: Callable[[str], dict[str, Any]] = _default_json_get,
) -> list[dict[str, Any]]:
    """Return candidates; identity selection remains the caller's decision."""

    clean_gene = gene.strip()
    if not clean_gene:
        raise ValueError("Gene name is empty.")
    params = urlencode(
        {
            "query": f"gene_exact:{clean_gene} AND organism_id:{organism_id}",
            "format": "json",
            "fields": "accession,id,gene_names,organism_name,length,sequence",
            "size": 10,
        }
    )
    payload = fetch_json(f"https://rest.uniprot.org/uniprotkb/search?{params}")
    candidates: list[dict[str, Any]] = []
    for result in payload.get("results", []):
        sequence = result.get("sequence", {}).get("value")
        candidates.append(
            {
                "accession": result.get("primaryAccession"),
                "entry_id": result.get("uniProtkbId"),
                "organism": result.get("organism", {}).get("scientificName"),
                "length": result.get("sequence", {}).get("length"),
                "sequence_sha256": sequence_hash(normalize_sequence(sequence)) if sequence else None,
            }
        )
    return candidates
