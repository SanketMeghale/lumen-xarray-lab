$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
panel serve "$root\examples\dashboard_app.py" --show --allow-websocket-origin "localhost:5006" --allow-websocket-origin "127.0.0.1:5006"
