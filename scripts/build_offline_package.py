#!/usr/bin/env python3
"""Build verified local or GitHub Release packages from a complete offline bundle."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile


DEFAULT_CHUNK_SIZE = 1_900_000_000


@dataclass(frozen=True)
class Part:
    target: str
    asset: str
    part_sha256: str
    final_sha256: str
    index: int
    total: int

    def tsv(self) -> str:
        return "\t".join(
            (
                self.target,
                self.asset,
                self.part_sha256,
                self.final_sha256,
                str(self.index),
                str(self.total),
            )
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_asset(source: Path, target: str, output: Path, chunk_size: int) -> list[Part]:
    final_digest = sha256(source)
    count = max(1, (source.stat().st_size + chunk_size - 1) // chunk_size)
    safe_name = target.replace("/", "-").replace("_", "-").lstrip(".")
    parts: list[Part] = []
    with source.open("rb") as reader:
        for index in range(count):
            asset_name = f"{safe_name}.part-{index:03d}"
            destination = output / asset_name
            remaining = chunk_size
            with destination.open("wb") as writer:
                while remaining:
                    block = reader.read(min(8 * 1024 * 1024, remaining))
                    if not block:
                        break
                    writer.write(block)
                    remaining -= len(block)
            parts.append(
                Part(
                    target=target,
                    asset=asset_name,
                    part_sha256=sha256(destination),
                    final_sha256=final_digest,
                    index=index,
                    total=count,
                )
            )
    return parts


def build_common_archive(bundle: Path, destination: Path, *, windows_only: bool = False) -> None:
    required = [
        "Run-PPI-Scout-Windows.cmd",
        "README.md",
        "BUNDLE-SHA256SUMS",
        "BUNDLE-SOURCES.txt",
        "jobs",
        "msas",
        "models/SHA256SUMS",
        "windows-wsl2-x64/install-and-run.ps1",
        "windows-wsl2-x64/install-and-run.sh",
    ]
    if not windows_only:
        required.insert(0, "Run-PPI-Scout-macOS.command")
    with tarfile.open(destination, "w:gz") as archive:
        for relative in required:
            source = bundle / relative
            if not source.exists():
                raise FileNotFoundError(f"Bundle is missing required common path: {source}")
            archive.add(source, arcname=relative, recursive=True)
        results = tarfile.TarInfo("results")
        results.type = tarfile.DIRTYPE
        results.mode = 0o755
        archive.addfile(results)


def macos_installer(manifest: str, owner: str, repo: str, tag: str) -> str:
    return f'''#!/bin/zsh
set -euo pipefail
DEST="${{PPI_SCOUT_BUNDLE_DIR:-$HOME/PPI-Scout-Offline}}"
DOWNLOADS="$DEST/.downloads"
BASE="https://github.com/{owner}/{repo}/releases/download/{tag}"
mkdir -p "$DEST" "$DOWNLOADS"
print "正在从 GitHub Release 准备一次性离线包……"
while IFS=$'\\t' read -r target asset part_sha final_sha index total; do
  [[ -n "$target" ]] || continue
  part="$DOWNLOADS/$asset"
  if [[ ! -f "$part" ]]; then
    curl -fL --retry 5 --progress-bar -o "$part.tmp" "$BASE/$asset"
    mv "$part.tmp" "$part"
  fi
  actual="$(shasum -a 256 "$part" | awk '{{print $1}}')"
  [[ "$actual" == "$part_sha" ]] || {{ print -u2 "分卷校验失败：$asset"; exit 1; }}
  output="$DEST/$target"
  mkdir -p "$(dirname "$output")"
  [[ "$index" != "0" ]] || : > "$output.tmp"
  cat "$part" >> "$output.tmp"
  if (( index + 1 == total )); then
    actual="$(shasum -a 256 "$output.tmp" | awk '{{print $1}}')"
    [[ "$actual" == "$final_sha" ]] || {{ print -u2 "整文件校验失败：$target"; exit 1; }}
    mv "$output.tmp" "$output"
  fi
done <<'PPI_ASSETS'
{manifest}
PPI_ASSETS
tar -xzf "$DEST/.bootstrap/common.tar.gz" -C "$DEST"
chmod +x "$DEST/Run-PPI-Scout-macOS.command" "$DEST/windows-wsl2-x64/install-and-run.sh"
rm -rf "$DEST/.bootstrap" "$DOWNLOADS"
print "离线包已完整校验。后续计算不访问网络。"
"$DEST/Run-PPI-Scout-macOS.command"
'''


def windows_installer_ps1(manifest: str, owner: str, repo: str, tag: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$Destination = if ($env:PPI_SCOUT_BUNDLE_DIR) {{ $env:PPI_SCOUT_BUNDLE_DIR }} else {{ Join-Path $HOME "PPI-Scout-Offline" }}
$Downloads = Join-Path $Destination ".downloads"
$Base = "https://github.com/{owner}/{repo}/releases/download/{tag}"
New-Item -ItemType Directory -Force -Path $Destination, $Downloads | Out-Null
$Rows = @'
target\tasset\tpart_sha256\tfinal_sha256\tindex\ttotal
{manifest}
'@ | ConvertFrom-Csv -Delimiter "`t"
Write-Host "正在从 GitHub Release 准备一次性离线包……"
foreach ($Group in ($Rows | Group-Object target)) {{
    $Target = Join-Path $Destination $Group.Name
    $Temporary = "$Target.tmp"
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    if (Test-Path $Temporary) {{ Remove-Item -Force $Temporary }}
    $Output = [System.IO.File]::Open($Temporary, [System.IO.FileMode]::CreateNew)
    try {{
        foreach ($Row in ($Group.Group | Sort-Object {{ [int]$_.index }})) {{
            $Part = Join-Path $Downloads $Row.asset
            if (-not (Test-Path $Part -PathType Leaf)) {{
                & curl.exe -fL --retry 5 --progress-bar -o "$Part.tmp" "$Base/$($Row.asset)"
                if ($LASTEXITCODE -ne 0) {{ throw "下载失败：$($Row.asset)" }}
                Move-Item -Force "$Part.tmp" $Part
            }}
            $PartHash = (Get-FileHash $Part -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($PartHash -ne $Row.part_sha256) {{ throw "分卷校验失败：$($Row.asset)" }}
            $Input = [System.IO.File]::OpenRead($Part)
            try {{ $Input.CopyTo($Output) }} finally {{ $Input.Dispose() }}
        }}
    }} finally {{ $Output.Dispose() }}
    $FinalHash = (Get-FileHash $Temporary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($FinalHash -ne $Group.Group[0].final_sha256) {{ throw "整文件校验失败：$($Group.Name)" }}
    Move-Item -Force $Temporary $Target
}}
& tar.exe -xzf (Join-Path $Destination ".bootstrap/common.tar.gz") -C $Destination
if ($LASTEXITCODE -ne 0) {{ throw "公共离线包解压失败" }}
Remove-Item -Recurse -Force (Join-Path $Destination ".bootstrap"), $Downloads
Write-Host "离线包已完整校验。后续计算不访问网络。" -ForegroundColor Green
& (Join-Path $Destination "Run-PPI-Scout-Windows.cmd")
'''


def windows_local_installer_ps1(manifest: str) -> str:
    return f'''$ErrorActionPreference = "Stop"
$Source = $PSScriptRoot
$Destination = if ($env:PPI_SCOUT_BUNDLE_DIR) {{ $env:PPI_SCOUT_BUNDLE_DIR }} else {{ Join-Path $HOME "PPI-Scout-Offline" }}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$Rows = @'
target\tasset\tpart_sha256\tfinal_sha256\tindex\ttotal
{manifest}
'@ | ConvertFrom-Csv -Delimiter "`t"

Write-Host "正在校验并拼合 Windows 完整离线包，请不要关闭窗口……"
foreach ($Group in ($Rows | Group-Object target)) {{
    $Target = Join-Path $Destination $Group.Name
    $Temporary = "$Target.tmp"
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    if (Test-Path $Temporary) {{ Remove-Item -Force $Temporary }}
    $Output = [System.IO.File]::Open($Temporary, [System.IO.FileMode]::CreateNew)
    try {{
        foreach ($Row in ($Group.Group | Sort-Object {{ [int]$_.index }})) {{
            $Part = Join-Path $Source $Row.asset
            if (-not (Test-Path $Part -PathType Leaf)) {{ throw "缺少离线分卷：$($Row.asset)" }}
            $PartHash = (Get-FileHash $Part -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($PartHash -ne $Row.part_sha256) {{ throw "分卷损坏或未下载完整：$($Row.asset)" }}
            $Input = [System.IO.File]::OpenRead($Part)
            try {{ $Input.CopyTo($Output) }} finally {{ $Input.Dispose() }}
        }}
    }} finally {{ $Output.Dispose() }}
    $FinalHash = (Get-FileHash $Temporary -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($FinalHash -ne $Group.Group[0].final_sha256) {{ throw "拼合后的文件校验失败：$($Group.Name)" }}
    Move-Item -Force $Temporary $Target
}}

& tar.exe -xzf (Join-Path $Destination ".bootstrap/common.tar.gz") -C $Destination
if ($LASTEXITCODE -ne 0) {{ throw "公共离线包解压失败" }}
Remove-Item -Recurse -Force (Join-Path $Destination ".bootstrap")
Write-Host "离线包已完整校验；从这里开始，PPI Scout 计算不会访问网络。" -ForegroundColor Green
& (Join-Path $Destination "Run-PPI-Scout-Windows.cmd")
'''


def write_windows_local_setup(output: Path, parts: list[Part], tag: str) -> None:
    manifest = "\n".join(part.tsv() for part in parts)
    (output / "setup.ps1").write_text(
        windows_local_installer_ps1(manifest),
        encoding="utf-8-sig",
    )
    command = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass "
        "-File \"%~dp0setup.ps1\"\r\n"
        "if errorlevel 1 (\r\n"
        "  echo.\r\n"
        "  echo 安装或运行失败，请截图保留上面的红色错误信息。\r\n"
        "  pause\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
    )
    (output / "双击这里安装并运行.cmd").write_text(command, encoding="utf-8")
    (output / "Install-and-Run-PPI-Scout.cmd").write_text(command, encoding="utf-8")
    (output / "README-FIRST-请先看.txt").write_text(
        f"""PPI Scout Windows 完整离线包（{tag}）

最简单的用法：
1. 必须先把 GitHub 下载得到的 ZIP 完整解压，不能直接在 ZIP 里面运行。
2. 打开解压后的文件夹。
3. 双击“ 双击这里安装并运行.cmd ”。
4. 第一次会校验和拼合所有分卷，文件很大，请耐心等待。

电脑要求：
- 64 位 Windows 10 或 Windows 11。
- 已启用 WSL2；不需要通过 Microsoft Store 下载 Ubuntu。
- 建议至少预留 40 GB 可用磁盘空间。
- NVIDIA 显卡需要事先安装支持 WSL2 的 Windows 驱动；没有可用 CUDA 时会自动使用较慢的 CPU。

离线说明：
- 这个文件夹已经包含 PPI Scout、Python、Boltz、Ubuntu WSL 镜像和模型权重。
- ZIP 下载完整并且 WSL2/显卡驱动已提前配置好后，预测过程可以断网运行。
- 不要删除任何 .part-000、.part-001 等分卷文件。

如果中文文件名无法双击，也可以运行 Install-and-Run-PPI-Scout.cmd。
""",
        encoding="utf-8-sig",
    )


def write_setup_zips(
    output: Path,
    mac_parts: list[Part],
    windows_parts: list[Part],
    owner: str,
    repo: str,
    tag: str,
) -> None:
    mac_manifest = "\n".join(part.tsv() for part in mac_parts)
    windows_manifest = "\n".join(part.tsv() for part in windows_parts)
    with tempfile.TemporaryDirectory() as tmp_value:
        tmp = Path(tmp_value)
        mac_script = tmp / "Online-Setup-and-Run-macOS.command"
        mac_script.write_text(macos_installer(mac_manifest, owner, repo, tag), encoding="utf-8")
        mac_script.chmod(0o755)
        with zipfile.ZipFile(output / "PPI-Scout-Online-Setup-macOS.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(mac_script, mac_script.name)

        windows_ps1 = tmp / "setup.ps1"
        windows_ps1.write_text(
            windows_installer_ps1(windows_manifest, owner, repo, tag),
            encoding="utf-8-sig",
        )
        windows_cmd = tmp / "Online-Setup-and-Run-Windows.cmd"
        windows_cmd.write_text(
            '@echo off\r\nchcp 65001 >nul\r\npowershell.exe -NoLogo -NoProfile '
            '-ExecutionPolicy Bypass -File "%~dp0setup.ps1"\r\nif errorlevel 1 pause\r\n',
            encoding="utf-8",
        )
        with zipfile.ZipFile(output / "PPI-Scout-Online-Setup-Windows.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(windows_cmd, windows_cmd.name)
            archive.write(windows_ps1, windows_ps1.name)


def write_windows_online_setup(
    output: Path,
    parts: list[Part],
    owner: str,
    repo: str,
    tag: str,
) -> Path:
    """Write the small first-download ZIP used by the Windows release."""
    manifest = "\n".join(part.tsv() for part in parts)
    safe_tag = tag.replace("/", "-")
    destination = output / f"PPI-Scout-Windows-Installer-{safe_tag}.zip"
    with tempfile.TemporaryDirectory() as tmp_value:
        tmp = Path(tmp_value)
        setup = tmp / "setup.ps1"
        setup.write_text(
            windows_installer_ps1(manifest, owner, repo, tag),
            encoding="utf-8-sig",
        )
        command = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass "
            "-File \"%~dp0setup.ps1\"\r\n"
            "if errorlevel 1 (\r\n"
            "  echo.\r\n"
            "  echo 下载、安装或运行失败，请截图保留上面的红色错误信息。\r\n"
            "  pause\r\n"
            "  exit /b 1\r\n"
            ")\r\n"
        )
        chinese_command = tmp / "双击这里下载并安装.cmd"
        english_command = tmp / "Download-Install-and-Run.cmd"
        chinese_command.write_text(command, encoding="utf-8")
        english_command.write_text(command, encoding="utf-8")
        readme = tmp / "README-FIRST-请先看.txt"
        readme.write_text(
            f"""PPI Scout Windows 安装器（{tag}）

1. 第一次使用必须联网，预计下载约 10.4 GB。
2. 双击“ 双击这里下载并安装.cmd ”。
3. 程序会自动下载、校验并安装完整离线包，请不要关闭窗口。
4. 安装完成后，实际预测可以断网运行。

需要 64 位 Windows 10/11、已启用的 WSL2，以及至少 40 GB 可用空间。
如果中文文件名无法双击，请运行 Download-Install-and-Run.cmd。
""",
            encoding="utf-8-sig",
        )
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in (chinese_command, english_command, setup, readme):
                archive.write(path, path.name)
    return destination


def prepare(args: argparse.Namespace) -> None:
    bundle = args.bundle.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    common = output / "ppi-scout-offline-common.tar.gz"
    build_common_archive(bundle, common)
    common_parts = split_asset(common, ".bootstrap/common.tar.gz", output, args.chunk_size)
    common.unlink()

    model_targets = (
        "models/mols.tar",
        "models/boltz2_conf.ckpt",
        "models/boltz2_aff.ckpt",
    )
    model_parts = [
        part
        for target in model_targets
        for part in split_asset(bundle / target, target, output, args.chunk_size)
    ]
    mac_target = "macos-arm64/ppi-scout-runtime-macos-arm64.tar.gz"
    windows_targets = (
        "windows-wsl2-x64/ppi-scout-runtime-linux-x86_64.tar.gz",
        "windows-wsl2-x64/ubuntu-rootfs.tar.gz",
    )
    mac_parts = split_asset(bundle / mac_target, mac_target, output, args.chunk_size)
    windows_parts = [
        part
        for target in windows_targets
        for part in split_asset(bundle / target, target, output, args.chunk_size)
    ]
    write_setup_zips(
        output,
        common_parts + model_parts + mac_parts,
        common_parts + model_parts + windows_parts,
        args.owner,
        args.repo,
        args.tag,
    )
    (output / "release-assets.sha256").write_text(
        "".join(
            f"{sha256(path)}  {path.name}\n"
            for path in sorted(output.iterdir())
            if path.is_file() and path.name != "release-assets.sha256"
        ),
        encoding="utf-8",
    )


def prepare_windows_artifact(
    bundle: Path,
    output: Path,
    tag: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    remove_payloads: bool = False,
    owner: str = "ZHULUYI-KyushuU",
    repo: str = "ppi-scout",
) -> None:
    bundle = bundle.expanduser().resolve()
    output = output.expanduser().resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    common = output / "ppi-scout-offline-common.tar.gz"
    build_common_archive(bundle, common, windows_only=True)
    common_parts = split_asset(common, ".bootstrap/common.tar.gz", output, chunk_size)
    common.unlink()

    targets = (
        "models/mols.tar",
        "models/boltz2_conf.ckpt",
        "models/boltz2_aff.ckpt",
        "windows-wsl2-x64/ppi-scout-runtime-linux-x86_64.tar.gz",
        "windows-wsl2-x64/ubuntu-rootfs.tar.gz",
    )
    payload_parts: list[Part] = []
    for target in targets:
        source = bundle / target
        payload_parts.extend(split_asset(source, target, output, chunk_size))
        if remove_payloads:
            source.unlink()
    parts = common_parts + payload_parts
    write_windows_local_setup(output, parts, tag)
    write_windows_online_setup(output, parts, owner, repo, tag)
    (output / "artifact-files.sha256").write_text(
        "".join(
            f"{sha256(path)}  {path.name}\n"
            for path in sorted(output.iterdir())
            if path.is_file() and path.name != "artifact-files.sha256"
        ),
        encoding="utf-8",
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--bundle", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--tag", required=True)
    result.add_argument("--owner", default="ZHULUYI-KyushuU")
    result.add_argument("--repo", default="ppi-scout")
    result.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    result.add_argument(
        "--windows-local",
        action="store_true",
        help="Write a self-contained Windows Actions artifact that joins local parts.",
    )
    result.add_argument(
        "--remove-payloads-after-split",
        action="store_true",
        help="Save CI disk space by deleting assembled payloads after splitting them.",
    )
    return result


if __name__ == "__main__":
    arguments = parser().parse_args()
    if arguments.windows_local:
        prepare_windows_artifact(
            arguments.bundle,
            arguments.output,
            arguments.tag,
            arguments.chunk_size,
            arguments.remove_payloads_after_split,
            arguments.owner,
            arguments.repo,
        )
    else:
        prepare(arguments)
