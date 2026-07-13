"""Collect raw confidence fields from local prediction results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


RAW_FIELDS = (
    "rank_score",
    "ranking_score",
    "confidence_score",
    "ptm",
    "pTM",
    "iptm",
    "ipTM",
    "protein_iptm",
    "complex_plddt",
    "complex_iplddt",
    "complex_ipLDDT",
)


def _flatten_scalar_fields(payload: Any, prefix: str = "") -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                found[path] = value
            elif isinstance(value, dict):
                found.update(_flatten_scalar_fields(value, path))
    return found


def collect_confidence_files(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        if "confidence" not in path.name.lower() and "score" not in path.name.lower():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        flat = _flatten_scalar_fields(payload)
        row: dict[str, Any] = {"source": str(path.relative_to(root))}
        for requested in RAW_FIELDS:
            matches = [value for key, value in flat.items() if key.split(".")[-1] == requested]
            if matches:
                row[requested] = matches[0]
        rows.append(row)
    return rows


def write_summary_csv(rows: Iterable[dict[str, Any]], destination: Path) -> Path:
    materialized = list(rows)
    fieldnames = ["source"] + sorted({key for row in materialized for key in row if key != "source"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized)
    return destination
