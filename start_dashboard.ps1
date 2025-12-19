# ============================================================
# VIRTUS - Iniciar Dashboard
# ============================================================
# Inicia APENAS o dashboard (Backend + Frontend)
# Trading Bot roda separadamente
# ============================================================

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "              VIRTUS Dashboard                               " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$pythonPath = Join-Path $ROOT "env\Scripts\python.exe"

# Função para verificar porta
function Test-Port {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return $null -ne $connection
}

# Função para matar processo em porta
function Stop-ProcessOnPort {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connection) {
        $pid = $connection.OwningProcess | Select-Object -First 1
        if ($pid) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}

# Libera portas
Write-Host "🧹 Liberando portas..." -ForegroundColor Yellow
Stop-ProcessOnPort 8000
Stop-ProcessOnPort 5173
Start-Sleep -Seconds 2

# Verifica se Brain API está rodando
$brainRunning = Test-Port 8001
if ($brainRunning) {
    Write-Host "✅ Brain API detectado na porta 8001" -ForegroundColor Green
} else {
    Write-Host "⚠️  Brain API não detectado (porta 8001)" -ForegroundColor Yellow
    Write-Host "   Dashboard funcionará com dados limitados" -ForegroundColor Yellow
}
Write-Host ""

# ==================== BACKEND ====================
Write-Host "🖥️  Iniciando Backend (porta 8000)..." -ForegroundColor Green

$backendPath = Join-Path $ROOT "brain\dashboard\backend"
Start-Process -FilePath $pythonPath `
    -ArgumentList "run_server.py" `
    -WorkingDirectory $backendPath `
    -WindowStyle Normal

Start-Sleep -Seconds 3

# Verifica se backend iniciou
if (Test-Port 8000) {
    Write-Host "  ✅ Backend rodando" -ForegroundColor Green
} else {
    Write-Host "  ❌ Backend falhou ao iniciar" -ForegroundColor Red
}

# ==================== FRONTEND ====================
Write-Host "🌐 Iniciando Frontend (porta 5173)..." -ForegroundColor Green

$frontendPath = Join-Path $ROOT "brain\dashboard\frontend"

# Verifica se node_modules existe
$nodeModules = Join-Path $frontendPath "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "  📦 Instalando dependências do frontend..." -ForegroundColor Yellow
    Set-Location $frontendPath
    npm install
}

# Inicia frontend
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c npm run dev" `
    -WorkingDirectory $frontendPath `
    -WindowStyle Normal

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "                 DASHBOARD INICIADO                          " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🖥️  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  📚 API Docs: http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "  🌐 Frontend: http://localhost:5173" -ForegroundColor White
Write-Host ""

if (-not $brainRunning) {
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "  ⚠️  Para dados de trading em tempo real, inicie o bot:    " -ForegroundColor Yellow
    Write-Host "      .\start_trading.ps1                                   " -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Pressione qualquer tecla para abrir o dashboard no navegador..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Abre navegador
Start-Process "http://localhost:5173"
