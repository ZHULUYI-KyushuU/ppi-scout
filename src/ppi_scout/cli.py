"""Command-line interface for PPI Scout.

The planner and peptide designer are intentionally usable without a Boltz
installation. Heavy backends are imported only inside commands that need them,
so a new user can inspect and share a resolved job before spending GPU time.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import importlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

from . import __version__
from .i18n import SUPPORTED_LANGUAGES, Translator, choose_language, normalize_language
from .msa_library import LocalMSAResolution, resolve_receptor_msa


ROUTES = ("auto", "full-length", "domain", "motif-peptide")
_ALLOWED_RESIDUES = frozenset("ACDEFGHIKLMNPQRSTVWYX")


class CLIError(RuntimeError):
    """A concise, user-facing command error."""


def _safe_job_slug(value: Any) -> str:
    """Turn a human job name into one safe directory component."""

    cleaned = re.sub(r"[^\w.-]+", "-", str(value or ""), flags=re.UNICODE).strip("._-")
    return cleaned[:80] or "ppi-job"


def _jsonable(value: Any) -> Any:
    """Convert core dataclasses/enums/path objects to JSON-compatible values."""

    for method_name in ("to_dict", "as_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            return _jsonable(method())
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    enum_value = getattr(value, "value", None)
    if enum_value is not None and not isinstance(value, (str, bytes)):
        return _jsonable(enum_value)
    return value


def _clean_sequence(text: str, *, source: str = "sequence") -> str:
    lines = text.strip().splitlines()
    if any(line.lstrip().startswith(">") for line in lines):
        records: list[str] = []
        current: list[str] = []
        for line in lines:
            if line.lstrip().startswith(">"):
                if current:
                    records.append("".join(current))
                    current = []
                continue
            current.append("".join(line.split()))
        if current:
            records.append("".join(current))
        if len(records) != 1:
            raise CLIError(f"{source} must contain exactly one FASTA record.")
        sequence = records[0].upper()
    else:
        sequence = "".join(text.split()).upper()
    if not sequence:
        raise CLIError(f"{source} contains no amino-acid sequence.")
    invalid = sorted(set(sequence) - _ALLOWED_RESIDUES)
    if invalid:
        raise CLIError(f"{source} contains invalid residue characters: {''.join(invalid)}")
    return sequence


def _read_fasta(path_value: str) -> str:
    path = Path(path_value).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CLIError(f"Cannot read FASTA file {path}: {exc}") from exc
    return _clean_sequence(text, source=str(path))


def _looks_like_sequence(value: str) -> bool:
    compact = "".join(value.split()).upper()
    # Prefixes remain available for genuinely tiny peptides; this threshold
    # avoids treating ordinary protein names such as AIM or LC3 as sequences.
    return len(compact) >= 12 and bool(compact) and set(compact) <= _ALLOWED_RESIDUES


def _protein_from_free_text(value: str, chain_id: str) -> dict[str, Any]:
    raw = value.strip()
    if not raw:
        raise CLIError(f"Protein {chain_id} is required.")

    prefix, separator, payload = raw.partition(":")
    if separator and prefix.casefold() in {"name", "protein"}:
        return {"id": chain_id, "name": payload.strip(), "sequence": None, "source": "name"}
    if separator and prefix.casefold() in {"sequence", "seq"}:
        sequence = _clean_sequence(payload, source=f"protein {chain_id}")
        return {"id": chain_id, "name": chain_id, "sequence": sequence, "source": "sequence"}
    if separator and prefix.casefold() in {"fasta", "file"}:
        path = Path(payload.strip()).expanduser()
        return {
            "id": chain_id,
            "name": path.stem,
            "sequence": _read_fasta(str(path)),
            "source": "fasta",
            "source_path": str(path),
        }

    candidate_path = Path(raw).expanduser()
    try:
        is_file = candidate_path.is_file()
    except OSError:
        # Long inline sequences are not valid filesystem paths on many hosts.
        is_file = False
    if is_file:
        return {
            "id": chain_id,
            "name": candidate_path.stem,
            "sequence": _read_fasta(str(candidate_path)),
            "source": "fasta",
            "source_path": str(candidate_path),
        }
    if raw.startswith(">") or _looks_like_sequence(raw):
        sequence = _clean_sequence(raw, source=f"protein {chain_id}")
        return {"id": chain_id, "name": chain_id, "sequence": sequence, "source": "sequence"}
    return {"id": chain_id, "name": raw, "sequence": None, "source": "name"}


def _protein_from_args(args: argparse.Namespace, suffix: str, fallback: str | None) -> dict[str, Any]:
    chain_id = suffix.upper()
    sequence = getattr(args, f"sequence_{suffix}", None)
    fasta = getattr(args, f"fasta_{suffix}", None)
    name = getattr(args, f"protein_{suffix}", None)
    supplied = [value is not None for value in (sequence, fasta, name)]
    if sum(supplied) > 1:
        raise CLIError(
            f"Protein {chain_id}: choose only one of --protein-{suffix}, "
            f"--sequence-{suffix}, or --fasta-{suffix}."
        )
    if sequence is not None:
        clean = _clean_sequence(sequence, source=f"protein {chain_id}")
        return {"id": chain_id, "name": name or chain_id, "sequence": clean, "source": "sequence"}
    if fasta is not None:
        path = Path(fasta).expanduser()
        return {
            "id": chain_id,
            "name": path.stem,
            "sequence": _read_fasta(str(path)),
            "source": "fasta",
            "source_path": str(path),
        }
    if name is not None:
        return {"id": chain_id, "name": name.strip(), "sequence": None, "source": "name"}
    if fallback is None:
        raise CLIError(f"Protein {chain_id} is required.")
    return _protein_from_free_text(fallback, chain_id)


def _route_fallback(proteins: Sequence[dict[str, Any]], mode: str) -> dict[str, Any]:
    if mode != "auto":
        return {
            "route": mode.replace("-", "_"),
            "confidence": "user_selected",
            "reasons": ["The analysis route was selected explicitly by the user."],
            "warnings": [],
            "selected_region": None,
            "selected_motif": None,
        }
    sequences = [item.get("sequence") for item in proteins]
    if any(sequence is None for sequence in sequences):
        return {
            "route": "needs_review",
            "confidence": "low",
            "reasons": ["At least one protein is name-only and still requires sequence resolution."],
            "warnings": ["Resolve species-specific sequences before choosing a structural representation."],
            "selected_region": None,
            "selected_motif": None,
        }
    return {
        "route": "needs_review",
        "confidence": "low",
        "reasons": ["The scientific routing module is unavailable, so sequence length was not used as a proxy."],
        "warnings": ["Review domain, disorder, motif, and membrane context before live execution."],
        "selected_region": None,
        "selected_motif": None,
    }


def _route_with_core(
    proteins: Sequence[dict[str, Any]],
    mode: str,
    *,
    motif_sequence: str | None = None,
    motif_region: tuple[int, int] | None = None,
    motif_in_disorder: bool | None = None,
    motif_exposed: bool | None = None,
    receptor_has_motif_pocket: bool | None = None,
) -> dict[str, Any]:
    """Call the stable science-core API; retain a conservative thin fallback."""

    try:
        models = importlib.import_module("ppi_scout.models")
        router = importlib.import_module("ppi_scout.router")
        ProteinEvidence = getattr(models, "ProteinEvidence")
        InteractionQuery = getattr(models, "InteractionQuery")
        route_interaction = getattr(router, "route_interaction")
    except (ImportError, AttributeError):
        return _route_fallback(proteins, mode)

    evidence = []
    for protein in proteins:
        sequence = protein.get("sequence")
        evidence.append(
            ProteinEvidence(
                name=protein.get("name") or protein["id"],
                sequence=sequence,
                residue_count=len(sequence) if sequence else None,
            )
        )
    goal = mode.replace("-", "_")
    try:
        decision = route_interaction(
            InteractionQuery(
                evidence[0],
                evidence[1],
                goal=goal,
                motif_sequence=motif_sequence,
                motif_region=motif_region,
                motif_in_disorder=motif_in_disorder,
                motif_exposed=motif_exposed,
                receptor_has_motif_pocket=receptor_has_motif_pocket,
            )
        )
    except (TypeError, ValueError) as exc:
        fallback = _route_fallback(proteins, mode)
        fallback["warnings"].append(f"Science-core routing could not be completed: {exc}")
        return fallback
    payload = _jsonable(decision)
    if not isinstance(payload, dict):
        raise CLIError("The science-core router returned an unsupported result.")
    return payload


def create_job(
    protein_a: dict[str, Any],
    protein_b: dict[str, Any],
    *,
    language: str,
    organism: str | None = None,
    mode: str = "auto",
    name: str | None = None,
    motif_owner: str | None = None,
    motif_sequence: str | None = None,
    motif_region: tuple[int, int] | None = None,
    motif_context: str | None = None,
    receptor_has_motif_pocket: bool | None = None,
) -> dict[str, Any]:
    proteins = [protein_a, protein_b]
    motif_in_disorder = True if motif_context == "disordered" else None
    if motif_context == "buried":
        motif_in_disorder = False
    motif_exposed = True if motif_context == "exposed" else None
    if motif_context == "buried":
        motif_exposed = False
    routing = _route_with_core(
        proteins,
        mode,
        motif_sequence=motif_sequence,
        motif_region=motif_region,
        motif_in_disorder=motif_in_disorder,
        motif_exposed=motif_exposed,
        receptor_has_motif_pocket=receptor_has_motif_pocket,
    )
    return {
        "schema_version": "1.0",
        "name": name or f"{protein_a.get('name', 'A')}--{protein_b.get('name', 'B')}",
        "language": normalize_language(language),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "organism": organism or None,
            "proteins": proteins,
        },
        "routing": routing,
        "hypothesis": {
            "motif_owner": motif_owner,
            "motif_sequence": motif_sequence,
            "motif_region": list(motif_region) if motif_region else None,
            "motif_context": motif_context,
            "receptor_has_motif_pocket": receptor_has_motif_pocket,
            "coordinate_convention": "1-based inclusive",
        }
        if motif_sequence or motif_region or motif_context or receptor_has_motif_pocket
        else None,
        "peptide_design": None,
        "execution": {
            "backend": "boltz2",
            "status": "planned",
            "remote_msa": False,
        },
        "privacy": {
            "local_first": True,
            "sequence_upload_authorized": False,
        },
    }


def _serialize(payload: Any, requested_format: str, translator: Translator) -> tuple[str, str]:
    data = _jsonable(payload)
    if requested_format == "yaml":
        try:
            yaml = importlib.import_module("yaml")
        except ImportError:
            print(translator.t("yaml_fallback"), file=sys.stderr)
        else:
            return yaml.safe_dump(data, allow_unicode=True, sort_keys=False), "yaml"
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n", "json"


def _emit(
    payload: Any,
    *,
    requested_format: str,
    output: str | None,
    translator: Translator,
) -> None:
    text, actual_format = _serialize(payload, requested_format, translator)
    if output:
        destination = Path(output).expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        print(translator.t("output_written", path=destination), file=sys.stderr)
        if actual_format != requested_format:
            print(f"format={actual_format}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def _parse_windows(raw: str) -> tuple[int, ...]:
    try:
        values = tuple(int(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError as exc:
        raise CLIError("--windows must be a comma-separated list of positive integers.") from exc
    if not values or any(value <= 0 for value in values):
        raise CLIError("--windows must be a comma-separated list of positive integers.")
    return tuple(dict.fromkeys(values))


def _parse_unbounded_region(raw: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[:\-]\s*(\d+)\s*", raw)
    if not match:
        raise CLIError("--motif-region uses 1-based inclusive START:END coordinates.")
    start, end = (int(match.group(1)), int(match.group(2)))
    if start < 1 or end < start:
        raise CLIError("--motif-region requires START >= 1 and START <= END.")
    return start, end


def _fallback_peptide_panel(
    sequence: str,
    motif_start: int,
    motif_end: int,
    windows: Sequence[int],
) -> dict[str, Any]:
    """Minimal WT-only fallback used only when the science core is absent."""

    motif_length = motif_end - motif_start + 1
    variants: list[dict[str, Any]] = []
    for requested in windows:
        if requested < motif_length:
            raise CLIError(f"Window {requested} is shorter than the {motif_length}-residue motif.")
        size = min(requested, len(sequence))
        left_flank = (size - motif_length) // 2
        start = max(1, motif_start - left_flank)
        end = start + size - 1
        if end > len(sequence):
            end = len(sequence)
            start = end - size + 1
        variants.append(
            {
                "kind": "wt",
                "requested_window": requested,
                "start_1based": start,
                "end_1based": end,
                "sequence": sequence[start - 1 : end],
            }
        )
    return {
        "motif": {
            "sequence": sequence[motif_start - 1 : motif_end],
            "start_1based": motif_start,
            "end_1based": motif_end,
        },
        "variants": variants,
        "warnings": ["Science-core unavailable: generated WT windows only; no scientific controls were inferred."],
    }


def design_panel(
    sequence: str,
    motif_start: int,
    motif_end: int,
    *,
    windows: Sequence[int],
    seed: int,
) -> dict[str, Any]:
    try:
        module = importlib.import_module("ppi_scout.peptide_design")
        designer = getattr(module, "design_peptide_panel")
    except (ImportError, AttributeError):
        panel = _fallback_peptide_panel(sequence, motif_start, motif_end, windows)
    else:
        try:
            panel = _jsonable(
                designer(
                    sequence,
                    motif_start,
                    motif_end,
                    window_sizes=tuple(windows),
                    seed=seed,
                )
            )
        except (TypeError, ValueError) as exc:
            raise CLIError(f"Peptide design failed: {exc}") from exc
    return {
        "schema_version": "1.0",
        "kind": "peptide_panel",
        "coordinate_system": "1-based inclusive",
        "parent_sequence_length": len(sequence),
        "motif": {
            "sequence": sequence[motif_start - 1 : motif_end],
            "start_1based": motif_start,
            "end_1based": motif_end,
        },
        "window_sizes": list(windows),
        "seed": seed,
        "panel": panel,
    }


def _scan_and_design_motifs(
    sequence: str,
    *,
    flank_size: int,
    windows: Sequence[int],
    seed: int,
    candidate_ids: Sequence[str] = (),
    design_top: int | None = None,
) -> dict[str, Any]:
    """Run the local AIM/LIR scanner and design only explicitly requested hits."""

    if flank_size < 0:
        raise CLIError("--flank-size must be zero or greater.")
    if design_top is not None and design_top < 1:
        raise CLIError("--design-top must be a positive integer.")
    try:
        module = importlib.import_module("ppi_scout.motif_scan")
        scanner = getattr(module, "scan_aim_lir")
    except (ImportError, AttributeError) as exc:
        raise CLIError("The local AIM/LIR motif scanner is unavailable.") from exc
    try:
        raw_scan = _jsonable(scanner(sequence, flank_size=flank_size))
    except (TypeError, ValueError) as exc:
        raise CLIError(f"Motif scan failed: {exc}") from exc
    if not isinstance(raw_scan, dict) or not isinstance(raw_scan.get("candidates"), list):
        raise CLIError("The motif scanner returned an unsupported result.")

    candidates = raw_scan["candidates"]
    by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise CLIError("The motif scanner returned an unsupported candidate.")
        candidate_id = str(candidate.get("candidate_id", ""))
        if not candidate_id:
            raise CLIError("The motif scanner returned a candidate without an ID.")
        by_id[candidate_id] = candidate

    selected_ids: list[str] = []
    for candidate_id in candidate_ids:
        normalized = candidate_id.strip().lower()
        if normalized and normalized not in selected_ids:
            selected_ids.append(normalized)
    if design_top is not None:
        for candidate in candidates[:design_top]:
            candidate_id = str(candidate["candidate_id"])
            if candidate_id not in selected_ids:
                selected_ids.append(candidate_id)

    unknown = [candidate_id for candidate_id in selected_ids if candidate_id not in by_id]
    if unknown:
        raise CLIError(
            "Unknown motif candidate ID(s): "
            + ", ".join(unknown)
            + ". Run `ppi-scout scan` without design options to list valid IDs."
        )

    panels: list[dict[str, Any]] = []
    for candidate_id in selected_ids:
        candidate = by_id[candidate_id]
        try:
            start = int(candidate["start_1based"])
            end = int(candidate["end_1based"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CLIError(f"Candidate {candidate_id} has invalid motif coordinates.") from exc
        panels.append(
            {
                "candidate_id": candidate_id,
                "candidate": candidate,
                "design": design_panel(
                    sequence,
                    start,
                    end,
                    windows=windows,
                    seed=seed,
                ),
            }
        )

    return {
        "schema_version": "1.0",
        "kind": "aim_lir_scan",
        "coordinate_system": "1-based inclusive",
        "parent_sequence_length": len(sequence),
        "flank_size": flank_size,
        **raw_scan,
        "designed_candidate_ids": selected_ids,
        "peptide_panels": panels,
        "selection_note": (
            "No peptide candidate was selected automatically."
            if not selected_ids
            else "Peptide panels were generated only for explicitly requested candidates."
        ),
    }


def _print_scan_candidates(scan: Mapping[str, Any], translator: Translator) -> None:
    candidates = scan.get("candidates", [])
    if not candidates:
        print(f"{translator.t('scan_candidates_title')}: {translator.t('scan_none')}", file=sys.stderr)
        return
    print(
        f"{translator.t('scan_candidates_title')} ({translator.t('scan_candidates_note')}):",
        file=sys.stderr,
    )
    for candidate in candidates:
        print(
            "  {candidate_id}: {core} at {start}:{end}; rank {rank}; sequence score {score}".format(
                candidate_id=candidate.get("candidate_id", "?"),
                core=candidate.get("core_sequence", "?"),
                start=candidate.get("start_1based", "?"),
                end=candidate.get("end_1based", "?"),
                rank=candidate.get("rank", "?"),
                score=candidate.get("sequence_score", "?"),
            ),
            file=sys.stderr,
        )
        print(
            "    "
            + translator.t(
                "scan_candidate_features",
                acidic=candidate.get("acidic_flank_count", "?"),
                st=candidate.get("serine_threonine_flank_count", "?"),
            ),
            file=sys.stderr,
        )
        for warning in candidate.get("warnings", []):
            if "truncated by a sequence terminus" in str(warning):
                warning_key = "scan_warning_truncated"
            elif "contains X" in str(warning):
                warning_key = "scan_warning_unknown"
            elif "score is tied" in str(warning):
                warning_key = "scan_warning_tied"
            else:
                warning_key = "scan_warning_review"
            print(f"    {translator.t('scan_warning_prefix')}: {translator.t(warning_key)}", file=sys.stderr)
    print(translator.t("scan_global_caveat"), file=sys.stderr)


def _default_peptide_windows(parent_length: int) -> tuple[int, ...]:
    """Return useful defaults without duplicate, terminus-truncated panels."""

    return tuple(dict.fromkeys(min(window, parent_length) for window in (16, 24, 34)))


def _load_document(path_value: str) -> dict[str, Any]:
    path = Path(path_value).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CLIError(f"Cannot read job file {path}: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            yaml = importlib.import_module("yaml")
            payload = yaml.safe_load(text)
        except (ImportError, ValueError, TypeError) as exc:
            raise CLIError("Job file is not JSON; install PyYAML to read YAML input.") from exc
    if not isinstance(payload, dict):
        raise CLIError("Job file must contain a JSON/YAML object at the top level.")
    return payload


def _command_plan(args: argparse.Namespace, translator: Translator) -> int:
    protein_a = _protein_from_args(args, "a", args.protein_a_pos)
    protein_b = _protein_from_args(args, "b", args.protein_b_pos)
    motif_sequence = (
        _clean_sequence(args.motif_sequence, source="motif sequence")
        if args.motif_sequence
        else None
    )
    motif_region = _parse_unbounded_region(args.motif_region) if args.motif_region else None
    if motif_region and not args.motif_owner:
        raise CLIError("--motif-region requires --motif-owner A or B.")
    if args.motif_owner:
        owner = protein_a if args.motif_owner == "A" else protein_b
        owner_sequence = owner.get("sequence")
        if motif_region and owner_sequence:
            start, end = motif_region
            if end > len(owner_sequence):
                raise CLIError(
                    f"Motif region {start}:{end} exceeds protein {args.motif_owner} length {len(owner_sequence)}."
                )
            extracted = owner_sequence[start - 1 : end]
            if motif_sequence and extracted != motif_sequence:
                raise CLIError(
                    f"Motif sequence {motif_sequence} does not match protein {args.motif_owner} "
                    f"residues {start}:{end} ({extracted})."
                )
            motif_sequence = motif_sequence or extracted
    job = create_job(
        protein_a,
        protein_b,
        language=translator.language,
        organism=args.organism,
        mode=args.mode,
        name=args.name,
        motif_owner=args.motif_owner,
        motif_sequence=motif_sequence,
        motif_region=motif_region,
        motif_context=args.motif_context,
        receptor_has_motif_pocket=args.receptor_has_motif_pocket,
    )
    _emit(job, requested_format=args.format, output=args.output, translator=translator)
    return 0


def _command_scan_motifs(args: argparse.Namespace, translator: Translator) -> int:
    if bool(args.sequence) == bool(args.fasta):
        raise CLIError(translator.t("sequence_required") + " Choose exactly one of --sequence or --fasta.")
    sequence = _clean_sequence(args.sequence, source="sequence") if args.sequence else _read_fasta(args.fasta)
    payload = _scan_and_design_motifs(
        sequence,
        flank_size=args.flank_size,
        windows=_parse_windows(args.windows),
        seed=args.seed,
        candidate_ids=args.design_candidate or (),
        design_top=args.design_top,
    )
    _emit(payload, requested_format=args.format, output=args.output, translator=translator)
    return 0


def _command_doctor(args: argparse.Namespace, translator: Translator) -> int:
    checks: dict[str, Any] = {
        "title": translator.t("doctor_title"),
        "ppi_scout_version": __version__,
        "python": sys.version.split()[0],
        "languages": list(SUPPORTED_LANGUAGES),
        "yaml_available": importlib.util.find_spec("yaml") is not None,
        "science_core_available": all(
            importlib.util.find_spec(name) is not None
            for name in (
                "ppi_scout.models",
                "ppi_scout.router",
                "ppi_scout.peptide_design",
                "ppi_scout.motif_scan",
                "ppi_scout.visualization",
            )
        ),
    }
    try:
        backend_module = importlib.import_module("ppi_scout.backends.boltz2")
        checks["boltz2"] = _jsonable(backend_module.Boltz2Backend().doctor())
    except (ImportError, AttributeError) as exc:
        checks["boltz2"] = {"available": False, "problems": [str(exc)]}
    checks["ready_to_plan"] = True
    checks["ready_to_run"] = bool(checks.get("boltz2", {}).get("available"))
    _emit(checks, requested_format=args.format, output=args.output, translator=translator)
    return 0


def _finalize_run_artifacts(
    output_dir: Path,
    run_job: dict[str, Any],
    status: dict[str, Any],
    *,
    language: str | None = None,
) -> dict[str, Any]:
    """Write status, CSV, Markdown, and HTML without masking the run outcome."""

    underlying_status = str(status.get("status", "unknown"))
    execution = run_job.get("execution", {})
    if not isinstance(execution, dict):
        execution = {}
    run_job["execution"] = {**execution, "status": underlying_status}

    destination = output_dir / "report.html"
    temporary_destination = output_dir / ".report.html.tmp"
    # Persist the authoritative run state before attempting a non-critical
    # presentation artifact. A renderer failure must never erase this outcome.
    (output_dir / "job.json").write_text(
        json.dumps(run_job, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        temporary_destination.unlink(missing_ok=True)
        analysis = importlib.import_module("ppi_scout.analysis")
        reporting = importlib.import_module("ppi_scout.reporting")
        visualization = importlib.import_module("ppi_scout.visualization")
        rows = analysis.collect_confidence_files(output_dir)
        summary_path = analysis.write_summary_csv(rows, output_dir / "confidence_summary.csv")
        markdown_path = reporting.write_markdown_report(run_job, rows, output_dir / "report.md")
        visualization.write_html_report(
            run_job,
            rows,
            temporary_destination,
            status=status,
            language=language or run_job.get("language"),
        )
        temporary_destination.replace(destination)
        status["artifacts"] = {
            **dict(status.get("artifacts", {})),
            "confidence_summary": str(summary_path),
            "markdown_report": str(markdown_path),
            "html_report": str(destination),
        }
        status["confidence_rows"] = len(rows)
    except Exception as exc:  # a report is non-critical; preserve the Boltz outcome
        try:
            temporary_destination.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        status["visualization"] = {
            "status": "failed",
            "path": str(destination),
            "error": str(exc),
            "run_status_unchanged": True,
            "recovery": f"Inspect {output_dir / 'status.json'} and rerun the same command.",
        }
    else:
        status["visualization"] = {
            "status": "complete",
            "path": str(destination),
            "offline": True,
        }

    try:
        (output_dir / "status.json").write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        visualization_state = status.get("visualization")
        if isinstance(visualization_state, dict):
            visualization_state["metadata_persisted"] = False
            visualization_state["metadata_error"] = str(exc)
    return status


def _print_run_visualization_status(status: Mapping[str, Any], translator: Translator) -> None:
    visualization = status.get("visualization", {})
    if not isinstance(visualization, Mapping):
        return
    if visualization.get("status") == "complete":
        print(
            translator.t(
                "auto_visualization_complete",
                run_status=status.get("status", "unknown"),
                path=visualization.get("path", "report.html"),
            ),
            file=sys.stderr,
        )
    elif visualization.get("status") == "failed":
        print(
            translator.t(
                "auto_visualization_failed",
                run_status=status.get("status", "unknown"),
                error=visualization.get("error", "unknown error"),
                recovery=visualization.get("recovery", "Inspect status.json and rerun the same command."),
            ),
            file=sys.stderr,
        )
    if visualization.get("metadata_persisted") is False:
        print(
            translator.t(
                "auto_visualization_metadata_failed",
                error=visualization.get("metadata_error", "unknown error"),
            ),
            file=sys.stderr,
        )


def _command_run(args: argparse.Namespace, translator: Translator) -> int:
    live_requested = bool(getattr(args, "live", False))
    dry_run_requested = bool(getattr(args, "dry_run", False))
    if live_requested and dry_run_requested:
        raise CLIError("Choose either --live or --dry-run, not both.")
    job = _load_document(args.job)
    routing = job.get("routing", {})
    if (
        isinstance(job.get("hypothesis"), dict)
        and isinstance(routing, dict)
        and routing.get("route") == "motif_peptide"
    ):
        return _command_run_panel(args, translator, job=job)
    proteins = job.get("inputs", {}).get("proteins", [])
    if len(proteins) < 2 or any(not item.get("sequence") for item in proteins):
        raise CLIError("The job needs at least two resolved protein sequences before it can run.")
    try:
        backend_module = importlib.import_module("ppi_scout.backends.boltz2")
        backend = backend_module.Boltz2Backend()
    except (ImportError, AttributeError) as exc:
        raise CLIError(translator.t("core_unavailable")) from exc
    output_dir = Path(args.output_dir or f"runs/{_safe_job_slug(job.get('name'))}").expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_job = dict(job)
    run_job["execution"] = {
        **dict(job.get("execution", {})),
        "backend": "boltz2",
        "status": "planned",
        "remote_msa": bool(args.remote_msa),
        "output_format": args.output_format,
    }
    run_job["privacy"] = {
        **dict(job.get("privacy", {})),
        "local_first": True,
        "sequence_upload_authorized": bool(args.remote_msa),
    }
    page_language = getattr(args, "lang", None) or run_job.get("language")
    (output_dir / "job.json").write_text(
        json.dumps(run_job, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        chains = [
            {
                "id": item.get("id") or chr(65 + index),
                "sequence": item["sequence"],
                "msa": "remote" if args.remote_msa else "empty",
            }
            for index, item in enumerate(proteins)
        ]
        input_payload = backend.compile_input(chains)
        input_path = backend.write_input(input_payload, output_dir / "resolved_input.yaml")
        argv = backend.command(
            input_path,
            output_dir / "predictions",
            remote_msa=args.remote_msa,
            output_format=args.output_format,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        status = {"status": "failed", "error": str(exc)}
        status = _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
        _print_run_visualization_status(status, translator)
        raise CLIError(str(exc)) from exc
    plan = {
        "schema_version": "1.0",
        "backend": "boltz2",
        "input_path": str(input_path),
        "output_dir": str(output_dir / "predictions"),
        "remote_msa": bool(args.remote_msa),
        "argv": argv,
    }
    (output_dir / "plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        result = backend.run(argv, live=live_requested, log_path=output_dir / "run.json")
    except (OSError, RuntimeError, ValueError) as exc:
        status = {"status": "failed", "error": str(exc), "plan": plan}
        status = _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
        _print_run_visualization_status(status, translator)
        raise CLIError(str(exc)) from exc
    status = {**_jsonable(result), "plan": plan}
    status = _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
    _print_run_visualization_status(status, translator)
    _emit(status, requested_format="json", output=None, translator=translator)
    return 0


def _command_run_panel(
    args: argparse.Namespace,
    translator: Translator,
    *,
    job: dict[str, Any] | None = None,
) -> int:
    """Prepare, execute, resume, analyze, and report a matched peptide panel."""

    live_requested = bool(getattr(args, "live", False))
    job = job or _load_document(args.job)
    proteins = job.get("inputs", {}).get("proteins", [])
    hypothesis = job.get("hypothesis")
    if not isinstance(hypothesis, dict):
        raise CLIError("run requires a reviewed motif job with a recorded motif hypothesis.")
    motif_owner = str(hypothesis.get("motif_owner", "")).upper()
    owner = next(
        (item for item in proteins if str(item.get("id", "")).upper() == motif_owner),
        None,
    )
    if owner is None or not owner.get("sequence"):
        raise CLIError("run requires an exact sequence for the recorded motif owner.")
    windows = (
        _parse_windows(args.windows)
        if args.windows
        else _default_peptide_windows(len(str(owner["sequence"])))
    )

    receptor_msa: str | None = None
    msa_resolution: LocalMSAResolution | None = None
    if args.receptor_msa:
        msa_path = Path(args.receptor_msa).expanduser().resolve()
        if not msa_path.is_file():
            raise CLIError(f"Local receptor MSA file does not exist: {msa_path}")
        receptor_msa = str(msa_path)
    elif args.msa_library:
        receptor = next(
            (item for item in proteins if str(item.get("id", "")).upper() != motif_owner),
            None,
        )
        if receptor is None or not receptor.get("sequence"):
            raise CLIError("run requires an exact receptor sequence for MSA lookup.")
        try:
            msa_resolution = resolve_receptor_msa(
                Path(args.msa_library),
                str(receptor["sequence"]),
            )
        except (OSError, ValueError) as exc:
            raise CLIError(str(exc)) from exc
        if msa_resolution.path is not None:
            receptor_msa = str(msa_resolution.path)
            print(
                f"Using exact local receptor MSA: {msa_resolution.path}",
                file=sys.stderr,
            )
        else:
            print(
                "No exact local receptor MSA was found; using offline single-sequence mode.",
                file=sys.stderr,
            )

    try:
        backend_module = importlib.import_module("ppi_scout.backends.boltz2")
        executor_module = importlib.import_module("ppi_scout.executor")
        panel_module = importlib.import_module("ppi_scout.panel_execution")
        backend = backend_module.Boltz2Backend()
    except (ImportError, AttributeError) as exc:
        raise CLIError(translator.t("core_unavailable")) from exc
    if live_requested and not backend.doctor().available:
        raise CLIError("Boltz is unavailable. Run `ppi-scout doctor` before live execution.")

    try:
        manifest = panel_module.build_panel_manifest(
            job,
            windows=windows,
            design_seed=args.design_seed,
            prediction_seed=args.prediction_seed,
            scramble_count=args.scrambles,
            remote_msa=bool(args.remote_msa),
            receptor_msa=receptor_msa,
            output_format=args.output_format,
            accelerator=args.accelerator,
            no_kernels=(None if args.kernels is None else not args.kernels),
            recycling_steps=args.recycling_steps,
            sampling_steps=args.sampling_steps,
            diffusion_samples=args.diffusion_samples,
        )
    except (TypeError, ValueError) as exc:
        raise CLIError(str(exc)) from exc

    if msa_resolution is not None:
        manifest["msa"]["library_lookup"] = msa_resolution.to_dict()
        if not msa_resolution.matched:
            manifest["warnings"].append(
                "No exact sequence-addressed receptor MSA was found in the local library; "
                "the panel uses offline single-sequence mode."
            )

    output_dir = Path(
        args.output_dir or f"runs/{_safe_job_slug(job.get('name'))}"
    ).expanduser()
    try:
        tasks = executor_module.prepare_workspace(
            manifest,
            output_dir,
            backend=backend,
            resume=True,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise CLIError(str(exc)) from exc

    run_job = copy.deepcopy(job)
    run_job["peptide_design"] = manifest["peptide_design"]
    run_job["execution"] = {
        **dict(run_job.get("execution", {})),
        "backend": "boltz2",
        "kind": "motif_peptide_panel",
        "status": "planned",
        "remote_msa": bool(args.remote_msa),
        "output_format": args.output_format,
        "engine_settings": manifest["execution"]["engine_settings"],
        "task_count": len(tasks),
        "automatic_resume": True,
    }
    run_job["privacy"] = {
        **dict(run_job.get("privacy", {})),
        "local_first": not bool(args.remote_msa),
        "sequence_upload_authorized": bool(args.remote_msa),
        "msa_mode": manifest["msa"]["mode"],
    }
    run_job["panel_manifest"] = "manifest.resolved.json"
    page_language = getattr(args, "lang", None) or run_job.get("language")
    (output_dir / "job.json").write_text(
        json.dumps(run_job, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "panel.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    try:
        status = executor_module.execute_prepared(
            tasks,
            output_dir,
            live=live_requested,
            backend=backend,
            resume=True,
            stream=live_requested,
        )
    except KeyboardInterrupt:
        try:
            status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
            _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
        except (OSError, json.JSONDecodeError):
            pass
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        try:
            status = json.loads((output_dir / "status.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            status = {"status": "failed", "error": str(exc)}
        status["error"] = str(exc)
        status = _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
        _print_run_visualization_status(status, translator)
        raise CLIError(str(exc)) from exc

    status["artifacts"] = {
        "panel": str(output_dir / "panel.json"),
        "plan": str(output_dir / "plan.json"),
    }
    status["task_count"] = len(tasks)
    status["msa_mode"] = manifest["msa"]["mode"]
    status = _finalize_run_artifacts(output_dir, run_job, status, language=page_language)
    _print_run_visualization_status(status, translator)
    _emit(status, requested_format="json", output=None, translator=translator)
    return 0


def _interactive() -> int:
    def ask(prompt: str) -> str:
        print(prompt, end="", file=sys.stderr, flush=True)
        return input()

    print(
        "语言 / Language / 言語：先选择提示语言；这不会改变科学分析。"
        "例如 / Example / 例：1 = 中文。不可留空 / do not leave blank / 空欄不可。",
        file=sys.stderr,
    )
    language = choose_language(
        input_fn=ask,
        output_fn=lambda message: print(message, file=sys.stderr),
    )
    translator = Translator.for_language(language)
    print(translator.t("welcome"), file=sys.stderr)
    print(translator.t("interactive_intro"), file=sys.stderr)
    print(translator.t("input_hint"), file=sys.stderr)
    print(translator.t("protein_ab_guidance"), file=sys.stderr)
    print(translator.t("protein_a_guidance"), file=sys.stderr)
    protein_a = _protein_from_free_text(ask(translator.t("protein_a_prompt")), "A")
    print(translator.t("protein_b_guidance"), file=sys.stderr)
    protein_b = _protein_from_free_text(ask(translator.t("protein_b_prompt")), "B")
    print(translator.t("organism_guidance"), file=sys.stderr)
    organism = ask(translator.t("organism_prompt")).strip() or None
    print(translator.t("mode_guidance"), file=sys.stderr)
    mode = ask(translator.t("mode_prompt")).strip() or "auto"
    if mode not in ROUTES:
        print(translator.t("invalid_mode"), file=sys.stderr)
        mode = "auto"
    job = create_job(protein_a, protein_b, language=language, organism=organism, mode=mode)
    print(translator.t("scan_guidance"), file=sys.stderr)
    enable_scan = ask(translator.t("scan_prompt")).strip().casefold()
    if enable_scan in {"y", "yes", "是", "开启", "开", "要", "需要", "はい", "する"}:
        print(translator.t("scan_owner_guidance"), file=sys.stderr)
        owner = ask(translator.t("scan_owner_prompt")).strip().upper() or "B"
        if owner not in {"A", "B"}:
            print(translator.t("scan_skipped"), file=sys.stderr)
            job["motif_scan"] = {
                "status": "skipped",
                "reason": "motif owner must be A or B",
            }
        else:
            owner_protein = protein_a if owner == "A" else protein_b
            owner_sequence = owner_protein.get("sequence")
            if not owner_sequence:
                reason = translator.t("scan_sequence_required")
                print(reason, file=sys.stderr)
                job["motif_scan"] = {"status": "skipped", "owner": owner, "reason": reason}
            else:
                default_windows = _default_peptide_windows(len(owner_sequence))
                preview = _scan_and_design_motifs(
                    owner_sequence,
                    flank_size=6,
                    windows=default_windows,
                    seed=17,
                )
                _print_scan_candidates(preview, translator)
                print(translator.t("scan_select_guidance"), file=sys.stderr)
                requested = ask(translator.t("scan_select_prompt")).strip()
                selected_ids = [
                    value.strip()
                    for value in requested.replace("，", ",").split(",")
                    if value.strip()
                ]
                scan = (
                    _scan_and_design_motifs(
                        owner_sequence,
                        flank_size=6,
                        windows=default_windows,
                        seed=17,
                        candidate_ids=selected_ids,
                    )
                    if selected_ids
                    else preview
                )
                scan["status"] = "complete"
                scan["owner"] = owner
                job["motif_scan"] = scan
                job["peptide_design"] = (
                    {
                        "enabled": True,
                        "source": "motif_scan.peptide_panels",
                        "candidate_ids": scan["designed_candidate_ids"],
                        "windows": list(default_windows),
                        "seed": 17,
                    }
                    if scan["peptide_panels"]
                    else None
                )
    print(translator.t("job_created"), file=sys.stderr)
    _emit(job, requested_format="json", output=None, translator=translator)
    return 0


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("json", "yaml"), default="json")
    parser.add_argument("-o", "--output", help="Write output to this path instead of stdout.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppi-scout", description="Plan local protein-interaction predictions.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--lang", choices=SUPPORTED_LANGUAGES, default=None, help="CLI language.")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Check the local PPI Scout/Boltz environment.")
    _add_output_options(doctor)
    doctor.set_defaults(handler=_command_doctor)

    plan = subparsers.add_parser("plan", help="Resolve two protein inputs into a job plan.")
    plan.add_argument("protein_a_pos", nargs="?", help="Protein A name, sequence, or FASTA path.")
    plan.add_argument("protein_b_pos", nargs="?", help="Protein B name, sequence, or FASTA path.")
    plan.add_argument("--protein-a", help="Protein A name/accession (unresolved input).")
    plan.add_argument("--sequence-a", help="Protein A amino-acid sequence.")
    plan.add_argument("--fasta-a", help="Protein A single-record FASTA file.")
    plan.add_argument("--protein-b", help="Protein B name/accession (unresolved input).")
    plan.add_argument("--sequence-b", help="Protein B amino-acid sequence.")
    plan.add_argument("--fasta-b", help="Protein B single-record FASTA file.")
    plan.add_argument("--organism", help="Species or strain shared by the query.")
    plan.add_argument("--mode", choices=ROUTES, default="auto")
    plan.add_argument("--name", help="Human-readable job name.")
    plan.add_argument("--motif-owner", choices=("A", "B"), help="Chain containing the motif.")
    plan.add_argument("--motif-sequence", help="Resolved motif sequence, for example WEEL.")
    plan.add_argument(
        "--motif-region",
        help="Motif coordinates in its owner as 1-based inclusive START:END.",
    )
    plan.add_argument(
        "--motif-context",
        choices=("disordered", "exposed", "buried", "unknown"),
        help="Evidence-supported structural context of the candidate motif.",
    )
    plan.add_argument(
        "--receptor-has-motif-pocket",
        action="store_true",
        default=None,
        help="Record evidence that the receptor has a compatible motif-binding pocket.",
    )
    _add_output_options(plan)
    plan.set_defaults(handler=_command_plan)

    scan = subparsers.add_parser(
        "scan",
        help="Scan a local sequence for AIM/LIR candidates without selecting one automatically.",
    )
    scan.add_argument("--sequence", help="Parent amino-acid sequence.")
    scan.add_argument("--fasta", help="Single-record parent FASTA file.")
    scan.add_argument("--flank-size", type=int, default=6, help="Context residues on each side.")
    scan.add_argument("--windows", default="16,24,34", help="Comma-separated peptide lengths.")
    scan.add_argument("--seed", type=int, default=17, help="Deterministic decoy seed.")
    scan.add_argument(
        "--design-candidate",
        action="append",
        help="Candidate ID to design; repeat for multiple candidates.",
    )
    scan.add_argument(
        "--design-top",
        type=int,
        help="Explicitly design the first N ranked candidates.",
    )
    _add_output_options(scan)
    scan.set_defaults(handler=_command_scan_motifs)

    run = subparsers.add_parser(
        "run",
        help="Dry-run or execute a job; motif jobs automatically include matched controls.",
    )
    run.add_argument("job", help="Job JSON/YAML path.")
    run.add_argument("--output-dir")
    execution_mode = run.add_mutually_exclusive_group()
    execution_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile the Boltz command without executing it (this is also the safe default).",
    )
    execution_mode.add_argument(
        "--live",
        action="store_true",
        help="Explicitly start the real Boltz prediction after reviewing the dry-run.",
    )
    msa_mode = run.add_mutually_exclusive_group()
    msa_mode.add_argument(
        "--remote-msa",
        action="store_true",
        help="Explicitly authorize sending protein sequences to a remote MSA service.",
    )
    run.add_argument("--output-format", choices=("pdb", "mmcif"), default="pdb")
    run.add_argument(
        "--windows",
        help="Motif jobs only: peptide lengths, for example 24 or 16,24,34.",
    )
    run.add_argument("--design-seed", type=int, default=17, help=argparse.SUPPRESS)
    run.add_argument("--prediction-seed", type=int, default=17, help=argparse.SUPPRESS)
    run.add_argument("--scrambles", type=int, default=3, help=argparse.SUPPRESS)
    msa_mode.add_argument(
        "--receptor-msa",
        help="Motif jobs only: audited local receptor MSA; peptides remain msa: empty.",
    )
    msa_mode.add_argument(
        "--msa-library",
        help="Motif jobs only: exact-sequence local A3M directory.",
    )
    run.add_argument("--accelerator", choices=("auto", "gpu", "cpu", "tpu"), default="auto")
    run.add_argument(
        "--kernels",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=argparse.SUPPRESS,
    )
    run.add_argument("--recycling-steps", type=int, default=3, help=argparse.SUPPRESS)
    run.add_argument("--sampling-steps", type=int, default=200, help=argparse.SUPPRESS)
    run.add_argument("--diffusion-samples", type=int, default=1, help=argparse.SUPPRESS)
    run.set_defaults(handler=_command_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        if argv is not None and len(argv) > 0:
            parser.print_help()
            return 0
        try:
            return _interactive()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.", file=sys.stderr)
            return 130

    translator = Translator.for_language(args.lang)
    try:
        return int(args.handler(args, translator))
    except CLIError as exc:
        print(f"{translator.t('error_prefix')}: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
