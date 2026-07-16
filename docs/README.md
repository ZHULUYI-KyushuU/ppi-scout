# PPI Scout documentation map

Use this page to find the right document without reading the repository from
top to bottom.

## I want to use PPI Scout

- [`USER_GUIDE.md`](USER_GUIDE.md): complete command-oriented user guide.
- [`../examples/README.md`](../examples/README.md): public Atg8–Atg19 and
  exploratory Atg8–Yta7 examples.
- [`../portable/README.md`](../portable/README.md): portable offline bundle
  layout and platform prerequisites.

## I want to understand how it works

- [`ARCHITECTURE.md`](ARCHITECTURE.md): component map, data flow, generated
  artifacts, and scientific safety boundaries.
- [`../.agents/skills/ppi-scout/SKILL.md`](../.agents/skills/ppi-scout/SKILL.md):
  agent workflow and interpretation policy.

## I want to use a cloud predictor

- [`HELIXFOLD3_CLOUD.md`](HELIXFOLD3_CLOUD.md): explicitly authorized official
  PaddleHelix HelixFold3 workflow.
- [`HELIXFOLD3_CODEX_HANDOFF.md`](HELIXFOLD3_CODEX_HANDOFF.md): exact Codex
  handoff boundary for a reviewed cloud manifest.

## I want to develop or release the project

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md): local development and pull
  request expectations.
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md): version, test, tag, and
  release checks.
- [`../CHANGELOG.md`](../CHANGELOG.md): user-facing version history.

## Which file is authoritative?

The reviewed job JSON and the resolved run manifest are authoritative for one
scientific run. README examples explain behavior but do not replace those
machine-readable records. Upstream Boltz documentation remains authoritative
for the currently installed Boltz command and model behavior.
