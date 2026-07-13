"""Conservative, deterministic sequence scan for canonical AIM/LIR patterns.

This module deliberately uses sequence identity only.  It does not infer motif
function, solvent exposure, disorder, phosphorylation, or binding.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from .resolver import normalize_sequence


CANONICAL_AIM_LIR_PATTERN = r"[WFY]xx[LIV]"
_OVERLAPPING_AIM_LIR = re.compile(r"(?=([WFY]..[LIV]))")


@dataclass(frozen=True)
class AimLirCandidate:
    """One canonical sequence-pattern match, using 1-based coordinates."""

    candidate_id: str
    candidate_key: str
    rank: int
    start_1based: int
    end_1based: int
    core_sequence: str
    flank_start_1based: int
    flank_end_1based: int
    flank_sequence: str
    sequence_score: float
    acidic_flank_count: int
    serine_threonine_flank_count: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AimLirScanResult:
    """Auditable result containing every canonical AIM/LIR sequence match."""

    scan_version: str
    coordinate_system: str
    motif_pattern: str
    sequence_length: int
    flank_size: int
    scoring_rule: str
    candidate_id_rule: str
    rank_rule: str
    candidates: tuple[AimLirCandidate, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _candidate_key(core_start: int, core_end: int, core_sequence: str) -> str:
    """Return an audit key stable across repeated scans of the same parent sequence."""

    return f"aim-lir-{core_start:06d}-{core_end:06d}-{core_sequence}"


def scan_aim_lir(sequence: str, flank_size: int = 6) -> AimLirScanResult:
    """Find and sequence-rank all canonical ``[WFY]xx[LIV]`` matches.

    The transparent score is ``4 + acidic flank residues + 0.5 * S/T flank
    residues``.  The four-point base records only that the canonical pattern
    matched.  D/E and S/T are counted outside the four-residue core, within the
    requested flank on each side.  The score is a sequence-screening heuristic,
    not a probability or structural/functional claim.
    """

    parent = normalize_sequence(sequence)
    if isinstance(flank_size, bool) or not isinstance(flank_size, int) or flank_size < 0:
        raise ValueError("flank_size must be a non-negative integer.")

    provisional: list[dict[str, Any]] = []
    for ordinal, match in enumerate(_OVERLAPPING_AIM_LIR.finditer(parent), start=1):
        core_start = match.start() + 1
        core_end = core_start + 3
        core_sequence = match.group(1)
        flank_start = max(1, core_start - flank_size)
        flank_end = min(len(parent), core_end + flank_size)
        flank_sequence = parent[flank_start - 1 : flank_end]

        left_flank = parent[flank_start - 1 : core_start - 1]
        right_flank = parent[core_end:flank_end]
        scoring_flanks = left_flank + right_flank
        acidic_count = sum(residue in "DE" for residue in scoring_flanks)
        phospho_capable_count = sum(residue in "ST" for residue in scoring_flanks)
        sequence_score = 4.0 + acidic_count + (0.5 * phospho_capable_count)

        reasons = (
            "+4.0: canonical [WFY]xx[LIV] sequence pattern matched; this is sequence evidence only.",
            f"+{acidic_count:.1f}: {acidic_count} acidic D/E residue(s) in the reported flanks at +1.0 each.",
            (
                f"+{0.5 * phospho_capable_count:.1f}: {phospho_capable_count} S/T residue(s) "
                "in the reported flanks at +0.5 each; residue identity does not establish phosphorylation."
            ),
        )
        warnings: list[str] = []
        if core_start - flank_start < flank_size or flank_end - core_end < flank_size:
            warnings.append("The requested flank was truncated by a sequence terminus.")
        if "X" in flank_sequence:
            warnings.append("The reported flank contains X (an unknown/unspecified residue).")

        provisional.append(
            {
                "candidate_id": f"aim-{ordinal:03d}",
                "candidate_key": _candidate_key(core_start, core_end, core_sequence),
                "start_1based": core_start,
                "end_1based": core_end,
                "core_sequence": core_sequence,
                "flank_start_1based": flank_start,
                "flank_end_1based": flank_end,
                "flank_sequence": flank_sequence,
                "sequence_score": sequence_score,
                "acidic_flank_count": acidic_count,
                "serine_threonine_flank_count": phospho_capable_count,
                "reasons": reasons,
                "warnings": warnings,
            }
        )

    provisional.sort(
        key=lambda candidate: (
            -candidate["sequence_score"],
            candidate["start_1based"],
            candidate["end_1based"],
            candidate["core_sequence"],
        )
    )
    score_counts: dict[float, int] = {}
    for candidate in provisional:
        score = candidate["sequence_score"]
        score_counts[score] = score_counts.get(score, 0) + 1

    candidates: list[AimLirCandidate] = []
    last_score: float | None = None
    dense_rank = 0
    for candidate in provisional:
        score = candidate["sequence_score"]
        if score != last_score:
            dense_rank += 1
            last_score = score
        warnings = list(candidate["warnings"])
        if score_counts[score] > 1:
            warnings.append(
                "Sequence score is tied; tied candidates have the same rank and are displayed by ascending coordinates."
            )
        candidates.append(
            AimLirCandidate(
                candidate_id=candidate["candidate_id"],
                candidate_key=candidate["candidate_key"],
                rank=dense_rank,
                start_1based=candidate["start_1based"],
                end_1based=candidate["end_1based"],
                core_sequence=candidate["core_sequence"],
                flank_start_1based=candidate["flank_start_1based"],
                flank_end_1based=candidate["flank_end_1based"],
                flank_sequence=candidate["flank_sequence"],
                sequence_score=score,
                acidic_flank_count=candidate["acidic_flank_count"],
                serine_threonine_flank_count=candidate["serine_threonine_flank_count"],
                reasons=candidate["reasons"],
                warnings=tuple(warnings),
            )
        )

    global_warnings = [
        (
            "Candidates are canonical sequence-pattern matches only; this scan does not establish "
            "function, exposure, disorder, phosphorylation, interaction, or binding."
        ),
        "Sequence scores are heuristic prioritization values, not probabilities or confidence scores.",
    ]
    if "X" in parent:
        global_warnings.append("The input sequence contains X (unknown/unspecified residues).")
    if not candidates:
        global_warnings.append("No canonical [WFY]xx[LIV] sequence pattern was found.")

    return AimLirScanResult(
        scan_version="1.0",
        coordinate_system="1-based inclusive",
        motif_pattern=CANONICAL_AIM_LIR_PATTERN,
        sequence_length=len(parent),
        flank_size=flank_size,
        scoring_rule=(
            "4.0 for a canonical [WFY]xx[LIV] match, +1.0 per D/E and +0.5 per S/T "
            "outside the core within each reported flank"
        ),
        candidate_id_rule=(
            "aim-NNN IDs are assigned by ascending sequence position before ranking; "
            "the numeric ID is not a priority rank"
        ),
        rank_rule=(
            "dense rank by descending sequence_score; tied scores share a rank and are displayed "
            "by ascending start_1based, end_1based, then core_sequence"
        ),
        candidates=tuple(candidates),
        warnings=tuple(global_warnings),
    )
