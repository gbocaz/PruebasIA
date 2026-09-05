# Ejecutar como administrador después de configurar el recolector.
$ErrorActionPreference = "Stop"
$dest = "C:\Program Files\TICControl"
$config = "$env:ProgramData\TICControl\network-collector.json"

New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $config) | Out-Null

if (-not (Test-Path "$dest\tic-network-collector.exe")) {
    Write-Error "Copie tic-network-collector.exe a $dest."
}
if (-not (Test-Path $config)) {
    Write-Error "Configure primero el recolector. Falta $config."
}

& "$dest\tic-network-collector.exe" install-service
Start-Service TICControlNetworkCollector
Get-Service TICControlNetworkCollector
