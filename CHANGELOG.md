# Changelog

All notable user-facing changes are recorded here. PPI Scout follows semantic
versioning: major versions may change compatibility, minor versions add
features, and patch versions contain compatible fixes.

## 0.5.0 — Unreleased

### Added

- One-command `run-panel` execution for reviewed motif-peptide hypotheses.
- Matched WT, anchor-mutant, `AxxA`, `AAAA`, reverse-decoy, flank-scramble,
  and composition-matched scramble tasks.
- Automatic resume, progress streaming, confidence collection, Markdown
  reporting, and self-contained HTML visualization for a complete panel.
- Exact-sequence local receptor MSA lookup and a hard-offline entry point.
- Portable macOS arm64 and Windows WSL2 release preparation.
- Official PaddleHelix HelixFold3 manifest validation and handoff guidance.
- Cross-version and cross-platform continuous integration.
- Documentation and architecture indexes for faster repository orientation.

### Changed

- Reorganized the README around a short start path, a command map, scientific
  boundaries, and links to detailed documentation.
- Added automated checks that keep the package version and README install tag
  synchronized.

### Fixed

- Closed the streamed Boltz stdout pipe after execution to avoid a resource
  warning in repeated or test runs.

## 0.4.0 — 2026-07-13

- Initial public CLI, Codex Skill, deterministic routing, motif scanning,
  peptide/control design, local Boltz execution, result collection, and
  offline HTML reporting.
