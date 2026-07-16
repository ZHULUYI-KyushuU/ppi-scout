# Example: Atg8 and the Yta7 FDFL region

This is the repository's only local example. It uses public *Saccharomyces
cerevisiae* sequences: full-length Atg8 P38182 as chain A and Yta7 P40340
residues 43–66 as chain B. The exploratory `FDFL` core is Yta7 residues 53–56.

Files:

- `atg8.fasta` and `yta7-43-66.fasta`: exact inputs.
- `atg8-yta7-job.json`: reviewed local Boltz job.
- `helixfold3-yta7-panel.json`: optional five-job cloud control manifest.

Safe dry-run (does not start prediction):

```bash
ppi-scout run examples/atg8-yta7-job.json \
  --windows 24 \
  --output-dir runs/atg8-yta7 \
  --dry-run
```

After reviewing the inputs, controls, MSA policy, and compute cost:

```bash
ppi-scout run examples/atg8-yta7-job.json \
  --windows 24 \
  --output-dir runs/atg8-yta7 \
  --live
```

Rerunning the same command continues unfinished controls. The run directory
always contains `status.json`, `confidence_summary.csv`, `report.md`, and a
self-contained `report.html` that opens by double-clicking.

The prediction is structural-model evidence, not proof that Atg8 and Yta7
bind. For the optional official HelixFold3 workflow, see
[`docs/HELIXFOLD3.md`](../docs/HELIXFOLD3.md).
