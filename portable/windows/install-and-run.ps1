param(
    [Parameter(Mandatory = $true)]
    [string]$BundleRoot
)

$ErrorActionPreference = "Stop"
$Distro = "PPI-Scout-Offline"
$InstallRoot = Join-Path $env:LOCALAPPDATA "PPI-Scout-Offline\wsl"
$RootFs = Join-Path $BundleRoot "windows-wsl2-x64\ubuntu-rootfs.tar.gz"
$Runner = Join-Path $BundleRoot "windows-wsl2-x64\install-and-run.sh"

function Fail([string]$Message) {
    Write-Host "错误：$Message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Fail "Windows 尚未启用 WSL2。请先在管理员终端启用 WSL2；离线包本身不需要 Microsoft Store。"
}
if (-not (Test-Path $RootFs -PathType Leaf)) { Fail "缺少 Ubuntu WSL2 离线镜像：$RootFs" }
if (-not (Test-Path $Runner -PathType Leaf)) { Fail "缺少 Windows 离线运行脚本：$Runner" }

$Existing = @(wsl.exe --list --quiet 2>$null) | ForEach-Object { $_.Trim([char]0).Trim() }
if ($Existing -notcontains $Distro) {
    Write-Host "[1/3] 首次导入随包附带的 Ubuntu WSL2 环境……"
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    wsl.exe --import $Distro $InstallRoot $RootFs --version 2
    if ($LASTEXITCODE -ne 0) { Fail "WSL2 环境导入失败。请确认虚拟化与 WSL2 已启用。" }
} else {
    Write-Host "[1/3] PPI Scout WSL2 环境已就绪。"
}

Write-Host "[2/3] 转换本地离线包路径……"
$LinuxBundleRoot = (wsl.exe -d $Distro -u root -- wslpath -a $BundleRoot).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($LinuxBundleRoot)) {
    Fail "无法把 Windows 路径转换为 WSL2 路径。"
}

Write-Host "[3/3] 开始或续跑完全本地的 Boltz 面板……"
wsl.exe -d $Distro -u root -- bash "$LinuxBundleRoot/windows-wsl2-x64/install-and-run.sh" "$LinuxBundleRoot"
if ($LASTEXITCODE -ne 0) { Fail "本地预测未成功完成，请查看 results 目录中的 launcher.log。" }

$Report = Join-Path $BundleRoot "results\atg8-yta7-fdfl\report.html"
if (Test-Path $Report -PathType Leaf) {
    Start-Process $Report
    Write-Host "完成：$Report" -ForegroundColor Green
} else {
    Fail "计算结束，但没有找到本地结果页。"
}
