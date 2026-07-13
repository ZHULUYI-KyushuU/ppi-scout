"""Auditable scientific inputs and decisions used by PPI Scout."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ProteinEvidence:
    name: str
    sequence: str | None = None
    residue_count: int | None = None
    known_domain: str | None = None
    domain_region: tuple[int, int] | None = None
    has_transmembrane_region: bool | None = None
    membrane_dependent: bool | None = None
    folded_interface_expected: bool | None = None
    intrinsically_disordered_region: tuple[int, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InteractionQuery:
    protein_a: ProteinEvidence
    protein_b: ProteinEvidence
    goal: str = "auto"
    question: str | None = None
    motif_sequence: str | None = None
    motif_region: tuple[int, int] | None = None
    motif_in_disorder: bool | None = None
    motif_exposed: bool | None = None
    receptor_has_motif_pocket: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutingDecision:
    route: str
    confidence: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    selected_region: tuple[int, int] | None = None
    selected_motif: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PeptideVariant:
    variant_id: str
    kind: str
    requested_window: int
    actual_window: int
    parent_start: int
    parent_end: int
    motif_start_in_peptide: int
    motif_end_in_peptide: int
    sequence: str
    mutation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PeptidePanel:
    design_version: str
    coordinate_system: str
    parent_sequence_sha256: str
    parent_length: int
    motif_sequence: str
    motif_start: int
    motif_end: int
    window_sizes: tuple[int, ...]
    variants: tuple[PeptideVariant, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
