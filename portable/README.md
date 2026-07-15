# PPI Scout offline bundles

The portable bundle has two platform launchers and one shared, immutable model
payload. Runtime inference never needs Codex, ChatGPT, a browser, an MSA
service, Hugging Face, or any other network service.

## Bundle layout

```text
PPI-Scout-Offline/
  Run-PPI-Scout-macOS.command
  Run-PPI-Scout-Windows.cmd
  checksums.sha256
  jobs/current-job.json
  msas/<receptor-sequence-sha256>.a3m
  models/{mols.tar,boltz2_conf.ckpt,boltz2_aff.ckpt,SHA256SUMS}
  macos-arm64/ppi-scout-runtime-macos-arm64.tar.gz
  windows-wsl2-x64/{ubuntu-rootfs.tar.gz,ppi-scout-runtime-linux-x86_64.tar.gz,...}
  results/
```

The first launch verifies and installs the runtime and model cache to fast local
storage. Later launches resume unfinished panel tasks. Jobs, logs, structures,
tables, and HTML reports remain under `results/` in the bundle.

The Windows launcher imports its bundled Ubuntu root filesystem as a private
WSL2 distribution. WSL2 must already be enabled in Windows; no Microsoft Store
or network access is required by the bundle itself. NVIDIA GPU use additionally
requires a compatible Windows NVIDIA driver with WSL support. CPU fallback is
automatic but substantially slower.

## MSA policy

Receptor MSAs are optional and must be named by the SHA-256 of the exact
normalized receptor sequence. The query sequence inside the A3M is checked
before use. Peptide chains always use `msa: empty`. If no exact local A3M is
present, execution stays offline and falls back to single-sequence mode.

## Release packaging

GitHub Release assets must each be under 2 GiB, so large files are split into
ordered parts by `scripts/prepare_offline_release.py`. Bootstrap launchers
download all parts once, verify every SHA-256, reconstruct the bundle, and then
hand control to the platform-specific offline launcher.
