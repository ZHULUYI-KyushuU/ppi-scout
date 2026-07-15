#!/usr/bin/env bash
set -euo pipefail

BUNDLE_ROOT="${1:?bundle root is required}"
VERSION="0.4.0"
STATE_ROOT="/opt/ppi-scout-offline/$VERSION"
RUNTIME_ARCHIVE="$BUNDLE_ROOT/windows-wsl2-x64/ppi-scout-runtime-linux-x86_64.tar.gz"
RUNTIME_ROOT="$STATE_ROOT/runtime"
CACHE_ROOT="$STATE_ROOT/boltz-cache"
JOB="$BUNDLE_ROOT/jobs/current-job.json"
MSA_LIBRARY="$BUNDLE_ROOT/msas"
RESULT_ROOT="$BUNDLE_ROOT/results/atg8-yta7-fdfl"

fail() {
  echo "错误：$1" >&2
  exit 1
}

[[ "$(uname -m)" == "x86_64" ]] || fail "这个 Windows 包只支持 x86_64 WSL2。"
[[ -f "$RUNTIME_ARCHIVE" ]] || fail "缺少 Linux x86_64 离线运行时。"
[[ -f "$JOB" ]] || fail "缺少任务文件。"
[[ -f "$BUNDLE_ROOT/models/SHA256SUMS" ]] || fail "缺少模型校验清单。"
mkdir -p "$STATE_ROOT" "$RESULT_ROOT" "$MSA_LIBRARY"

if [[ ! -x "$RUNTIME_ROOT/python/bin/python3" ]]; then
  echo "首次安装 Linux x86_64 本地运行时……"
  rm -rf "$STATE_ROOT/runtime.tmp"
  mkdir -p "$STATE_ROOT/runtime.tmp"
  tar -xzf "$RUNTIME_ARCHIVE" -C "$STATE_ROOT/runtime.tmp"
  rm -rf "$RUNTIME_ROOT"
  mv "$STATE_ROOT/runtime.tmp" "$RUNTIME_ROOT"
fi

if [[ ! -f "$CACHE_ROOT/.models-ok" ]]; then
  echo "校验并安装 Boltz 模型（首次约需数分钟）……"
  (cd "$BUNDLE_ROOT/models" && sha256sum -c SHA256SUMS) || fail "模型文件校验失败。"
  rm -rf "$CACHE_ROOT/mols"
  mkdir -p "$CACHE_ROOT"
  cp -p "$BUNDLE_ROOT/models/boltz2_conf.ckpt" "$CACHE_ROOT/"
  cp -p "$BUNDLE_ROOT/models/boltz2_aff.ckpt" "$CACHE_ROOT/"
  tar -xf "$BUNDLE_ROOT/models/mols.tar" -C "$CACHE_ROOT"
  echo "$VERSION" > "$CACHE_ROOT/.models-ok"
fi

PYTHON="$RUNTIME_ROOT/python/bin/python3"
[[ -x "$PYTHON" ]] || fail "本地 Python 运行时不可执行。"
[[ -d "$CACHE_ROOT/mols" && -f "$CACHE_ROOT/boltz2_conf.ckpt" && -f "$CACHE_ROOT/boltz2_aff.ckpt" ]] || \
  fail "本地模型缓存不完整。"
export PATH="$RUNTIME_ROOT/python/bin:$PATH"

ENGINE_ARGS=()
if ! "$PYTHON" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)'; then
  echo "未检测到可用 NVIDIA CUDA；切换为较慢的 CPU 模式。"
  ENGINE_ARGS=(--accelerator cpu --no-kernels)
fi

BOLTZ_CACHE="$CACHE_ROOT" "$PYTHON" -m ppi_scout.offline doctor >/dev/null
if [[ "${PPI_SCOUT_SELF_TEST:-0}" == "1" ]]; then
  echo "离线包自检完成：运行时、模型、断网入口均已就绪。"
  exit 0
fi
BOLTZ_CACHE="$CACHE_ROOT" \
  "$PYTHON" -m ppi_scout.offline \
  --lang zh-CN \
  run-panel "$JOB" \
  --windows 24 \
  --design-seed 7 \
  --msa-library "$MSA_LIBRARY" \
  --output-dir "$RESULT_ROOT" \
  "${ENGINE_ARGS[@]}" \
  --live 2>&1 | tee "$RESULT_ROOT/launcher.log"

[[ -f "$RESULT_ROOT/report.html" ]] || fail "没有生成本地结果页，请查看 launcher.log。"
