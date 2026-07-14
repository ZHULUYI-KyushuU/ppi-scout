# Official PaddleHelix HelixFold3 cloud workflow

Use this workflow only when the operator explicitly requests remote execution
and authorizes submission of the exact sequences in the manifest. The public
operator guide is
[docs/HELIXFOLD3_CLOUD.md](../../../../docs/HELIXFOLD3_CLOUD.md).

## Establish the submission boundary

1. Treat the named manifest as authoritative. Do not resolve, extend, trim,
   mutate, or replace any sequence during submission.
2. Run `python scripts/validate_helixfold3_panel.py MANIFEST` and stop unless it
   prints `VALID`.
3. Submit only to the official PaddleHelix page:
   `https://paddlehelix.baidu.com/app/all/helixfold3/forecast`.
4. Use the operator's existing authenticated browser state. Never request,
   read, copy, display, export, save, or commit credentials, cookies, tokens,
   or verification codes.

If the authenticated session cannot be operated, stop at
`ready_for_manual_submission`, create a five-row table containing the exact job
names and A/B sequences, and wait for the operator to provide real provider job
IDs or persistent result URLs. Do not infer submission from a filled form or a
button click.

## Select and record the model

Re-check the official page on the submission date. Select the newest model
explicitly labeled as a stable production HelixFold3 release, with
HelixFold3.2 as the minimum. Do not choose an experimental or preview release,
and do not substitute Boltz, Chai-1, Protenix, or a local model. If the page
exposes no model version or selector, record exactly
`provider-selected default`; do not infer a version from marketing text or
prior knowledge.

## Submit independent protein complexes

- Create one provider task per manifest job.
- Put full-length Atg8 in protein entity A and exactly one panel peptide in
  protein entity B.
- Never put multiple panel peptides in one complex.
- Use the manifest job ID as the provider task name when supported.
- Leave small-molecule affinity and ligand-scoring features disabled.
- Keep all model settings matched across the panel.

Mark a task `submitted` only after the provider returns a real job ID or a
persistent result URL. Immediately record the provider identifier or URL,
exact model label, UTC timestamp, entity sequence SHA-256 values, deterministic
input SHA-256, and provider status in
`runs/helixfold3-yta7/submission-receipts.json`. Define the deterministic input
hash as SHA-256 over the UTF-8 bytes of `A_SEQUENCE + "\n" + B_SEQUENCE`.

## Monitor and collect results

Monitor every task until `completed` or `failed`. Retry only an explicitly
reported transient failure, and never create an unrecorded duplicate. Download
each complete, unmodified provider package to
`runs/helixfold3-yta7/<panel-job-id>/provider/`. Keep run directories and raw
provider artifacts out of Git.

Create these derived artifacts outside every `provider/` directory:

- `submission-receipts.json` with one receipt per job;
- `results-summary.csv` with provider-native metrics and blank cells for absent
  values;
- `results-summary.md` with a concise matched-control comparison;
- `report.html` linking the downloaded structures and clearly separating raw
  metrics from interpretation.

Map output chains to inputs by exact sequence rather than provider chain label.
For the top-ranked structure of each job, inspect the canonical Atg8 AIM/LIR
groove and record which peptide residues, if any, occupy the W and L pockets.
If mutants and the composition-matched scramble retain the same pose and
confidence as WT, conclude `nonspecific or ambiguous`. A confident or plausible
pose is not proof of binding or affinity.

Lead the final report with exactly one of `NOT SUBMITTED`,
`PARTIALLY SUBMITTED`, `RUNNING`, `COMPLETED`, or `FAILED`. Use `COMPLETED` only
when all five tasks reached a terminal state and every completed task's raw
package was downloaded.
