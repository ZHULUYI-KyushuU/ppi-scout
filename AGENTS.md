# Repository guidance

- Keep scientific routing deterministic and auditable.
- Never route solely from protein length.
- Never describe structure confidence as proof of binding.
- Never enable a remote MSA provider without explicit user permission.
- Preserve exact resolved sequences, coordinates, hashes, seeds, and backend
  parameters in generated manifests.
- Prefer standard-library Python for the core planner. Keep heavy prediction
  dependencies isolated behind backend adapters.
- Run the unit tests and the Skill validator after changes.
- Do not commit model weights, MSA caches, run outputs, credentials, or
  unpublished project presets.
