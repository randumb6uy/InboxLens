# IndexLens One-Click Full-Stack Launcher (PowerShell)
param (
    [switch]$NoBrowser
)

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "         IndexLens — Starting Full-Stack Agent       " -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Cyan

# Locate Python in virtualenv or PATH
$pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$browserArg = ""
if ($NoBrowser) {
    $browserArg = "--no-browser"
}

& $pythonExe -m src.cli launch $browserArg
