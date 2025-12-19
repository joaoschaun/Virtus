# ============================================================
# VIRTUS - Iniciar Trading Bot
# ============================================================
# Inicia APENAS o bot de trading (main.py + brain_api.py)
# Dashboard roda separadamente
# ============================================================

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "              VIRTUS Trading Bot                             " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$pythonPath = Join-Path $ROOT "env\Scripts\python.exe"
$brainPath = Join-Path $ROOT "brain"

# Verifica Python
if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ Python não encontrado em: $pythonPath" -ForegroundColor Red
    exit 1
}

# Mata processos Python anteriores
Write-Host "🧹 Parando processos anteriores..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Inicia Brain API (para o dashboard consultar)
Write-Host "🧠 Iniciando Brain API (porta 8001)..." -ForegroundColor Green
Start-Process -FilePath $pythonPath `
    -ArgumentList "brain_api.py" `
    -WorkingDirectory $brainPath `
    -WindowStyle Minimized

Start-Sleep -Seconds 3

# Inicia Trading Bot principal
Write-Host "🤖 Iniciando Trading Bot..." -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Set-Location $brainPath
& $pythonPath main.py
