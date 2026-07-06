@echo off
REM ============================================================================
REM Atlas Agent Installer for Windows (CMD wrapper)
REM ============================================================================
REM This batch file launches the PowerShell installer for users running CMD.
REM
REM Usage:
REM   git clone https://github.com/theusamaaslam/AtlasAgent.git
REM   cd AtlasAgent
REM   scripts\install.cmd
REM
REM Or if you're already in PowerShell, use the direct command instead:
REM   powershell -ExecutionPolicy ByPass -File .\scripts\install.ps1
REM ============================================================================

echo.
echo  Atlas Agent Installer
echo  Launching PowerShell installer...
echo.

powershell -ExecutionPolicy ByPass -NoProfile -File "%~dp0install.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  Installation failed. Please try running PowerShell directly:
    echo    powershell -ExecutionPolicy ByPass -File "%~dp0install.ps1"
    echo.
    pause
    exit /b 1
)
