"""Deterministic nested peptide and matched-control design."""

from __future__ import annotations

from collections import Counter
import hashlib
import random
import re
from typing import Iterable

from .models import PeptidePanel, PeptideVariant
from .resolver import normalize_sequence


CANONICAL_AIM = re.compile(r"[WFY]..[LIV]")


def _window_bounds(parent_length: int, motif_start: int, motif_end: int, requested: int) -> tuple[int, int]:
    motif_length = motif_end - motif_start + 1
    if requested < motif_length:
        raise ValueError(f"Window {requested} is shorter than the motif ({motif_length}).")
    size = min(parent_length, requested)
    left = (size - motif_length) // 2
    start = motif_start - left
    end = start + size - 1
    if start < 1:
        start = 1
        end = size
    if end > parent_length:
        end = parent_length
        start = parent_length - size + 1
    return start, end


def _replace_core(peptide: str, start: int, end: int, replacement: str) -> str:
    if len(replacement) != end - start + 1:
        raise ValueError("Replacement length must equal motif length.")
    return peptide[: start - 1] + replacement + peptide[end:]


def _variant(
    *,
    window: int,
    parent_start: int,
    parent_end: int,
    motif_start_in_peptide: int,
    motif_end_in_peptide: int,
    kind: str,
    sequence: str,
    mutation: str | None = None,
    ordinal: int | None = None,
) -> PeptideVariant:
    suffix = f"-{ordinal:02d}" if ordinal is not None else ""
    return PeptideVariant(
        variant_id=f"w{window}-{kind.replace('_', '-')}{suffix}",
        kind=kind,
        requested_window=window,
        actual_window=len(sequence),
        parent_start=parent_start,
        parent_end=parent_end,
        motif_start_in_peptide=motif_start_in_peptide,
        motif_end_in_peptide=motif_end_in_peptide,
        sequence=sequence,
        mutation=mutation,
    )


def _clean_scrambles(
    sequence: str,
    rng: random.Random,
    *,
    count: int,
) -> tuple[list[str], bool]:
    controls: list[str] = []
    seen = {sequence}
    attempts = 0
    maximum = max(2000, count * 1000)
    residues = list(sequence)
    while len(controls) < count and attempts < maximum:
        attempts += 1
        candidate_residues = residues.copy()
        rng.shuffle(candidate_residues)
        candidate = "".join(candidate_residues)
        if candidate in seen or CANONICAL_AIM.search(candidate):
            continue
        if Counter(candidate) != Counter(sequence):
            continue
        seen.add(candidate)
        controls.append(candidate)
    return controls, len(controls) == count


def design_peptide_panel(
    parent_sequence: str,
    motif_start: int,
    motif_end: int,
    *,
    window_sizes: Iterable[int] = (16, 24, 34),
    seed: int = 17,
    scramble_count: int = 3,
) -> PeptidePanel:
    """Create nested windows with auditable controls.

    Coordinates are 1-based inclusive. The function does not claim that the
    motif is functional; it only creates a controlled structural screen.
    """

    parent = normalize_sequence(parent_sequence)
    if motif_start < 1 or motif_end < motif_start or motif_end > len(parent):
        raise ValueError("Motif coordinates are outside the parent sequence.")
    motif = parent[motif_start - 1 : motif_end]
    requested_windows = tuple(dict.fromkeys(int(value) for value in window_sizes))
    if not requested_windows or any(value <= 0 for value in requested_windows):
        raise ValueError("At least one positive peptide window is required.")
    if scramble_count < 0:
        raise ValueError("scramble_count must be non-negative.")

    rng = random.Random(seed)
    variants: list[PeptideVariant] = []
    warnings: list[str] = [
        "Reverse-core variants are decoys, not guaranteed biological negatives.",
        "Peptide predictions do not establish motif accessibility in the full-length protein.",
    ]

    for window in requested_windows:
        parent_start, parent_end = _window_bounds(len(parent), motif_start, motif_end, window)
        wt = parent[parent_start - 1 : parent_end]
        relative_start = motif_start - parent_start + 1
        relative_end = motif_end - parent_start + 1
        if len(wt) < window:
            warnings.append(
                f"Requested window {window} was truncated to the available parent length {len(wt)}."
            )
        variants.append(
            _variant(
                window=window,
                parent_start=parent_start,
                parent_end=parent_end,
                motif_start_in_peptide=relative_start,
                motif_end_in_peptide=relative_end,
                kind="wt",
                sequence=wt,
            )
        )

        if len(motif) == 4:
            anchor_1 = "A" + motif[1:]
            anchor_2 = motif[:3] + "A"
            replacements = (
                ("anchor_1_to_a", anchor_1, f"{motif}->{anchor_1}"),
                ("anchor_2_to_a", anchor_2, f"{motif}->{anchor_2}"),
                ("double_anchor_to_a", "A" + motif[1:3] + "A", f"{motif}->AxxA"),
                ("core_to_aaaa", "AAAA", f"{motif}->AAAA"),
                ("reverse_decoy", motif[::-1], f"{motif}->{motif[::-1]}"),
            )
            for kind, replacement, mutation in replacements:
                variants.append(
                    _variant(
                        window=window,
                        parent_start=parent_start,
                        parent_end=parent_end,
                        motif_start_in_peptide=relative_start,
                        motif_end_in_peptide=relative_end,
                        kind=kind,
                        sequence=_replace_core(wt, relative_start, relative_end, replacement),
                        mutation=mutation,
                    )
                )
        else:
            warnings.append(
                f"Window {window}: anchor and AAAA controls were skipped because the motif is not four residues."
            )

        before = list(wt[: relative_start - 1])
        after = list(wt[relative_end:])
        rng.shuffle(before)
        rng.shuffle(after)
        flank_scramble = "".join(before) + motif + "".join(after)
        if flank_scramble != wt:
            variants.append(
                _variant(
                    window=window,
                    parent_start=parent_start,
                    parent_end=parent_end,
                    motif_start_in_peptide=relative_start,
                    motif_end_in_peptide=relative_end,
                    kind="flank_scramble",
                    sequence=flank_scramble,
                    mutation="native motif retained; flanks independently shuffled",
                )
            )

        scrambles, complete = _clean_scrambles(wt, rng, count=scramble_count)
        for index, sequence in enumerate(scrambles, start=1):
            variants.append(
                _variant(
                    window=window,
                    parent_start=parent_start,
                    parent_end=parent_end,
                    motif_start_in_peptide=relative_start,
                    motif_end_in_peptide=relative_end,
                    kind="clean_scramble",
                    sequence=sequence,
                    mutation="composition-matched; canonical AIM pattern excluded",
                    ordinal=index,
                )
            )
        if not complete:
            warnings.append(
                f"Window {window}: only {len(scrambles)} of {scramble_count} requested clean scrambles could be generated."
            )

    return PeptidePanel(
        design_version="1.0",
        coordinate_system="1-based inclusive",
        parent_sequence_sha256=hashlib.sha256(parent.encode("ascii")).hexdigest(),
        parent_length=len(parent),
        motif_sequence=motif,
        motif_start=motif_start,
        motif_end=motif_end,
        window_sizes=requested_windows,
        variants=tuple(variants),
        warnings=tuple(dict.fromkeys(warnings)),
    )
