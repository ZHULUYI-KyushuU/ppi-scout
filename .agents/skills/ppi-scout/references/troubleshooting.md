# Troubleshooting

Keep failures explicit. Do not repair them by changing the biological route, sequence, MSA policy, or controls silently.

| Symptom | Check | Action |
|---|---|---|
| `ppi-scout` is not found | Active environment and editable install | Activate the project environment and install the repository package; then run `ppi-scout --help`. |
| Skill is not discovered | Current repository and `.agents/skills/ppi-scout/SKILL.md` | Open the repository root in Codex and select PPI Scout from the available Skills. |
| Protein name is ambiguous | Organism, strain, accession, isoform | Supply an exact accession, FASTA, or sequence. Do not choose silently. |
| Motif coordinates disagree | Source sequence and convention | Use 1-based inclusive `START:END`; verify the extracted residues before planning. |
| `doctor` cannot find Boltz | `boltz` on `PATH`; `boltz predict --help` | Install or expose a compatible local Boltz environment outside the workflow, then rerun `doctor`. |
| No NVIDIA GPU is detected | `nvidia-smi`, driver, device visibility | Use an appropriate GPU host. Treat CPU execution as potentially impractical; do not start it accidentally. |
| CUDA out of memory | Sequence length, samples, parallelism, other GPU jobs | Stop, preserve logs, and create a new reviewed plan with justified resource changes. Do not truncate proteins automatically. |
| Remote MSA is blocked or not permitted | Job `privacy` and `execution.remote_msa` | Use an approved local/precomputed MSA or `msa: empty`; document the accuracy tradeoff. |
| Remote MSA authentication fails | Secret source and server configuration | Keep credentials in environment variables or approved secret storage; never paste them into job JSON or logs. |
| Boltz input is rejected | Unique chain IDs, amino-acid alphabet, YAML, MSA paths | Run `ppi-scout run JOB --dry-run`, inspect the compiled input, and correct the plan rather than editing run artifacts. |
| Run is interrupted | Run ID, manifest, logs, cached outputs | Use `ppi-scout resume RUN_ID`. Create a new job if scientific parameters must change. |
| No confidence JSON is found | Run completion and output path | Preserve the incomplete status; inspect logs and resume. Do not report a negative biological result. |
| WT and controls all score highly | Expected pocket, clashes, window choice, MSA sensitivity | Label specificity ambiguous and inspect matched structures; do not claim binding from ipTM. |
| Affinity files appear in a PPI result | Imported or incorrectly configured run | Ignore affinity values for PPI/peptide interpretation and remove affinity from the next planned input. |

When a failure remains unresolved, return the failing command, exit status, relevant log path, current MSA mode, and the next safe diagnostic step. Do not expose sequences or credentials in a shared issue unless the user confirms they are public.
