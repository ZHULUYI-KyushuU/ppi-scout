"""Create a conservative, human-readable prototype report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


def build_markdown_report(job: dict[str, Any], rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    route = job.get("routing", {}).get("route", job.get("resolved_workflow", "unknown"))
    lines = [
        f"# PPI Scout report: {job.get('name', 'unnamed job')}",
        "",
        "## Outcome",
        "",
        "This run provides structure-model evidence only. It does not establish experimental binding.",
        "",
        f"Resolved route: `{route}`",
        "",
        "## Raw confidence outputs",
        "",
    ]
    if not rows:
        lines.append("No confidence JSON files were found. The run may be a plan/dry-run or incomplete.")
    else:
        keys = sorted({key for row in rows for key in row if key != "source"})
        lines.append("| source | " + " | ".join(keys) + " |")
        lines.append("|---|" + "|".join("---" for _ in keys) + "|")
        for row in rows:
            values = [str(row.get(key, "")) for key in keys]
            lines.append(f"| {row.get('source', '')} | " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Do not interpret a high ipTM or confidence score as proof of binding.",
            "- Compare matched WT, anchor mutants, and decoys under identical settings.",
            "- Inspect peptide-local confidence, interface error, contacts, clashes, and pose convergence.",
            "- Treat a WT that does not separate from ADFA/AAAA/scrambles as specificity not established.",
            "- Validate prioritized hypotheses experimentally.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(job: dict[str, Any], rows: Iterable[dict[str, Any]], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_markdown_report(job, rows), encoding="utf-8")
    return destination
