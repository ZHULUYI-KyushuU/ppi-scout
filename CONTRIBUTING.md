# Contributing to PPI Scout

PPI Scout accepts focused fixes, tests, documentation improvements, and
scientifically conservative workflow extensions.

## Before changing code

Preserve these project invariants:

- Never infer protein identity when accession, organism, isoform, or sequence
  is ambiguous.
- Never choose a peptide representation from protein length alone.
- Never enable remote MSA without explicit sequence-upload authorization.
- Never describe structure confidence as experimental proof of binding.
- Preserve exact sequences, coordinates, hashes, seeds, MSA policy, backend
  arguments, and run state in generated artifacts.

## Local development

```bash
git clone https://github.com/ZHULUYI-KyushuU/ppi-scout.git
cd ppi-scout
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest
```

On PowerShell, replace the activation line with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Pull requests

Keep each pull request narrow. Explain the biological or operational reason,
the behavior change, privacy implications, and the checks used to validate it.
Add tests for every new branch in scientific routing, MSA selection, resume
behavior, command compilation, or result parsing.

## Release checklist

Follow [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). A release is
not complete until the runtime version, package metadata, install command,
tag, changelog, and generated artifacts all identify the same version.
