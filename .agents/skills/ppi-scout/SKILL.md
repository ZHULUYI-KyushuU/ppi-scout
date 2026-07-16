---
name: ppi-scout
description: Plan, run, resume, and conservatively interpret reproducible local Boltz protein-complex or motif-peptide screens, with optional AIM/LIR scanning and explicitly authorized official HelixFold3 cloud panels. Use for protein names, accessions, FASTA files, amino-acid sequences, reviewed PPI Scout jobs, local prediction, control comparison, or offline reports.
---

# PPI Scout

## User workflow

Use the requested `--lang zh-CN`, `--lang en`, or `--lang ja`. Otherwise ask
once. Keep sequences, accessions, paths, coordinates, command arguments, and
metric names unchanged.

PPI Scout has four public commands:

1. `ppi-scout doctor` — read-only environment check.
2. `ppi-scout plan` — verify two inputs and write the authoritative job.
3. `ppi-scout scan` — optional AIM/LIR sequence scan; never select a hit
   silently.
4. `ppi-scout run` — safe dry-run by default; `--live` explicitly starts
   inference. A reviewed motif job automatically becomes a matched control
   panel. Rerunning the same command resumes unfinished controls and rewrites
   the CSV, Markdown, and offline HTML reports.

Typical local workflow:

```bash
ppi-scout --lang zh-CN doctor
ppi-scout --lang zh-CN plan atg8.fasta yta7.fasta \
  --organism "Saccharomyces cerevisiae S288c" \
  --motif-owner B --motif-region 53:56 --motif-sequence FDFL \
  --motif-context disordered --receptor-has-motif-pocket -o job.json
ppi-scout run job.json --windows 24 --output-dir runs/atg8-yta7 --dry-run
ppi-scout run job.json --windows 24 --output-dir runs/atg8-yta7 --live
```

After each run, report the real run state and point to `status.json`,
`confidence_summary.csv`, `report.md`, and `report.html`. Tell the user that
`report.html` opens by double-clicking. Never treat a renderer failure as a
Boltz failure.

## Intake and planning

- Collect the question, two exact inputs, organism/strain, and known motif,
  domain, interface, membrane dependence, or mutation.
- Prefer A for the receptor/reference and B for the candidate or motif-bearing
  partner when appropriate. A/B are stable labels, not evidence of binding or
  automatic bait/prey assignments.
- Do not guess an ambiguous protein identity.
- Run `doctor`, then `plan`, then review exact sequences, coordinates, route,
  controls, MSA policy, external data flow, output path, and compute cost.
- Keep dry-run as the default. Use `--live` only after explicit acceptance.

For representation decisions, read
[`routing-rules.md`](references/routing-rules.md). Never choose a peptide only
because a protein is long. Use `needs_review` when identity, coordinates,
membrane context, or structural evidence is insufficient.

## AIM/LIR projects

Read [`aim-lir-rules.md`](references/aim-lir-rules.md). Scanning is opt-in and
requires an exact sequence:

```bash
ppi-scout scan --fasta yta7.fasta
ppi-scout scan --fasta yta7.fasta --design-candidate CANDIDATE_ID
```

Report every canonical `[WFY]xx[LIV]` match and its transparent sequence-only
rank. Explain that scanning cannot establish accessibility, disorder,
topology, function, or binding. Record the selected motif owner, 1-based
inclusive coordinates, exact core, context, and receptor-pocket evidence in
the job. Generate nested WT peptides and matched anchor, `AAAA`, reverse,
flank-scramble, and composition-matched controls; never test only the
four-residue core.

## Local Boltz execution

Read [`boltz-local.md`](references/boltz-local.md) before installation or live
execution and [`troubleshooting.md`](references/troubleshooting.md) after a
failure. Default to single-sequence offline mode. Use `--receptor-msa FILE` for
one audited local MSA, or `--msa-library DIR` for exact-sequence lookup.
`--remote-msa` is explicit authorization to send sequences externally.

Never change scientific inputs or settings inside an existing output folder.
Use a new job/output folder when parameters change.

## Cloud execution

Only after explicit authorization, read
[`helixfold3-cloud.md`](references/helixfold3-cloud.md) and treat the supplied
manifest as the exact submission boundary. Use only the official PaddleHelix
service. Never request or expose credentials, invent an API contract, combine
control peptides into one complex, or claim submission without a durable
provider job ID or result URL.

## Privacy and interpretation

Read [`interpretation-guardrails.md`](references/interpretation-guardrails.md)
before interpreting results.

- Never present ipTM, protein_ipTM, pLDDT, rank score, confidence score, or a
  predicted pose as proof of binding.
- Never use Boltz small-molecule affinity outputs for protein–protein or
  protein–peptide affinity.
- Compare WT and controls under matched settings and label conclusions as
  structural-model support, ambiguity, or lack of support.
- Do not externally submit unpublished, proprietary, patient-derived, or
  otherwise sensitive sequences without explicit permission.
- Never commit credentials, private sequences, MSA/model caches, provider raw
  output, or run directories.

Use [`job-template.json`](assets/job-template.json) only as a starting point;
the job produced by `ppi-scout plan` is authoritative.
