# PPI Scout User Guide

This guide defines the supported operating workflow for PPI Scout. It covers
installation, input preparation, job planning, Boltz execution, result review,
and data-handling requirements.

## Contents

1. [System model](#system-model)
2. [Installation](#installation)
3. [Input specification](#input-specification)
4. [Job lifecycle](#job-lifecycle)
5. [Representation selection](#representation-selection)
6. [AIM/LIR candidate scanning](#aimlir-candidate-scanning)
7. [Peptide panel design](#peptide-panel-design)
8. [MSA configuration](#msa-configuration)
9. [Prediction execution](#prediction-execution)
10. [Outputs and result review](#outputs-and-result-review)
11. [Data governance](#data-governance)
12. [Troubleshooting](#troubleshooting)

## System model

PPI Scout is an orchestration and audit layer around a separately maintained
Boltz installation.

| Layer | Responsibility |
|---|---|
| PPI Scout | Validate inputs, select a representation, design controls, compile jobs, record provenance, and summarize outputs |
| Boltz | Generate structural predictions and model confidence fields |
| Offline report | Present run metadata, candidates, controls, and discovered confidence fields in a local HTML file |
| Codex Skill | Provide optional workflow guidance and conservative interpretation |

Planning, motif scanning, peptide design, dry-run compilation, and JSON/HTML
report generation do not require a GPU. Live structure prediction requires a
working Boltz environment.

## Installation

### Supported Python versions

PPI Scout requires Python 3.10 or later. The current upstream Boltz package
requires Python 3.10-3.12. Use Python 3.11 or 3.12 when both packages will be
installed in the same environment.

### macOS, Linux, and WSL2

Install the released CLI directly from GitHub:

```bash
python -m pip install "git+https://github.com/ZHULUYI-KyushuU/ppi-scout.git@v0.4.0"
```

To use the repository-scoped Codex Skill or contribute to the project, clone
the repository and install from its root:

```bash
git clone https://github.com/ZHULUYI-KyushuU/ppi-scout.git
cd ppi-scout
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

For development:

```bash
python -m pip install -e ".[test]"
```

### Windows PowerShell

PPI Scout planning and reporting can run directly in PowerShell. The following
form avoids PowerShell activation-policy dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\ppi-scout.exe --lang en doctor
```

For CUDA-backed Boltz execution on Windows, use WSL2 with Ubuntu unless the
workstation has a separately validated native configuration.

### Boltz installation

Install Boltz in the same environment as PPI Scout so the `boltz` executable is
available on `PATH`.

NVIDIA CUDA environment:

```bash
python -m pip install --upgrade "boltz[cuda]"
```

CPU-only or non-CUDA environment:

```bash
python -m pip install --upgrade boltz
```

The CPU package is supported upstream but is substantially slower for
inference. Consult the
[official Boltz repository](https://github.com/jwohlwend/boltz) for current
platform and accelerator requirements.

Boltz downloads model data on first prediction. The default cache directory is
`~/.boltz`. To use a managed storage location, set `BOLTZ_CACHE` to an absolute
path before prediction:

```bash
export BOLTZ_CACHE=/absolute/path/to/boltz-cache
```

PowerShell equivalent:

```powershell
$env:BOLTZ_CACHE = "D:\models\boltz-cache"
```

Do not place the model cache inside the repository.

### Installation validation

```bash
ppi-scout --version
ppi-scout --lang en doctor
boltz predict --help
```

The `doctor` response distinguishes two states:

- `ready_to_plan: true`: planning, scanning, design, dry-run compilation, and
  reporting are available.
- `ready_to_run: true`: the Boltz executable is also available for live
  prediction.

## Input specification

### FASTA requirements

Use one protein record per FASTA file:

```text
>Atg8_Saccharomyces_cerevisiae_S288c
MSEQUENCE...
```

Requirements:

- amino-acid sequence, not nucleotide sequence;
- standard one-letter residue codes;
- no residue numbering or annotation inside sequence lines;
- one biological sequence per file;
- verified organism and strain provenance;
- exact sequence version retained with the project record.

### Chain labels

PPI Scout uses stable input labels `A` and `B`.

- Assign `A` to the receptor, known pocket, or reference protein when that
  convention fits the biological question.
- Assign `B` to the candidate partner or motif-bearing protein.
- Treat both labels as identifiers only. They do not establish interaction
  direction, stoichiometry, or bait/prey status.

For the public Atg8–Atg19 example, the conventional assignment is `A=Atg8`
and `B=Atg19` because the annotated motif is located in Atg19.

### Accepted input forms

The `plan` command accepts:

- a protein name or accession as an unresolved record;
- a literal amino-acid sequence;
- a single-record FASTA path.

Live prediction and local motif scanning require resolved sequences. PPI Scout
does not silently retrieve or guess an ambiguous protein sequence.

## Job lifecycle

The supported lifecycle is:

```text
doctor -> plan -> dry-run -> review -> live run -> analyze -> report
```

For a reviewed motif-peptide hypothesis, `run-panel` automates the execution,
resume, analysis, and report stages while retaining `--live` as the explicit
resource-use boundary.

### 1. Environment check

```bash
ppi-scout --lang en doctor
```

### 2. Job planning

```bash
ppi-scout --lang en plan \
  --fasta-a receptor.fasta \
  --fasta-b partner.fasta \
  --organism "Saccharomyces cerevisiae" \
  --mode auto \
  --name receptor-partner \
  -o job.json
```

The job file is the authoritative record of the resolved inputs and routing
decision. Review it before execution.

### 3. Dry-run compilation

```bash
ppi-scout run job.json \
  --output-dir runs/receptor-partner \
  --dry-run
```

Dry-run is the default behavior. It creates the resolved job artifacts and the
Boltz command plan without starting inference.

Review at minimum:

- protein identities and exact sequences;
- organism and strain;
- selected representation and routing reasons;
- motif coordinates and sequence ownership, if applicable;
- MSA mode and any external data transfer;
- output directory and compiled Boltz arguments.

### 4. Live execution

```bash
ppi-scout run job.json \
  --output-dir runs/receptor-partner \
  --live
```

Live inference is never implied by `run`; it requires `--live`.

### 5. Analysis and reporting

```bash
ppi-scout analyze runs/receptor-partner
ppi-scout --lang en report runs/receptor-partner
```

### Matched motif-peptide panels

Use a job whose exact sequences, motif owner, 1-based inclusive coordinates,
motif context, receptor pocket evidence, and `motif_peptide` route have already
been reviewed:

```bash
ppi-scout run-panel job.json \
  --windows 16,24,34 \
  --output-dir runs/receptor-motif-panel \
  --dry-run

ppi-scout run-panel job.json \
  --windows 16,24,34 \
  --output-dir runs/receptor-motif-panel \
  --live
```

The live command runs unfinished variants sequentially, streams Boltz output,
and resumes automatically when rerun with the same inputs and settings. A
different sequence, window, seed, MSA mode, or backend setting requires a new
output directory. The default MSA mode is `msa: empty`; add `--remote-msa` only
when sequence upload has been explicitly authorized.

For a completely local reusable MSA library, name each A3M with the SHA-256 of
its exact normalized receptor sequence and pass the directory:

```bash
ppi-scout run-panel job.json \
  --msa-library msas \
  --output-dir runs/receptor-motif-panel \
  --live
```

PPI Scout validates the first/query A3M sequence before use. The receptor MSA
is shared across every WT/control task, peptide chains remain `msa: empty`, and
a missing exact match falls back to offline single-sequence mode without a
remote request. Use `python -m ppi_scout.offline` instead of `ppi-scout` to
add a process-wide Python network deny policy for portable execution.

## Representation selection

Use `--mode auto` unless a representation is already supported by structural
or experimental evidence.

| Route | Selection basis |
|---|---|
| `full-length` | The biological question concerns the complete folded proteins and no narrower interface is justified |
| `domain` | A supported interface is localized to a folded domain, or unrelated regions would confound the intended model |
| `motif-peptide` | A localized linear-motif hypothesis has a compatible receptor pocket and evidence for accessible sequence context |
| `needs_review` | Identity, coordinates, topology, membrane context, or structural evidence is insufficient or contradictory |

Protein length alone is not a valid routing criterion. A long protein is not
automatically converted to a peptide, and a short complete protein is not
automatically treated as a peptide.

For an evidence-recorded motif plan:

```bash
ppi-scout plan \
  --fasta-a receptor.fasta \
  --fasta-b partner.fasta \
  --mode auto \
  --motif-owner B \
  --motif-region 412:415 \
  --motif-sequence WEEL \
  --motif-context exposed \
  --receptor-has-motif-pocket \
  -o job.json
```

Coordinates at the CLI boundary are 1-based and inclusive.

## AIM/LIR candidate scanning

Scanning is disabled by default and requires a resolved sequence.

```bash
ppi-scout scan-motifs \
  --fasta partner.fasta \
  -o motif-scan.json
```

The scanner reports canonical `[WFY]xx[LIV]` matches. It does not infer
disorder, solvent accessibility, topology, conservation, receptor
compatibility, biological function, or interaction.

Candidate IDs are assigned by sequence position and must not be interpreted as
ranks. Use the separate `rank`, coordinates, score features, and warnings when
reviewing candidates. PPI Scout does not select a candidate automatically.

## Peptide panel design

Select a candidate explicitly after reviewing the scan:

```bash
ppi-scout scan-motifs \
  --fasta partner.fasta \
  --design-candidate CANDIDATE_ID \
  --windows 16,24,34 \
  --seed 7 \
  -o peptide-panel.json
```

Alternatively, design around a validated coordinate directly:

```bash
ppi-scout design-peptides \
  --fasta partner.fasta \
  --motif 412:415 \
  --windows 16,24,34 \
  --seed 7 \
  -o peptide-panel.json
```

The generated panel includes nested WT windows and matched negative controls.
Use a fixed seed to preserve deterministic scramble controls. Do not evaluate
only the four-residue motif core.

## MSA configuration

MSA policy is an explicit data-governance and modeling decision.

| Mode | Configuration | Data exposure | Operational note |
|---|---|---|---|
| Precomputed/local | Provide an audited local MSA path | Local | Preferred when a validated local workflow is available |
| Single sequence | Set `msa: empty` | Local | Avoids remote transmission but may reduce prediction quality |
| Remote MSA | Authorize `--remote-msa` | Protein sequences are sent to the configured external service | Requires explicit approval |

Do not enable remote MSA as an automatic fallback after a local failure. Do not
store MSA credentials in a job file, command history, report, or repository.

## Prediction execution

### Starting a reviewed job

```bash
ppi-scout run job.json \
  --output-dir runs/receptor-partner \
  --live
```

The first Boltz prediction may download model data into the configured cache.
Preserve the PPI Scout version, Boltz version, job file, compiled YAML, command
arguments, MSA inputs, and logs with the run record.

### Resuming an interrupted run

Inspect the resume plan first:

```bash
ppi-scout resume runs/receptor-partner
```

Restart execution explicitly:

```bash
ppi-scout resume runs/receptor-partner --live
```

If scientific inputs or model parameters must change, create a new job and a
new run directory instead of mutating an existing run record.

## Outputs and result review

### Run artifacts

| Path | Purpose |
|---|---|
| `job.json` | Resolved scientific inputs and workflow policy |
| `resolved_input.yaml` | Boltz input generated from the reviewed job |
| `plan.json` | Compiled execution plan and command arguments |
| `status.json` | Dry-run, running, completed, or failed state |
| `run.json` | Live execution record |
| `predictions/` | Boltz structure and confidence outputs |
| `confidence_summary.csv` | Extracted confidence fields |
| `report.md` | Conservative Markdown summary |
| `report.html` | Self-contained local result view |

`run` and `resume` attempt to update `report.html` automatically. A report
generation failure does not imply that Boltz failed; verify `status.json` and
the live execution record independently.

Regenerate a run report:

```bash
ppi-scout --lang en visualize runs/receptor-partner
```

Render a scan or job JSON file:

```bash
ppi-scout --lang en visualize peptide-panel.json
```

### Review order

1. Confirm the run state in `status.json`.
2. Verify resolved sequences, chain labels, representation, and MSA policy.
3. Review all model samples and extracted confidence fields.
4. Inspect the expected interface in a molecular-structure viewer.
5. Compare WT and matched controls under identical settings.
6. Record alternative poses, unstable interfaces, and contradictory controls.
7. Treat the output as model support, ambiguity, or lack of support; do not
   convert it into a binding claim.

PDB or mmCIF structures can be inspected in applications such as PyMOL or
ChimeraX.

## Data governance

For confidential or unpublished sequences:

- keep FASTA files, jobs, MSAs, logs, predictions, and reports outside version
  control;
- use a project directory covered by the repository `.gitignore`, such as
  `private-projects/`;
- avoid remote MSA unless external sequence transmission has been approved;
- inspect logs and reports before sharing because they may contain sequences
  or local paths;
- do not paste confidential sequences into external chat, ticketing, or email
  systems;
- store model caches outside the repository.

Local Boltz execution does not guarantee that all data remain local. Enabling
remote MSA or using another external service changes the data boundary.

## Troubleshooting

| Symptom | Check | Resolution |
|---|---|---|
| `ppi-scout: command not found` | Active environment and installation path | Activate `.venv` or call the executable through `.venv/bin/ppi-scout` or `.venv\Scripts\ppi-scout.exe` |
| FASTA cannot be read | Working directory, path, case, and extension | Use an absolute path or correct the repository-relative path |
| Invalid residue characters | Sequence alphabet and pasted annotations | Remove residue numbers, punctuation, nucleotide characters, and non-sequence text |
| Motif scan requires a sequence | Input was a name/accession only | Provide `--sequence` or a single-record `--fasta` file |
| No AIM/LIR candidates | Canonical sequence pattern is absent | Record the negative canonical scan; evaluate non-canonical hypotheses separately |
| `ready_to_run: false` | Boltz executable, Python version, accelerator, and `PATH` | Install a compatible Boltz environment and rerun `doctor` |
| GPU out of memory | Input size, sample count, and available VRAM | Preserve the error record and re-plan only with biologically justified boundaries or appropriate hardware |
| `report.html` is missing | Run state and visualization message | Verify `status.json`, then rerun `ppi-scout visualize RUN_PATH` |

For CLI-specific options, run:

```bash
ppi-scout --help
ppi-scout COMMAND --help
```

Do not use high model confidence as the sole basis for a biological conclusion.
