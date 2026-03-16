$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
panel serve "$root\examples\dashboard_app.py" --show
