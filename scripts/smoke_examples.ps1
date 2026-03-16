$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
python "$root\examples\quickstart.py"
python "$root\examples\air_temperature_demo.py"
python "$root\examples\ai_upload_demo.py"
python "$root\examples\sql_explorer_demo.py"
