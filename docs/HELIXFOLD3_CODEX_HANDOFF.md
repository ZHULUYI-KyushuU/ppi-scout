# Codex Handoff: HelixFold3 Cloud Execution

Copy the prompt below into Codex with the PPI Scout repository open. The prompt
is intentionally strict about provider selection, authentication, receipts,
and scientific interpretation.

```text
You are taking over the public repository ZHULUYI-KyushuU/ppi-scout.

Objective
Run the public Saccharomyces cerevisiae Atg8–Yta7 five-job control panel on the
official PaddleHelix cloud service using the strongest stable production
HelixFold3 model available at submission time. HelixFold3.2 is the minimum
acceptable version. Do not substitute Boltz, Protenix, Chai-1, AlphaFold, or a
local HelixFold installation.

Authoritative files
1. Read AGENTS.md.
2. Read .agents/skills/ppi-scout/SKILL.md.
3. Read .agents/skills/ppi-scout/references/helixfold3-cloud.md.
4. Read docs/HELIXFOLD3_CLOUD.md.
5. Treat examples/helixfold3-yta7-panel.json as the exact job manifest.

Authorization and security
The operator has authorized submission of only the exact public P38182 Atg8
sequence and the five exact public Yta7-derived sequences in the manifest to
the official PaddleHelix service. This does not authorize submission of any
other sequence. Use the operator's already authenticated browser session if it
is available. Never ask for, display, copy, export, or commit a password,
cookie, session token, one-time code, or API credential.

Provider and model selection
Use https://paddlehelix.baidu.com/app/all/helixfold3/forecast. Re-check the
official service at execution time. Select the newest stable production
HelixFold3 model shown there, with HelixFold3.2 as the minimum. Do not select an
experimental preview merely because its version is newer. Record the exact
model label. If the service does not expose a selector or version label, record
"provider-selected default" and save a dated page screenshot or equivalent
receipt; do not guess the version.

Submission procedure
1. From the repository root, run `python scripts/validate_helixfold3_panel.py examples/helixfold3-yta7-panel.json`. Stop if it does not print `VALID`.
2. Submit five separate protein-complex jobs. Each job contains exactly two
   protein entities: A is full-length Atg8 and B is one panel peptide. Never put
   multiple panel peptides into the same prediction.
3. Use the manifest job ID as the provider job name when the service permits.
4. Do not enable ligand-affinity or small-molecule scoring options.
5. After each submission, immediately record the provider job ID or durable
   result URL, exact model label, UTC submission time, input hash, and current
   status in runs/helixfold3-yta7/submission-receipts.json.
6. A form fill or button click is not proof of submission. Mark a job
   "submitted" only after the provider returns a durable job ID or result URL.
7. Monitor all jobs until completed or failed. Report queued and running jobs
   accurately. Retry only when the provider explicitly reports a transient
   failure; never create duplicate jobs silently.

Authenticated-browser fallback
If Codex cannot operate the existing authenticated browser session, do not ask
for login secrets and do not claim that any job was submitted. Instead, stop at
"ready_for_manual_submission" and give the operator one compact table with the
five job names and the exact A/B sequences to paste into the official form.
Continue monitoring and downloading only after the operator supplies the five
provider job IDs or result URLs.

Official API mode
Use API mode only if the operator already has an official paid API credential
and the current PaddleHelix SDK/API documentation is accessible. Derive the
endpoint, authentication header, request schema, polling schema, and download
method exclusively from that current official documentation. Put the token in
an environment variable or secret manager. First generate a redacted dry-run
request and verify it. If any part of the contract is unknown, stop with
"api_contract_required"; do not invent an endpoint or payload and do not adapt
the open-source local input JSON as an assumed cloud API request.

Result collection
For each completed job, download the entire original provider result package
to runs/helixfold3-yta7/<panel-job-id>/provider/. Do not rename or edit raw
provider files. Write derived artifacts outside provider/. Create:
- submission-receipts.json with one receipt per job;
- results-summary.csv containing provider-native confidence metrics;
- results-summary.md with a concise WT-versus-controls comparison;
- report.html with links to all structures and a clearly labeled interpretation.
Use blank cells for absent metrics and document any metric mapping. Never make
up ipTM, pTM, pLDDT, ranking, or interface values.

Scientific review
Map output chains back to the manifest by exact sequence, not by assuming the
provider retained A/B labels. For every top-ranked structure, inspect whether
the peptide occupies the canonical Atg8 AIM/LIR-binding groove and record the
candidate residues placed in the W and L hydrophobic pockets. Compare WT,
YAEI-anchor mutant, FDFL-anchor mutant, double mutant, and composition-matched
scramble under identical model settings. If mutants and scramble retain the
same pose and confidence, describe the result as nonspecific or ambiguous.
Model confidence and a plausible pose are not proof of binding or affinity.

Repository discipline
Do not commit credentials, browser data, unpublished sequences, provider raw
outputs, screenshots containing personal information, or run directories.
Commit only reusable workflow/documentation changes requested by the operator.
Before committing, run git diff --check, the test suite, and the Skill
validator. Do not include unrelated existing worktree changes.

Final report
Lead with one of these exact states: NOT SUBMITTED, PARTIALLY SUBMITTED,
RUNNING, COMPLETED, or FAILED. Then provide the model label, a five-row job
status table with real provider IDs, output paths, control comparison, and any
blocker. Do not say "completed" unless all five jobs have terminal results and
the raw outputs were downloaded.
```
