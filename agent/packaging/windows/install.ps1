# Ejecutar en PowerShell como administrador después de copiar tic-agent.exe
# a C:\Program Files\TICControl\tic-agent.exe

$ErrorActionPreference = "Stop"
$dest = "C:\Program Files\TICControl"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path "$env:ProgramData\TICControl" | Out-Null

if (-not (Test-Path "$dest\tic-agent.exe")) {
    Write-Error "Copie tic-agent.exe a $dest antes de instalar el servicio."
}

& "$dest\tic-agent.exe" install-service
Start-Service TICControlAgent
Get-Service TICControlAgent
