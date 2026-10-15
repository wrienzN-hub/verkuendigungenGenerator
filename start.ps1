# Startet die gebaute React-Oberfläche und API zusammen auf Port 8000.
param([ValidateRange(1, 65535)][int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv-api/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Bitte zuerst die Python-Umgebung einrichten. Siehe docs/frontend.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'frontend/dist/index.html'))) {
    throw 'Bitte zuerst das Frontend bauen: cd frontend; pnpm install; pnpm build. Siehe docs/frontend.md.'
}
Push-Location $PSScriptRoot
try {
    Write-Host "Verkuendigungen: http://127.0.0.1:$Port | Beenden mit Strg+C"
    & $projectPython -m uvicorn verkuendigungen.api.app:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Der Server konnte nicht gestartet werden. Ist der Port bereits belegt?' }
} finally {
    Pop-Location
}
