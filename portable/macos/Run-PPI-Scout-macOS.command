#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VERSION="0.4.0"
STATE_ROOT="${PPI_SCOUT_STATE_ROOT:-$HOME/Library/Application Support/PPI-Scout-Offline/$VERSION}"
RUNTIME_ARCHIVE="$ROOT/macos-arm64/ppi-scout-runtime-macos-arm64.tar.gz"
RUNTIME_ROOT="$STATE_ROOT/runtime"
CACHE_ROOT="$STATE_ROOT/boltz-cache"
JOB="$ROOT/jobs/current-job.json"
MSA_LIBRARY="$ROOT/msas"
RESULT_ROOT="$ROOT/results/atg8-yta7-fdfl"

fail() {
  print -u2 "\n错误：$1"
  print -u2 "按回车关闭。"
  read -r
  exit 1
}

[[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]] || \
  fail "这个入口只支持 Apple Silicon（M1/M2/M3/M4）Mac。"
[[ -f "$RUNTIME_ARCHIVE" ]] || fail "缺少 macOS 离线运行时：$RUNTIME_ARCHIVE"
[[ -f "$JOB" ]] || fail "缺少任务文件：$JOB"
[[ -f "$ROOT/models/SHA256SUMS" ]] || fail "缺少模型校验清单。"
mkdir -p "$STATE_ROOT" "$ROOT/results" "$MSA_LIBRARY"

if [[ ! -x "$RUNTIME_ROOT/python/bin/python3" ]]; then
  print "[1/4] 首次安装 macOS 本地运行时……"
  rm -rf "$STATE_ROOT/runtime.tmp"
  mkdir -p "$STATE_ROOT/runtime.tmp"
  tar -xzf "$RUNTIME_ARCHIVE" -C "$STATE_ROOT/runtime.tmp" || fail "运行时解包失败。"
  rm -rf "$RUNTIME_ROOT"
  mv "$STATE_ROOT/runtime.tmp" "$RUNTIME_ROOT"
else
  print "[1/4] 本地运行时已就绪。"
fi

if [[ ! -f "$CACHE_ROOT/.models-ok" ]]; then
  print "[2/4] 校验并安装 Boltz 模型（首次约需数分钟）……"
  (cd "$ROOT/models" && shasum -a 256 -c SHA256SUMS) || fail "模型文件校验失败，请重新下载离线包。"
  rm -rf "$CACHE_ROOT/mols"
  mkdir -p "$CACHE_ROOT"
  cp -p "$ROOT/models/boltz2_conf.ckpt" "$CACHE_ROOT/"
  cp -p "$ROOT/models/boltz2_aff.ckpt" "$CACHE_ROOT/"
  tar -xf "$ROOT/models/mols.tar" -C "$CACHE_ROOT" || fail "化学组分库解包失败。"
  print "$VERSION" > "$CACHE_ROOT/.models-ok"
else
  print "[2/4] 本地模型已就绪。"
fi

PYTHON="$RUNTIME_ROOT/python/bin/python3"
[[ -x "$PYTHON" ]] || fail "本地 Python 运行时不可执行。"
[[ -d "$CACHE_ROOT/mols" && -f "$CACHE_ROOT/boltz2_conf.ckpt" && -f "$CACHE_ROOT/boltz2_aff.ckpt" ]] || \
  fail "本地模型缓存不完整。"
export PATH="$RUNTIME_ROOT/python/bin:$PATH"

print "[3/4] 执行完全离线自检……"
BOLTZ_CACHE="$CACHE_ROOT" "$PYTHON" -m ppi_scout.offline doctor >/dev/null || fail "离线自检失败。"
if [[ "${PPI_SCOUT_SELF_TEST:-0}" == "1" ]]; then
  print "离线包自检完成：运行时、模型、断网入口均已就绪。"
  exit 0
fi

print "[4/4] 开始或续跑本地 Boltz 面板。可保持断网。"
mkdir -p "$RESULT_ROOT"
BOLTZ_CACHE="$CACHE_ROOT" \
  "$PYTHON" -m ppi_scout.offline \
  --lang zh-CN \
  run-panel "$JOB" \
  --windows 24 \
  --design-seed 7 \
  --msa-library "$MSA_LIBRARY" \
  --output-dir "$RESULT_ROOT" \
  --live 2>&1 | tee "$RESULT_ROOT/launcher.log"

REPORT="$RESULT_ROOT/report.html"
[[ -f "$REPORT" ]] || fail "计算结束，但没有找到本地结果页。请查看 launcher.log。"
open "$REPORT"
print "\n完成：$REPORT"
print "按回车关闭。"
read -r
