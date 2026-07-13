"""Prepare auditable run workspaces and invoke prediction backends."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .backends.boltz2 import Boltz2Backend


@dataclass(frozen=True)
class PreparedTask:
    task_id: str
    input_path: str
    output_dir: str
    argv: tuple[str, ...]
    remote_msa: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["argv"] = list(self.argv)
        return payload


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.").lower()
    return slug or "task"


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _extract_chains(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_chains = payload.get("chains")
    if raw_chains is None:
        raw_chains = payload.get("complex", {}).get("chains")
    if raw_chains is not None:
        chains: list[dict[str, Any]] = []
        for raw in raw_chains:
            source = raw.get("resolved", raw)
            sequence = source.get("sequence") or raw.get("sequence")
            chains.append(
                {
                    "id": raw.get("id") or raw.get("chain_id"),
                    "sequence": sequence,
                    "msa": raw.get("msa", source.get("msa", "empty")),
                }
            )
        return chains

    entities = payload.get("entities", {})
    if entities:
        chains = []
        for index, role in enumerate(("receptor", "partner")):
            entity = entities.get(role)
            if entity is None:
                continue
            resolved = entity.get("resolved", entity)
            chains.append(
                {
                    "id": entity.get("chain_id") or chr(ord("A") + index),
                    "sequence": resolved.get("sequence") or entity.get("sequence"),
                    "msa": entity.get("msa", resolved.get("msa", "empty")),
                }
            )
        return chains
    raise ValueError("Manifest does not contain chains or receptor/partner entities.")


def _expanded_tasks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = manifest.get("prediction_jobs") or manifest.get("tasks")
    if isinstance(tasks, list) and tasks:
        return [dict(task) for task in tasks]
    return [dict(manifest)]


def prepare_workspace(
    manifest: dict[str, Any],
    run_dir: Path,
    *,
    backend: Boltz2Backend | None = None,
) -> list[PreparedTask]:
    backend = backend or Boltz2Backend()
    run_dir.mkdir(parents=True, exist_ok=True)
    for child in ("inputs", "raw", "analysis", "report", "logs"):
        (run_dir / child).mkdir(exist_ok=True)

    resolved_path = run_dir / "manifest.resolved.json"
    resolved_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    prepared: list[PreparedTask] = []
    used_ids: set[str] = set()
    for index, task in enumerate(_expanded_tasks(manifest), start=1):
        base = _slug(str(task.get("id") or task.get("name") or f"task-{index}"))
        task_id = base
        suffix = 2
        while task_id in used_ids:
            task_id = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(task_id)

        chains = _extract_chains(task)
        boltz_payload = backend.compile_input(chains)
        input_path = backend.write_input(boltz_payload, run_dir / "inputs" / f"{task_id}.yaml")
        remote_msa = bool(task.get("remote_msa", manifest.get("remote_msa", False)))
        if remote_msa and not bool(task.get("remote_msa_allowed", manifest.get("remote_msa_allowed", False))):
            raise ValueError("Remote MSA was requested without explicit remote_msa_allowed=true.")
        output_dir = run_dir / "raw" / task_id
        argv = backend.command(
            input_path,
            output_dir,
            remote_msa=remote_msa,
            extra_args=task.get("engine_args", manifest.get("engine_args", ())),
        )
        prepared.append(
            PreparedTask(
                task_id=task_id,
                input_path=str(input_path),
                output_dir=str(output_dir),
                argv=tuple(argv),
                remote_msa=remote_msa,
            )
        )

    plan = {
        "schema_version": 1,
        "manifest_sha256": _json_hash(manifest),
        "run_dir": str(run_dir),
        "tasks": [task.to_dict() for task in prepared],
    }
    (run_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (run_dir / "status.json").write_text(
        json.dumps({"status": "planned", "tasks": {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return prepared


def execute_prepared(
    tasks: Iterable[PreparedTask],
    run_dir: Path,
    *,
    live: bool = False,
    backend: Boltz2Backend | None = None,
) -> dict[str, Any]:
    backend = backend or Boltz2Backend()
    statuses: dict[str, Any] = {}
    for task in tasks:
        result = backend.run(
            list(task.argv),
            live=live,
            log_path=run_dir / "logs" / f"{task.task_id}.json",
        )
        statuses[task.task_id] = result
        (run_dir / "status.json").write_text(
            json.dumps(
                {"status": "running" if live else "dry_run", "tasks": statuses},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    final_status = "complete" if live else "dry_run"
    payload = {"status": final_status, "tasks": statuses}
    (run_dir / "status.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def run_manifest(manifest_path: Path, run_dir: Path, *, live: bool = False) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tasks = prepare_workspace(manifest, run_dir)
    return execute_prepared(tasks, run_dir, live=live)
