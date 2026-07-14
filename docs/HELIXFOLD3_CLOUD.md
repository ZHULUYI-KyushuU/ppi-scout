# Official HelixFold3 cloud execution

This repository supports a tightly scoped handoff for authorized protein
complex panels on the official PaddleHelix HelixFold3 cloud service. It does
not implement an unofficial API and it does not treat cloud prediction as
experimental evidence of binding.

## Provider and model policy

Use only the official forecast page:

<https://paddlehelix.baidu.com/app/all/helixfold3/forecast>

On the day of submission, inspect the model choices shown by the service and
select the newest stable production HelixFold3 release. HelixFold3.2 is the
minimum acceptable version. Do not select an experimental or preview release,
and do not replace HelixFold3 with Boltz, Chai-1, Protenix, AlphaFold, or a
local installation. If the page exposes no model selector or version label,
record `provider-selected default` instead of guessing.

## Validate the exact panel

From the repository root, run:

```bash
python scripts/validate_helixfold3_panel.py examples/helixfold3-yta7-panel.json
```

Proceed only when the command prints `VALID`. The validator checks the fixed
Atg8 P38182 sequence, all five Yta7-derived sequences, lengths, SHA-256 values,
control mutations, composition preservation, job separation, and provider
policy.

The manifest is the submission boundary. Do not resolve, trim, extend, mutate,
or replace its sequences at submission time.

## Authentication and submission proof

Use an already authenticated browser session. Never request, inspect, copy,
display, export, save, or commit a password, cookie, token, one-time code, or
other credential.

Create five separate protein-complex tasks. Each task must contain exactly two
protein entities: full-length Atg8 as A and one panel peptide as B. Never put
multiple variants into the same complex. Keep small-molecule affinity and
ligand-scoring options disabled.

A filled form or button click is not submission proof. A task is `submitted`
only when PaddleHelix returns a real provider job ID or a persistent result
URL. If the authenticated browser cannot be operated, stop at
`ready_for_manual_submission` and provide the operator a five-row exact-input
table. Continue only after the operator supplies real provider identifiers or
result URLs.

## Receipts and local result layout

Store local execution artifacts under the ignored directory
`runs/helixfold3-yta7/`:

```text
runs/helixfold3-yta7/
|-- submission-receipts.json
|-- results-summary.csv
|-- results-summary.md
|-- report.html
`-- <panel-job-id>/
    `-- provider/          # unmodified complete provider package
```

Each receipt must record the panel job ID, provider job ID or persistent URL,
exact model label, UTC submission time, provider status, entity A and B
SHA-256 values, and an input SHA-256. Compute the input SHA-256 over the UTF-8
bytes of `A_SEQUENCE + "\n" + B_SEQUENCE`.

Monitor all tasks until `completed` or `failed`. Retry only when the provider
explicitly identifies a transient failure, and record any retry without
silently duplicating a task. Do not commit run directories, raw packages, or
screenshots containing personal information.

## Result reporting and interpretation

Copy provider-native confidence fields without renaming or inventing metrics;
leave a blank cell when a metric is absent and document any necessary mapping.
Map output chains to the manifest by exact sequence rather than assuming the
provider preserved A/B labels.

For each top-ranked structure, inspect whether the peptide occupies the
canonical Atg8 AIM/LIR-binding groove and record the peptide residues placed in
the W and L hydrophobic pockets. Compare WT, both single-anchor mutants, the
double-anchor mutant, and the composition-matched scramble under identical
settings. If mutants and the scramble retain the same pose and confidence,
report the result as `nonspecific or ambiguous`.

Model confidence and a plausible or visually attractive pose do not prove
binding, affinity, or biological function. Lead the final report with exactly
one of `NOT SUBMITTED`, `PARTIALLY SUBMITTED`, `RUNNING`, `COMPLETED`, or
`FAILED`; use `COMPLETED` only after all five tasks are terminal and all
completed raw result packages have been downloaded.
