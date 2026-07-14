#!/usr/bin/env python3
"""Validate the fixed public Atg8–Yta7 HelixFold3 cloud panel."""

from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ATG8_SEQUENCE = (
    "MKSTFKSEYPFEKRKAESERIADRFKNRIPVICEKAEKSDIPEIDKRKYLVPADLTVGQF"
    "VYVIRKRIMLPPEKAIFIFVNDTLPPTAALMSAIYQEHKDKDGFLYVTYSGENTFGR"
)
ATG8_SHA256 = "06254f6852b1b1dfc3c6916b19e20fb0272536cf45cfd125418c976aba2782ce"
STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")

EXPECTED_JOBS = (
    (
        "yta7-atg8-wt",
        "wt",
        "wild_type",
        "SLRKINYAEIEKVFDFLEDDQVMD",
        "b9761a62123d129167e43d60975acc3e21e2fc100c371b621babc79c96be5df7",
    ),
    (
        "yta7-atg8-yaei-anchor-mut",
        "yaei_anchor_mutant",
        "matched_negative_control",
        "SLRKINAAEAEKVFDFLEDDQVMD",
        "966d3c60e362aaddcb08d4053b21fdbb0e1f59f0be3861934de2df1030ab2b99",
    ),
    (
        "yta7-atg8-fdfl-anchor-mut",
        "fdfl_anchor_mutant",
        "matched_negative_control",
        "SLRKINYAEIEKVADFAEDDQVMD",
        "09ada9543cdbef3965cdbfcc5b5f83ae2582ead889ffe90e32c91cc73afafb5d",
    ),
    (
        "yta7-atg8-double-anchor-mut",
        "double_anchor_mutant",
        "matched_negative_control",
        "SLRKINAAEAEKVADFAEDDQVMD",
        "407f157a18caa5ca0096f27a943570551eaeba93088d29c13c6aad021b3a2b4e",
    ),
    (
        "yta7-atg8-composition-scramble",
        "composition_scramble",
        "composition_matched_negative_control",
        "DYFNSDDKIQDKEVRLIMELEFVA",
        "2ffc856c29d6091d411dcf595a14be88737120781fc405445a999aaf5f197831",
    ),
)


def sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()


def _expect(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def _valid_sequence(errors: list[str], sequence: Any, label: str) -> None:
    _expect(errors, isinstance(sequence, str), f"{label} sequence must be a string")
    if isinstance(sequence, str):
        invalid = sorted(set(sequence) - STANDARD_AMINO_ACIDS)
        _expect(errors, not invalid, f"{label} sequence has invalid residues: {invalid}")


def validate_panel(panel: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(panel, dict):
        return ["top-level JSON value must be an object"]

    _expect(
        errors,
        panel.get("format") == "ppi-scout.helixfold3-cloud-panel.v1",
        "unexpected panel format",
    )
    _expect(
        errors,
        panel.get("panel_id") == "scer-atg8-yta7-40-63-controls",
        "unexpected panel_id",
    )

    provider = panel.get("provider")
    if not isinstance(provider, dict):
        errors.append("provider must be an object")
    else:
        expected_provider = {
            "name": "PaddleHelix",
            "service": "HelixFold3",
            "server_url": "https://paddlehelix.baidu.com/app/all/helixfold3/forecast",
            "model_policy": "newest stable production HelixFold3 model available at submission time",
            "minimum_model": "HelixFold3.2",
            "submission_mode": "authenticated_official_web_or_documented_official_paid_api",
        }
        for key, value in expected_provider.items():
            _expect(errors, provider.get(key) == value, f"provider.{key} is not authoritative")

    governance = panel.get("data_governance")
    if not isinstance(governance, dict):
        errors.append("data_governance must be an object")
    else:
        _expect(
            errors,
            governance.get("classification") == "public_reference_sequences",
            "data classification must be public_reference_sequences",
        )
        _expect(
            errors,
            governance.get("allowed_provider")
            == "PaddleHelix official HelixFold3 service only",
            "allowed provider is not restricted to official PaddleHelix HelixFold3",
        )
        _expect(
            errors,
            governance.get("credentials_permitted_in_manifest") is False,
            "credentials_permitted_in_manifest must be false",
        )

    design = panel.get("design")
    if not isinstance(design, dict):
        errors.append("design must be an object")
    else:
        _expect(
            errors,
            design.get("independent_job_required_for_each_variant") is True,
            "each variant must require an independent job",
        )
        _expect(
            errors,
            design.get("combine_variants_in_one_complex") is False,
            "variants must not be combined in one complex",
        )

    entity_a = panel.get("entity_a")
    if not isinstance(entity_a, dict):
        errors.append("entity_a must be an object")
    else:
        sequence_a = entity_a.get("sequence")
        _valid_sequence(errors, sequence_a, "entity_a")
        _expect(errors, entity_a.get("requested_chain_label") == "A", "entity_a chain must be A")
        _expect(errors, entity_a.get("name") == "Atg8", "entity_a must be Atg8")
        _expect(
            errors,
            entity_a.get("uniprot_accession") == "P38182",
            "entity_a UniProt accession must be P38182",
        )
        _expect(errors, sequence_a == ATG8_SEQUENCE, "entity_a sequence is not the fixed P38182 sequence")
        _expect(errors, entity_a.get("length") == 117, "entity_a length must be 117")
        _expect(errors, entity_a.get("sha256") == ATG8_SHA256, "entity_a stored SHA-256 is incorrect")
        if isinstance(sequence_a, str):
            _expect(errors, len(sequence_a) == 117, "entity_a sequence length is not 117")
            _expect(errors, sha256(sequence_a) == ATG8_SHA256, "entity_a sequence SHA-256 mismatch")

    jobs = panel.get("jobs")
    if not isinstance(jobs, list):
        errors.append("jobs must be an array")
        return errors

    _expect(errors, len(jobs) == 5, "panel must contain exactly five jobs")
    expected_ids = [row[0] for row in EXPECTED_JOBS]
    actual_ids = [job.get("id") if isinstance(job, dict) else None for job in jobs]
    _expect(errors, actual_ids == expected_ids, "job IDs or job order differ from the authoritative panel")
    _expect(errors, len(set(actual_ids)) == len(actual_ids), "job IDs must be unique")

    by_id = {job.get("id"): job for job in jobs if isinstance(job, dict)}
    for job_id, variant, role, expected_sequence, expected_hash in EXPECTED_JOBS:
        job = by_id.get(job_id)
        if not isinstance(job, dict):
            errors.append(f"missing job {job_id}")
            continue
        _expect(errors, job.get("variant") == variant, f"{job_id} variant is incorrect")
        _expect(errors, job.get("hypothesis_role") == role, f"{job_id} hypothesis_role is incorrect")

        entity_b = job.get("entity_b")
        if not isinstance(entity_b, dict):
            errors.append(f"{job_id}.entity_b must be an object")
            continue
        sequence_b = entity_b.get("sequence")
        _valid_sequence(errors, sequence_b, f"{job_id}.entity_b")
        _expect(
            errors,
            entity_b.get("requested_chain_label") == "B",
            f"{job_id} entity_b chain must be B",
        )
        _expect(errors, sequence_b == expected_sequence, f"{job_id} sequence is not authoritative")
        _expect(errors, entity_b.get("length") == 24, f"{job_id} stored length must be 24")
        _expect(errors, entity_b.get("sha256") == expected_hash, f"{job_id} stored SHA-256 is incorrect")
        if isinstance(sequence_b, str):
            _expect(errors, len(sequence_b) == 24, f"{job_id} sequence length is not 24")
            _expect(errors, sha256(sequence_b) == expected_hash, f"{job_id} sequence SHA-256 mismatch")

        receipt = job.get("receipt")
        if not isinstance(receipt, dict):
            errors.append(f"{job_id}.receipt must be an object")
        else:
            _expect(errors, receipt.get("status") == "not_submitted", f"{job_id} must start not_submitted")
            for key in ("provider_job_id", "result_url", "model_label", "submitted_at"):
                _expect(errors, receipt.get(key) is None, f"{job_id}.receipt.{key} must start null")

    sequences = {
        job_id: sequence
        for job_id, _, _, sequence, _ in EXPECTED_JOBS
    }
    wt = sequences["yta7-atg8-wt"]
    expected_mutations = {
        "yta7-atg8-yaei-anchor-mut": {6: "A", 9: "A"},
        "yta7-atg8-fdfl-anchor-mut": {13: "A", 16: "A"},
        "yta7-atg8-double-anchor-mut": {6: "A", 9: "A", 13: "A", 16: "A"},
    }
    for job_id, mutations in expected_mutations.items():
        control = sequences[job_id]
        differences = {index: residue for index, residue in enumerate(control) if residue != wt[index]}
        _expect(errors, differences == mutations, f"{job_id} anchor mutations are incorrect")

    scramble = sequences["yta7-atg8-composition-scramble"]
    _expect(errors, Counter(scramble) == Counter(wt), "scramble is not composition matched to WT")
    _expect(errors, scramble != wt, "scramble must differ from WT")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)

    try:
        panel = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"INVALID: cannot read manifest: {exc}", file=sys.stderr)
        return 1

    errors = validate_panel(panel)
    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        return 1

    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
