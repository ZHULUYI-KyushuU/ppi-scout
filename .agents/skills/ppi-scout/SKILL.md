---
name: ppi-scout
description: Plan, execute, resume, and conservatively interpret reproducible local Boltz protein-complex and motif-peptide screens. Use when a user supplies protein names, accessions, FASTA files, or amino-acid sequences and needs sequence resolution, optional AIM/LIR candidate scanning, full-length/domain/motif-peptide routing, peptide and control design, a PPI Scout job file, local prediction, legacy-result import, analysis, an offline HTML result view, or a Chinese, English, or Japanese report.
---

# PPI Scout

## Start the interaction

- Honor `--lang zh-CN`, `--lang en`, or `--lang ja` when supplied.
- Otherwise, ask once before scientific intake:

  ```text
  请选择语言 / Choose a language / 言語を選択してください
  1. 中文  2. English  3. 日本語
  ```

- Continue in the selected language. Keep sequences, accessions, paths, commands, and metric names unchanged.

## Provide operational context

- Use the selected language for workflow guidance while preserving sequences,
  accessions, paths, commands, and metric names exactly.
- Before requesting an input, state its purpose, accepted format, default, and
  whether omission changes execution or scientific interpretation.
- Before a command, identify the expected artifact or state transition. After
  execution, report the resulting path and status.
- Calibrate detail to the user. Keep routine instructions concise; expand
  routing, MSA, privacy, control design, and result interpretation when the
  decision has scientific or operational consequences.
- Prefer `A` for the receptor/reference and `B` for the candidate or
  motif-bearing partner when that convention fits the question. Explain that
  A/B are stable chain labels, not evidence of direction and not automatically
  bait/prey.

## Follow the safe workflow

1. Collect the biological question, both inputs, organism or strain, and any known motif, domain, interface, membrane dependence, or mutation. Do not guess an ambiguous protein identity.
2. If the user has not already specified whether to scan for AIM/LIR candidates, explicitly ask whether to enable motif scanning; default to no. If enabled, ask whether A or B owns the motif, defaulting to B. Require that owner's resolved sequence.
3. Run `ppi-scout doctor` before planning. Treat it as read-only; do not install packages or change MSA policy automatically.
4. Run `ppi-scout plan` before every live run. Default to `--mode auto`; use a manual mode only when the user requests or justifies it.
5. Review the job plan with the user. Show resolved sequences and coordinates, selected representation, reasons, warnings, peptide controls, MSA mode, external data flow, and output location.
6. Use `ppi-scout run JOB --dry-run` to inspect the compiled Boltz command. `run` is dry-run by default; live execution requires an explicit `--live` only after the plan is accepted and any remote-MSA disclosure is resolved. Every dry or live run automatically attempts `OUTPUT_DIR/report.html`.
7. Use `ppi-scout resume RUN_ID` for an interrupted run; resume is also dry-run by default, requires `--live` to execute, and automatically attempts the same run directory's `report.html`. Use `analyze` and then `report` without silently changing the original job. Use manual `visualize` only to regenerate HTML or to view a scan/job JSON.

Typical sequence:

```bash
ppi-scout --lang zh-CN doctor --format json
ppi-scout --lang zh-CN plan --fasta-a atg8.fasta --fasta-b atg19.fasta --organism "Saccharomyces cerevisiae S288c" --mode auto -o job.json
ppi-scout run job.json --output-dir runs/atg8-atg19 --dry-run
ppi-scout run job.json --output-dir runs/atg8-atg19 --live
ppi-scout analyze runs/atg8-atg19
ppi-scout --lang zh-CN report runs/atg8-atg19 -o runs/atg8-atg19/report.md
# runs/atg8-atg19/report.html is attempted automatically after both run commands
```

For a sequence-resolved motif hypothesis, record its owner, coordinates, and
context in the plan rather than leaving them only in chat:

```bash
ppi-scout plan --fasta-a atg8.fasta --fasta-b atg19.fasta --mode auto \
  --motif-owner B --motif-region 412:415 --motif-sequence WEEL \
  --motif-context exposed --receptor-has-motif-pocket -o job.json
```

## Route the biological representation

- Select `full_length` for complete proteins when the question concerns their folded, whole-protein interaction and no better localized evidence exists.
- Select `domain` when a supported interface lies in a folded domain or full-length context would add unrelated domains or unresolved regions.
- Select `motif_peptide` only for a localized linear-motif hypothesis with a plausible receptor pocket and accessible sequence context.
- Select `needs_review` when identity, coordinates, membrane context, or structural evidence is insufficient or contradictory.
- Never turn a long protein into a peptide solely because it is long. A short biologically complete protein can still require full-length modeling.

Read [routing-rules.md](references/routing-rules.md) before finalizing `auto` routing.

## Design AIM/LIR panels

For Atg8/LC3/GABARAP questions, read [aim-lir-rules.md](references/aim-lir-rules.md). Use 1-based inclusive coordinates at the CLI boundary. Generate nested WT windows and matched anchor-mutant and scramble controls; never test only the four-residue core.

Scanning is disabled unless the user opts in. When enabled, report every
canonical `[WFY]xx[LIV]` match and its transparent sequence-only ranking.
Explain that the scanner cannot infer accessibility, disorder, topology, or
function. Ask which candidate IDs to design; a blank answer means design none.
Never select a candidate silently.
Treat `aim-NNN` as a position-based candidate ID, not its priority rank. Use
the separate `rank` field when discussing sequence-only priority.

```bash
ppi-scout scan-motifs --fasta atg19.fasta
ppi-scout scan-motifs --fasta atg19.fasta --design-candidate CANDIDATE_ID
```

```bash
ppi-scout design-peptides \
  --fasta atg19.fasta \
  --motif 412:415 \
  --windows 16,24,34 \
  --seed 7 \
  -o peptide-panel.json
```

## Protect interpretation and privacy

- Read [interpretation-guardrails.md](references/interpretation-guardrails.md) before analyzing or reporting.
- Never present ipTM, protein_ipTM, confidence score, rank score, or a predicted pose as proof that two molecules bind.
- Never use the Boltz affinity module or affinity outputs for protein-protein or protein-peptide affinity; it is a small-molecule-to-protein module.
- Compare WT and controls only under matched settings, inspect the expected interface, and label conclusions as structural-model support, ambiguity, or lack of support.
- Treat `--use_msa_server` as sequence disclosure to a remote service. Do not send unpublished, proprietary, patient-derived, or otherwise sensitive sequences without explicit permission. Prefer a local/precomputed MSA or `msa: empty` when disclosure is not allowed, and document the accuracy tradeoff.
- After every `run` or `resume`, tell the user that PPI Scout automatically attempts the run directory's self-contained `report.html` and that it can be opened by double-clicking. A visualization failure is not a Boltz failure: inspect and explain the run-status fields and `status.json` separately from visualization status or warnings.
- Use `ppi-scout --lang LANGUAGE visualize RUN_OR_JSON` manually only to regenerate a page or visualize a scan/job JSON. A run directory produces `report.html`; a JSON file produces `<source-stem>-report.html`. Explain every section, state clearly when no confidence files exist, and never turn a bar length or high score into a binding claim.

Read [boltz-local.md](references/boltz-local.md) before Boltz installation or
live execution and [troubleshooting.md](references/troubleshooting.md) when a
check or run fails. Use [job-template.json](assets/job-template.json) as a
human-auditable starting point; let `ppi-scout plan` produce the authoritative
executable job.
