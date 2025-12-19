# ============================================================
# VIRTUS - Iniciar Todos os Serviços
# ============================================================
# Este script inicia os 3 serviços separadamente:
# 1. Brain API (porta 8001) - Trading Engine
# 2. Dashboard Backend (porta 8000) - API do Dashboard
# 3. Dashboard Frontend (porta 5173) - Interface Web
# ============================================================

param(
    [switch]$BrainOnly,      # Inicia apenas o Brain
    [switch]$DashboardOnly,  # Inicia apenas Dashboard (Backend + Frontend)
    [switch]$All             # Inicia tudo (padrão)
)

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         VIRTUS - Sistema de Trading Automatizado           " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Função para verificar se porta está em uso
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
            Write-Host "  Processo na porta $Port finalizado" -ForegroundColor Yellow
        }
    }
}

# Mata processos anteriores
Write-Host "🧹 Limpando processos anteriores..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Stop-ProcessOnPort 8000
Stop-ProcessOnPort 8001
Stop-ProcessOnPort 5173
Start-Sleep -Seconds 2
Write-Host ""

# Define o que iniciar
$startBrain = $All -or $BrainOnly -or (-not $BrainOnly -and -not $DashboardOnly)
$startDashboard = $All -or $DashboardOnly -or (-not $BrainOnly -and -not $DashboardOnly)

# ==================== BRAIN API ====================
if ($startBrain) {
    Write-Host "🧠 Iniciando Brain API (porta 8001)..." -ForegroundColor Green
    
    $brainPath = Join-Path $ROOT "brain"
    $pythonPath = Join-Path $ROOT "env\Scripts\python.exe"
    
    if (-not (Test-Path $pythonPath)) {
        Write-Host "  ❌ Python não encontrado em: $pythonPath" -ForegroundColor Red
        exit 1
    }
    
    # Inicia Brain API em nova janela
    Start-Process -FilePath $pythonPath `
        -ArgumentList "brain_api.py" `
        -WorkingDirectory $brainPath `
        -WindowStyle Normal
    
    Write-Host "  ✅ Brain API iniciado" -ForegroundColor Green
    Start-Sleep -Seconds 3
}

# ==================== DASHBOARD BACKEND ====================
if ($startDashboard) {
    Write-Host "🖥️  Iniciando Dashboard Backend (porta 8000)..." -ForegroundColor Green
    
    $backendPath = Join-Path $ROOT "brain\dashboard\backend"
    $pythonPath = Join-Path $ROOT "env\Scripts\python.exe"
    
    # Inicia Backend em nova janela
    Start-Process -FilePath $pythonPath `
        -ArgumentList "run_server.py" `
        -WorkingDirectory $backendPath `
        -WindowStyle Normal
    
    Write-Host "  ✅ Dashboard Backend iniciado" -ForegroundColor Green
    Start-Sleep -Seconds 2
    
    # ==================== DASHBOARD FRONTEND ====================
    Write-Host "🌐 Iniciando Dashboard Frontend (porta 5173)..." -ForegroundColor Green
    
    $frontendPath = Join-Path $ROOT "brain\dashboard\frontend"
    
    # Verifica se npm está disponível
    $npmPath = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npmPath) {
        Write-Host "  ❌ npm não encontrado. Instale Node.js" -ForegroundColor Red
        exit 1
    }
    
    # Inicia Frontend em nova janela
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c npm run dev" `
        -WorkingDirectory $frontendPath `
        -WindowStyle Normal
    
    Write-Host "  ✅ Dashboard Frontend iniciado" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "                    SERVIÇOS INICIADOS                       " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ($startBrain) {
    Write-Host "  🧠 Brain API:         http://localhost:8001" -ForegroundColor White
    Write-Host "     - Docs:            http://localhost:8001/docs" -ForegroundColor DarkGray
}

if ($startDashboard) {
    Write-Host "  🖥️  Dashboard Backend: http://localhost:8000" -ForegroundColor White
    Write-Host "     - Docs:            http://localhost:8000/docs" -ForegroundColor DarkGray
    Write-Host "  🌐 Dashboard Web:     http://localhost:5173" -ForegroundColor White
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Pressione Ctrl+C para parar este script" -ForegroundColor Yellow
Write-Host "  (Os serviços continuarão rodando em suas janelas)" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Aguarda
Write-Host "📊 Monitorando serviços... (Ctrl+C para sair)" -ForegroundColor Cyan
while ($true) {
    Start-Sleep -Seconds 30
    
    # Verifica status
    $brainOk = Test-Port 8001
    $backendOk = Test-Port 8000
    $frontendOk = Test-Port 5173
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $status = "[$timestamp] Status: "
    
    if ($startBrain) {
        $status += if ($brainOk) { "Brain ✅ " } else { "Brain ❌ " }
    }
    if ($startDashboard) {
        $status += if ($backendOk) { "Backend ✅ " } else { "Backend ❌ " }
        $status += if ($frontendOk) { "Frontend ✅" } else { "Frontend ❌" }
    }
    
    Write-Host $status -ForegroundColor Gray
}
