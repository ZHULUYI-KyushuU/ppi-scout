"""Compile a reviewed motif-peptide job into an auditable Boltz panel."""

from __future__ import annotations

import hashlib
import json
import platform
from typing import Any, Sequence

from .peptide_design import design_peptide_panel
from .resolver import normalize_sequence


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _positive(value: int, name: str) -> int:
    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def _resolve_engine(
    *,
    accelerator: str,
    no_kernels: bool | None,
    prediction_seed: int,
    recycling_steps: int,
    sampling_steps: int,
    diffusion_samples: int,
) -> tuple[dict[str, Any], list[str]]:
    if accelerator not in {"auto", "gpu", "cpu", "tpu"}:
        raise ValueError("accelerator must be auto, gpu, cpu, or tpu.")
    apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"
    resolved_accelerator = "gpu" if accelerator == "auto" and apple_silicon else accelerator
    kernels_disabled = apple_silicon if no_kernels is None else bool(no_kernels)

    settings = {
        "model": "boltz2",
        "accelerator": resolved_accelerator,
        "devices": 1,
        "prediction_seed": _positive(prediction_seed, "prediction_seed"),
        "recycling_steps": _positive(recycling_steps, "recycling_steps"),
        "sampling_steps": _positive(sampling_steps, "sampling_steps"),
        "diffusion_samples": _positive(diffusion_samples, "diffusion_samples"),
        "no_kernels": kernels_disabled,
    }
    argv = [
        "--model",
        "boltz2",
        "--devices",
        "1",
        "--seed",
        str(settings["prediction_seed"]),
        "--recycling_steps",
        str(settings["recycling_steps"]),
        "--sampling_steps",
        str(settings["sampling_steps"]),
        "--diffusion_samples",
        str(settings["diffusion_samples"]),
    ]
    if resolved_accelerator != "auto":
        argv.extend(("--accelerator", resolved_accelerator))
    if kernels_disabled:
        argv.append("--no_kernels")
    return settings, argv


def build_panel_manifest(
    job: dict[str, Any],
    *,
    windows: Sequence[int],
    design_seed: int = 17,
    prediction_seed: int = 17,
    scramble_count: int = 3,
    remote_msa: bool = False,
    receptor_msa: str | None = None,
    output_format: str = "pdb",
    accelerator: str = "auto",
    no_kernels: bool | None = None,
    recycling_steps: int = 3,
    sampling_steps: int = 200,
    diffusion_samples: int = 1,
) -> dict[str, Any]:
    """Build independent, matched Boltz tasks from one reviewed motif job."""

    route = str(job.get("routing", {}).get("route", "")).replace("-", "_")
    if route != "motif_peptide":
        raise ValueError("run-panel requires a reviewed job with routing.route=motif_peptide.")
    proteins = job.get("inputs", {}).get("proteins", [])
    if not isinstance(proteins, list) or len(proteins) != 2:
        raise ValueError("run-panel requires exactly two resolved protein inputs.")

    hypothesis = job.get("hypothesis")
    if not isinstance(hypothesis, dict):
        raise ValueError("run-panel requires a recorded motif hypothesis.")
    motif_owner = str(hypothesis.get("motif_owner", "")).upper()
    if motif_owner not in {"A", "B"}:
        raise ValueError("The motif hypothesis must identify motif_owner as A or B.")
    by_id = {str(item.get("id", "")).upper(): item for item in proteins}
    if set(by_id) != {"A", "B"}:
        raise ValueError("run-panel requires unique protein chain IDs A and B.")
    if any(not item.get("sequence") for item in proteins):
        raise ValueError("run-panel requires exact sequences for both proteins.")

    raw_region = hypothesis.get("motif_region")
    if not isinstance(raw_region, (list, tuple)) or len(raw_region) != 2:
        raise ValueError("The motif hypothesis must record a 1-based inclusive motif_region.")
    try:
        motif_start, motif_end = (int(raw_region[0]), int(raw_region[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError("motif_region must contain two integers.") from exc

    owner = by_id[motif_owner]
    receptor_id = "A" if motif_owner == "B" else "B"
    receptor = by_id[receptor_id]
    parent_sequence = normalize_sequence(str(owner["sequence"]))
    receptor_sequence = normalize_sequence(str(receptor["sequence"]))
    if motif_start < 1 or motif_end < motif_start or motif_end > len(parent_sequence):
        raise ValueError("The recorded motif_region lies outside the motif-owner sequence.")
    motif_sequence = parent_sequence[motif_start - 1 : motif_end]
    recorded_motif = hypothesis.get("motif_sequence") or job.get("routing", {}).get("selected_motif")
    if recorded_motif and normalize_sequence(str(recorded_motif)) != motif_sequence:
        raise ValueError(
            f"Recorded motif {recorded_motif} does not match residues "
            f"{motif_start}:{motif_end} ({motif_sequence})."
        )

    requested_windows = tuple(dict.fromkeys(_positive(int(value), "window") for value in windows))
    if not requested_windows:
        raise ValueError("At least one peptide window is required.")
    _positive(design_seed, "design_seed")
    if scramble_count < 3:
        raise ValueError("scramble_count must be at least 3 for a matched control panel.")
    if remote_msa and receptor_msa:
        raise ValueError("Choose either --remote-msa or --receptor-msa, not both.")
    if output_format not in {"pdb", "mmcif"}:
        raise ValueError("output_format must be pdb or mmcif.")

    panel = design_peptide_panel(
        parent_sequence,
        motif_start,
        motif_end,
        window_sizes=requested_windows,
        seed=design_seed,
        scramble_count=scramble_count,
    )
    engine_settings, engine_args = _resolve_engine(
        accelerator=accelerator,
        no_kernels=no_kernels,
        prediction_seed=prediction_seed,
        recycling_steps=recycling_steps,
        sampling_steps=sampling_steps,
        diffusion_samples=diffusion_samples,
    )

    if remote_msa:
        receptor_msa_value = "remote"
        msa_mode = "remote"
    elif receptor_msa:
        receptor_msa_value = receptor_msa
        msa_mode = "local_precomputed"
    else:
        receptor_msa_value = "empty"
        msa_mode = "single_sequence"

    tasks: list[dict[str, Any]] = []
    for variant in panel.variants:
        variant_payload = variant.to_dict()
        tasks.append(
            {
                "id": variant.variant_id,
                "name": f"{job.get('name', 'ppi-panel')}-{variant.variant_id}",
                "variant": variant_payload,
                "chains": [
                    {
                        "id": receptor_id,
                        "name": receptor.get("name") or receptor_id,
                        "sequence": receptor_sequence,
                        "msa": receptor_msa_value,
                    },
                    {
                        "id": motif_owner,
                        "name": f"{owner.get('name') or motif_owner}-{variant.variant_id}",
                        "sequence": variant.sequence,
                        "msa": "empty",
                    },
                ],
            }
        )

    panel_payload = panel.to_dict()
    return {
        "schema_version": "1.0",
        "kind": "motif_peptide_boltz_panel",
        "name": f"{job.get('name', 'ppi-panel')}-panel",
        "source_job_sha256": _json_hash(job),
        "coordinate_system": "1-based inclusive",
        "organism": job.get("inputs", {}).get("organism"),
        "routing": job.get("routing"),
        "hypothesis": {
            **hypothesis,
            "motif_owner": motif_owner,
            "motif_sequence": motif_sequence,
            "motif_region": [motif_start, motif_end],
            "receptor_chain": receptor_id,
        },
        "peptide_design": {
            "design_seed": design_seed,
            "scramble_count": scramble_count,
            "panel": panel_payload,
        },
        "execution": {
            "backend": "boltz2",
            "output_format": output_format,
            "engine_settings": engine_settings,
            "engine_args": engine_args,
        },
        "engine_args": engine_args,
        "output_format": output_format,
        "remote_msa": bool(remote_msa),
        "remote_msa_allowed": bool(remote_msa),
        "msa": {
            "mode": msa_mode,
            "receptor_msa": receptor_msa_value,
            "peptide_msa": "empty",
        },
        "privacy": {
            "local_first": not remote_msa,
            "external_sequence_upload": bool(remote_msa),
            "sequence_upload_authorized": bool(remote_msa),
        },
        "prediction_jobs": tasks,
        "warnings": list(panel.warnings)
        + (["Remote MSA sends protein sequence data to the configured MSA service."] if remote_msa else [])
        + (["Single-sequence mode avoids remote MSA upload but can reduce prediction accuracy."] if msa_mode == "single_sequence" else []),
    }
