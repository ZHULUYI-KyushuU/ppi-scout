# Local Boltz execution

Use PPI Scout as a local-first planner and audit layer around a separately installed `boltz` executable. Never install or upgrade Boltz during `doctor`, `plan`, or `run` without a separate user request.

## Install Boltz when requested

Use a dedicated Python 3.10-3.12 environment. When PPI Scout will execute
Boltz, install both packages in the same environment so the `boltz` executable
is available on `PATH`.

For an NVIDIA CUDA environment, use the upstream recommended package extra:

```bash
python -m pip install --upgrade "boltz[cuda]"
```

For CPU-only or non-CUDA hardware, omit the extra:

```bash
python -m pip install --upgrade boltz
```

Upstream documentation states that CPU inference is significantly slower.
Validate the installation before planning a live run:

```bash
boltz predict --help
ppi-scout doctor --format json --output doctor.json
```

Boltz downloads model data on first prediction. Its default cache is
`~/.boltz`; `BOLTZ_CACHE` can point to another absolute path. Keep the cache
outside the repository and do not commit model weights. For Windows CUDA
workstations, prefer a validated WSL2/Ubuntu environment.

## Check, plan, then run

```bash
ppi-scout doctor --format json --output doctor.json
ppi-scout plan PROTEIN_A PROTEIN_B --organism "ORGANISM" --mode auto -o job.json
ppi-scout run job.json --output-dir runs/JOB_NAME --dry-run
ppi-scout run job.json --output-dir runs/JOB_NAME --live
```

Require a successful `doctor` check and a reviewed job before live execution. `run` defaults to dry-run; `--live` is the explicit resource-use boundary. The dry run must display the resolved input path, output directory, MSA mode, and complete Boltz argument vector.

After every default dry-run or explicit live run, PPI Scout automatically
attempts `OUTPUT_DIR/report.html`. The same applies to `resume`, which remains a
dry-run unless `--live` is supplied. Users can double-click this self-contained
HTML file; a local web server is not required. Treat page generation as a
separate presentation step: failure to generate HTML does not establish that
Boltz failed. Check the run status and `status.json` separately from any
visualization status or warning. Use manual `visualize` only to regenerate a
page or render a scan/job JSON.

PPI Scout compiles the upstream form:

```bash
boltz predict INPUT.yaml --out_dir OUTPUT_DIR
```

For a reviewed `motif_peptide` job, use `run-panel` to compile and execute all
matched controls without manually creating separate inputs:

```bash
ppi-scout run-panel job.json --windows 24 --output-dir runs/JOB_NAME-panel --dry-run
ppi-scout run-panel job.json --windows 24 --output-dir runs/JOB_NAME-panel --live
```

The live form streams Boltz output and automatically skips completed variants
when rerun with the identical manifest. It also writes the panel manifest,
compiled plan, confidence CSV, Markdown report, and offline HTML page. Change
the output directory whenever sequences, windows, seeds, MSA policy, output
format, or sampling settings change. Apple Silicon defaults to the MPS-backed
GPU path with specialized kernels disabled. Do not add `--remote-msa` unless
sequence upload has been explicitly authorized.

Capture the PPI Scout version, Boltz version/help probe, exact job JSON, compiled YAML, full command, resolved sequences, MSA inputs, and logs in the run directory.

## Choose MSA mode explicitly

- **Precomputed/local MSA:** provide an audited local MSA path. Prefer this for confidential sequences when local generation is available.
- **Remote MSA:** add `--use_msa_server` only after explicit permission. The upstream default server may receive the submitted protein sequences. Record the server URL and consent decision.
- **Single-sequence:** set `msa: empty` for each protein. Record that this avoids remote MSA disclosure but can reduce prediction accuracy.

Never switch from local or single-sequence mode to a remote service after a failure. Never place MSA credentials in a job file, command log, report, or repository.

## Compile protein complexes safely

- Prefer Boltz YAML input; use unique chain IDs and exact uppercase sequences.
- Encode a peptide as a protein chain, normally with `msa: empty`.
- Keep 1-based inclusive biological coordinates in the PPI Scout manifest even when generated files use another internal convention.
- Omit `properties.affinity` for every protein-protein and protein-peptide job. Boltz documents affinity support for a small-molecule ligand against a protein target only.
- Keep WT and every control under the same model, MSA, template, sampling, and output settings.
- Use `--override` only when intentionally invalidating cached preprocessing or predictions; record why.

## Resume and import

Use `ppi-scout resume RUN_ID` to inspect continuation of the recorded job without changing its scientific inputs; add `--live` only to explicitly execute the resumed prediction. Both forms automatically attempt `RUN_ID/report.html`. If parameters must change, create a new planned job with a new name. Use `ppi-scout import-legacy SOURCE -o job.json` for older results, mark missing provenance fields as unknown, then analyze without inventing them.

Upstream references:

- <https://github.com/jwohlwend/boltz>
- <https://pypi.org/project/boltz/>
- <https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md>
