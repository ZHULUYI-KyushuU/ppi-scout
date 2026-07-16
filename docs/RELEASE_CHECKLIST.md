# Release checklist

Use this checklist for every PPI Scout release.

## 1. Freeze the version

- Update `project.version` in `pyproject.toml`.
- Update `__version__` in `src/ppi_scout/__init__.py`.
- Update the version-pinned install command in `README.md`.
- Move the matching `CHANGELOG.md` section from “Unreleased” to the release
  date.

The automated metadata test must confirm these values agree.

## 2. Validate the repository

```bash
python -m pip install -e ".[test]"
python -m pytest
python -m compileall -q src scripts tests
ppi-scout --version
ppi-scout --lang en doctor
```

Also build and install the wheel in a clean environment:

```bash
python -m pip install build
python -m build
python -m venv wheel-check
wheel-check/bin/python -m pip install dist/*.whl
wheel-check/bin/ppi-scout --version
```

Use `wheel-check\Scripts\ppi-scout.exe` for the final two commands on Windows.

## 3. Review scientific and privacy boundaries

- Dry-run remains the default.
- Live inference still requires explicit `--live`.
- Remote MSA still requires explicit authorization.
- Local MSA lookup still verifies the exact receptor sequence.
- Reports still distinguish model confidence from experimental evidence.
- No unpublished sequence, MSA cache, credential, model cache, or run output
  is present in the commit.

## 4. Tag and publish

After the release pull request is merged:

```bash
git switch main
git pull --ff-only
git tag -a v0.5.0 -m "PPI Scout 0.5.0"
git push origin v0.5.0
```

Create the GitHub Release from that exact tag. Paste the corresponding
changelog section into the release notes and attach only reviewed artifacts
with checksums.

## 5. Verify as a new user

Install from the public tag in a fresh environment and run the bundled dry-run
example. Confirm that the printed version, README command, Git tag, release
title, and generated job metadata all identify the same release.
