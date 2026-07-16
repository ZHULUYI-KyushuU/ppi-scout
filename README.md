# PPI Scout

[![Tests](https://github.com/ZHULUYI-KyushuU/ppi-scout/actions/workflows/ci.yml/badge.svg)](https://github.com/ZHULUYI-KyushuU/ppi-scout/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

PPI Scout prepares and runs reproducible local Boltz screens for two proteins
or a protein plus a motif peptide. It verifies the inputs, creates matched
controls, resumes unfinished work, and writes a local result page.

> A predicted structure or high confidence score is not proof of binding.

## Easiest option: Windows offline package

Open [Releases](https://github.com/ZHULUYI-KyushuU/ppi-scout/releases/latest),
download `PPI-Scout-Windows-Installer-v0.5.0.zip`, extract it, and double-click
`Download-Install-and-Run.cmd`. The first setup downloads and verifies about 10.4 GB;
later predictions can run without internet access.

The offline package already contains Python, PPI Scout, Boltz, model files, and
an Ubuntu WSL image. Windows must have WSL2 enabled. An NVIDIA GPU needs a
Windows driver with WSL support. See [`offline/README.md`](offline/README.md).

## Install from source

```bash
python -m pip install "git+https://github.com/ZHULUYI-KyushuU/ppi-scout.git@v0.5.0"
python -m pip install "boltz[cuda]"   # NVIDIA CUDA
ppi-scout doctor
```

Use `python -m pip install boltz` instead on a non-CUDA computer. CPU
prediction is possible but much slower.

## Four commands

| Command | What it does | Uses GPU? |
|---|---|---:|
| `ppi-scout doctor` | Checks Python, Boltz, and the accelerator | No |
| `ppi-scout plan` | Verifies two inputs and writes a job file | No |
| `ppi-scout scan` | Lists AIM/LIR sequence candidates | No |
| `ppi-scout run` | Dry-runs or executes a reviewed job and creates all reports | Only with `--live` |

Running `ppi-scout` without a command starts the Chinese/English/Japanese
guided intake.

## Included Atg8–Yta7 example

This safe command builds the complete WT/control plan without starting Boltz:

```bash
ppi-scout run examples/atg8-yta7-job.json \
  --windows 24 \
  --output-dir runs/atg8-yta7 \
  --dry-run
```

Review the exact sequences, FDFL coordinates, controls, MSA policy, and compute
cost. Then start or continue the prediction explicitly:

```bash
ppi-scout run examples/atg8-yta7-job.json \
  --windows 24 \
  --output-dir runs/atg8-yta7 \
  --live
```

Motif jobs automatically generate WT, anchor-mutant, `AAAA`, reverse, flank
scramble, and composition-matched controls. Rerunning the same command skips
completed controls.

## Results

Everything for one run stays in its output folder:

| File | Meaning |
|---|---|
| `status.json` | Authoritative run state and errors |
| `plan.json` | Exact Boltz tasks and commands |
| `confidence_summary.csv` | Raw confidence fields found in the outputs |
| `report.md` | Conservative text summary |
| `report.html` | Self-contained local result page; open by double-clicking |
| `predictions/` and `logs/` | Raw predictions and execution logs |

## MSA, privacy, and interpretation

- Remote MSA is off unless `--remote-msa` is explicitly supplied.
- `--remote-msa` sends protein sequences to an external MSA service.
- Use `--receptor-msa FILE` for one audited local MSA or `--msa-library DIR`
  for exact-sequence offline lookup.
- Never commit private sequences, credentials, MSA caches, model weights, or
  run directories.
- Compare WT with matched controls under identical settings. Do not describe
  ipTM, pLDDT, rank score, or a plausible pose as experimental binding.
- Do not use the Boltz small-molecule affinity output for protein–protein or
  protein–peptide affinity.

## Repository map

```text
examples/       one public local example and one optional cloud manifest
offline/        Windows/macOS offline launchers and verified model checksums
src/ppi_scout/  program code
tests/          automated safety and behavior checks
scripts/        offline package builder and cloud-manifest validator
locales/        Chinese, English, and Japanese messages
docs/           optional HelixFold3 cloud workflow
```

The code is split into small modules so sequence resolution, scientific
routing, control design, prediction, and reporting cannot silently rewrite one
another.

## Optional cloud workflow

The core program runs locally. The separate, explicitly authorized official
PaddleHelix HelixFold3 workflow is documented in
[`docs/HELIXFOLD3.md`](docs/HELIXFOLD3.md).

## Development

```bash
python -m pip install -e ".[test]"
python -m pytest
python -m compileall -q src scripts tests
```

PPI Scout is distributed under the [MIT License](LICENSE).
