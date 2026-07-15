# Atg8–Atg19 Example

This example uses the established *Saccharomyces cerevisiae* Atg8–Atg19
system. All input sequences are public, reviewed UniProtKB records.

| Chain | Protein | UniProtKB | Length | Role in this example |
|---|---|---|---:|---|
| A | Atg8 | [`P38182`](https://www.uniprot.org/uniprotkb/P38182/entry) | 117 aa | AIM-binding receptor |
| B | Atg19 | [`P35193`](https://www.uniprot.org/uniprotkb/P35193/entry) | 415 aa | Motif-bearing partner |

UniProtKB annotates Atg19 residues 406–415 as an Atg8-binding region and the
C-terminal `WEEL` sequence at residues 412–415 as the required WXXL motif.
The motif has also been characterized structurally (PDB
[`2ZPN`](https://www.rcsb.org/structure/2ZPN)).

## Included artifacts

- `atg8-scer-p38182.fasta`: reviewed Atg8 sequence.
- `atg19-scer-p35193.fasta`: reviewed Atg19 sequence.
- `atg8-atg19-job.json`: resolved motif-peptide job plan.
- `atg19-aim-scan-and-panel.json`: complete scan plus peptide/control panel.

## Reproduce the example

```bash
ppi-scout scan-motifs \
  --fasta examples/atg19-scer-p35193.fasta \
  --design-candidate aim-009 \
  --windows 16,24,34 \
  --seed 7 \
  -o examples/atg19-aim-scan-and-panel.json

ppi-scout --lang en visualize \
  examples/atg19-aim-scan-and-panel.json
```

The scanner reports every canonical sequence match. `aim-009` is selected
because it corresponds to the experimentally annotated C-terminal motif—not
because it has the highest sequence-only score. This illustrates why motif
selection requires biological evidence rather than automatic rank selection.

The HTML output is self-contained and opens locally without a server. This
example demonstrates planning and peptide design; it does not run Boltz or
generate a new binding claim.

## One-command local Atg8–Yta7 FDFL panel

`atg8-yta7-fdfl-job.json` records an exploratory motif-peptide hypothesis for
Atg8 and Yta7 P40340 residues 43–66. The `FDFL` core is peptide positions
11–14 and source-protein positions 53–56. Review the warnings in the job before
execution.

Prepare the complete 10-task panel without inference:

```bash
ppi-scout run-panel examples/atg8-yta7-fdfl-job.json \
  --windows 24 \
  --design-seed 7 \
  --output-dir runs/atg8-yta7-fdfl \
  --dry-run
```

After accepting the exact sequences, coordinates, controls, single-sequence
MSA tradeoff, and expected compute cost, run or resume every unfinished task:

```bash
ppi-scout run-panel examples/atg8-yta7-fdfl-job.json \
  --windows 24 \
  --design-seed 7 \
  --output-dir runs/atg8-yta7-fdfl \
  --live
```

The default does not contact a remote MSA service. The output is structural
model evidence for an exploratory hypothesis, not proof of binding.

## HelixFold3 Atg8–Yta7 control panel

`helixfold3-yta7-panel.json` is a separate, exact five-job manifest for an
explicitly authorized official PaddleHelix HelixFold3 cloud run. Validate its
fixed sequences and controls before any submission:

```bash
python scripts/validate_helixfold3_panel.py examples/helixfold3-yta7-panel.json
```

Follow [the official-cloud guide](../docs/HELIXFOLD3_CLOUD.md). Each variant is
an independent two-protein task; the five peptides must never be combined into
one complex.
