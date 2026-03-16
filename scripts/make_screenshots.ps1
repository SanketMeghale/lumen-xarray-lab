$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root\scripts\make_screenshots.py" @args
Write-Host ""
Write-Host "For browser screenshots install the optional tools if needed:"
Write-Host "  pip install -e .[demo]"
Write-Host "  python -m playwright install chromium"
