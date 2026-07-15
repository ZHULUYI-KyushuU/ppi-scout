@echo off
setlocal
chcp 65001 >nul
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows-wsl2-x64\install-and-run.ps1" -BundleRoot "%~dp0"
if errorlevel 1 (
  echo.
  echo PPI Scout did not finish successfully. See the message above.
  pause
  exit /b 1
)
endlocal
