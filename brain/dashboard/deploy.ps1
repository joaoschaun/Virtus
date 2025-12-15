# ============================================================================
# VIRTUS Dashboard - Script de Deploy Completo
# ============================================================================
# Execute como Administrador
# ============================================================================

param(
    [Parameter()]
    [ValidateSet('full', 'backend', 'frontend', 'nginx', 'status', 'logs')]
    [string]$Deploy = 'full'
)

$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
$VirtusRoot = "C:\Users\Administrator\Desktop\Virtus\brain"
$BackendPath = "$VirtusRoot\dashboard\backend"
$FrontendPath = "$VirtusRoot\dashboard\frontend"
$NginxPath = "C:\nginx"
$NginxConfSource = "$VirtusRoot\dashboard\nginx\nginx_windows.conf"
$LogPath = "$VirtusRoot\data\logs"
$PythonPath = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
$NpmPath = "npm"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
function Write-Banner {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $symbol = switch ($Type) {
        "Success" { "✓" }
        "Error"   { "✗" }
        "Warning" { "!" }
        default   { "→" }
    }
    $color = switch ($Type) {
        "Success" { "Green" }
        "Error"   { "Red" }
        "Warning" { "Yellow" }
        default   { "Cyan" }
    }
    Write-Host "  [$symbol] $Message" -ForegroundColor $color
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ============================================================================
# DEPLOY BACKEND
# ============================================================================
function Deploy-Backend {
    Write-Banner "DEPLOY: Backend FastAPI"
    
    # 1. Instala dependências Python
    Write-Status "Instalando dependências Python..."
    Set-Location $BackendPath
    & $PythonPath -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Dependências instaladas" "Success"
    } else {
        Write-Status "Erro ao instalar dependências" "Error"
        return $false
    }
    
    # 2. Instala o serviço Windows
    Write-Status "Configurando serviço Windows..."
    & PowerShell -ExecutionPolicy Bypass -File "$BackendPath\install_service.ps1" -Action install
    
    # 3. Inicia o serviço
    Write-Status "Iniciando serviço..."
    & PowerShell -ExecutionPolicy Bypass -File "$BackendPath\install_service.ps1" -Action start
    
    Start-Sleep -Seconds 3
    
    # 4. Verifica se está rodando
    $service = Get-Service -Name "VirtusDashboard" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq "Running") {
        Write-Status "Backend rodando com sucesso!" "Success"
        return $true
    } else {
        Write-Status "Backend pode não estar rodando" "Warning"
        return $false
    }
}

# ============================================================================
# DEPLOY FRONTEND
# ============================================================================
function Deploy-Frontend {
    Write-Banner "DEPLOY: Frontend React"
    
    Set-Location $FrontendPath
    
    # 1. Instala dependências
    Write-Status "Instalando dependências npm..."
    & $NpmPath install --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Erro ao instalar dependências npm" "Error"
        return $false
    }
    Write-Status "Dependências instaladas" "Success"
    
    # 2. Build de produção
    Write-Status "Gerando build de produção..."
    & $NpmPath run build
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Erro no build" "Error"
        return $false
    }
    
    # 3. Verifica se o build foi gerado
    if (Test-Path "$FrontendPath\dist\index.html") {
        Write-Status "Build gerado com sucesso!" "Success"
        $size = (Get-ChildItem "$FrontendPath\dist" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Status "Tamanho do build: $([math]::Round($size, 2)) MB" "Info"
        return $true
    } else {
        Write-Status "Build não encontrado" "Error"
        return $false
    }
}

# ============================================================================
# DEPLOY NGINX
# ============================================================================
function Deploy-Nginx {
    Write-Banner "DEPLOY: Nginx"
    
    # 1. Verifica se Nginx está instalado
    if (-not (Test-Path "$NginxPath\nginx.exe")) {
        Write-Status "Nginx não encontrado em $NginxPath" "Warning"
        Write-Status "Baixe em: https://nginx.org/en/download.html" "Info"
        Write-Status "Extraia para C:\nginx\" "Info"
        return $false
    }
    Write-Status "Nginx encontrado" "Success"
    
    # 2. Copia configuração
    Write-Status "Copiando configuração..."
    Copy-Item $NginxConfSource "$NginxPath\conf\nginx.conf" -Force
    Write-Status "Configuração copiada" "Success"
    
    # 3. Testa configuração
    Write-Status "Testando configuração..."
    Set-Location $NginxPath
    $testResult = & .\nginx.exe -t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Configuração válida" "Success"
    } else {
        Write-Status "Erro na configuração: $testResult" "Error"
        return $false
    }
    
    # 4. Para Nginx existente
    Get-Process nginx -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 1
    
    # 5. Inicia Nginx
    Write-Status "Iniciando Nginx..."
    Start-Process -FilePath "$NginxPath\nginx.exe" -WorkingDirectory $NginxPath
    Start-Sleep -Seconds 2
    
    if (Get-Process nginx -ErrorAction SilentlyContinue) {
        Write-Status "Nginx rodando!" "Success"
        return $true
    } else {
        Write-Status "Nginx pode não ter iniciado" "Warning"
        return $false
    }
}

# ============================================================================
# INSTALL NGINX SERVICE
# ============================================================================
function Install-NginxService {
    Write-Banner "Instalando Nginx como Serviço Windows"
    
    $NssmPath = "$BackendPath\nssm.exe"
    
    if (-not (Test-Path $NssmPath)) {
        Write-Status "NSSM não encontrado" "Error"
        return $false
    }
    
    # Remove serviço existente
    & $NssmPath remove NginxVirtus confirm 2>$null
    
    # Instala novo serviço
    & $NssmPath install NginxVirtus "$NginxPath\nginx.exe"
    & $NssmPath set NginxVirtus AppDirectory $NginxPath
    & $NssmPath set NginxVirtus DisplayName "VIRTUS Nginx Server"
    & $NssmPath set NginxVirtus Description "Servidor Nginx para o Dashboard VIRTUS"
    & $NssmPath set NginxVirtus Start SERVICE_AUTO_START
    & $NssmPath set NginxVirtus AppExit Default Restart
    
    Write-Status "Serviço Nginx instalado" "Success"
    
    # Inicia
    Start-Service -Name NginxVirtus
    Write-Status "Serviço Nginx iniciado" "Success"
    
    return $true
}

# ============================================================================
# STATUS
# ============================================================================
function Show-Status {
    Write-Banner "STATUS: VIRTUS Dashboard"
    
    # Backend
    $backendService = Get-Service -Name "VirtusDashboard" -ErrorAction SilentlyContinue
    if ($backendService) {
        $color = if ($backendService.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host "  Backend Service: " -NoNewline
        Write-Host $backendService.Status -ForegroundColor $color
    } else {
        Write-Host "  Backend Service: " -NoNewline
        Write-Host "Não instalado" -ForegroundColor Yellow
    }
    
    # Nginx
    $nginxService = Get-Service -Name "NginxVirtus" -ErrorAction SilentlyContinue
    if ($nginxService) {
        $color = if ($nginxService.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host "  Nginx Service:   " -NoNewline
        Write-Host $nginxService.Status -ForegroundColor $color
    } else {
        $nginxProcess = Get-Process nginx -ErrorAction SilentlyContinue
        if ($nginxProcess) {
            Write-Host "  Nginx Process:   " -NoNewline
            Write-Host "Running" -ForegroundColor Green
        } else {
            Write-Host "  Nginx:           " -NoNewline
            Write-Host "Não rodando" -ForegroundColor Yellow
        }
    }
    
    # Porta 8000
    $port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    Write-Host "  Porta 8000:      " -NoNewline
    if ($port8000) {
        Write-Host "Em uso" -ForegroundColor Green
    } else {
        Write-Host "Livre" -ForegroundColor Yellow
    }
    
    # Porta 80
    $port80 = Get-NetTCPConnection -LocalPort 80 -ErrorAction SilentlyContinue
    Write-Host "  Porta 80:        " -NoNewline
    if ($port80) {
        Write-Host "Em uso" -ForegroundColor Green
    } else {
        Write-Host "Livre" -ForegroundColor Yellow
    }
    
    # Frontend build
    Write-Host "  Frontend Build:  " -NoNewline
    if (Test-Path "$FrontendPath\dist\index.html") {
        $buildTime = (Get-Item "$FrontendPath\dist\index.html").LastWriteTime
        Write-Host "OK ($buildTime)" -ForegroundColor Green
    } else {
        Write-Host "Não existe" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================================
# LOGS
# ============================================================================
function Show-Logs {
    Write-Banner "LOGS: VIRTUS Dashboard"
    
    $logFiles = @(
        "$LogPath\dashboard_service.log",
        "$LogPath\dashboard_stdout.log",
        "$NginxPath\logs\dashboard_access.log",
        "$NginxPath\logs\dashboard_error.log"
    )
    
    foreach ($log in $logFiles) {
        if (Test-Path $log) {
            Write-Host "`n=== $log ===" -ForegroundColor Yellow
            Get-Content $log -Tail 10 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
        }
    }
}

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

# Verifica admin
if (-not (Test-Admin)) {
    Write-Host "ERRO: Execute como Administrador!" -ForegroundColor Red
    exit 1
}

# Cria diretório de logs
if (-not (Test-Path $LogPath)) {
    New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
}

# Executa ação
switch ($Deploy) {
    'full' {
        Write-Banner "DEPLOY COMPLETO - VIRTUS Dashboard"
        Write-Host "  Subdomínio: dashboard.virtusinvestimentos.com.br" -ForegroundColor Yellow
        Write-Host ""
        
        $backendOk = Deploy-Backend
        $frontendOk = Deploy-Frontend
        $nginxOk = Deploy-Nginx
        
        if ($backendOk -and $frontendOk -and $nginxOk) {
            Install-NginxService
        }
        
        Write-Host ""
        Show-Status
        
        Write-Banner "PRÓXIMOS PASSOS - Cloudflare"
        Write-Host "  1. Acesse o Cloudflare: https://dash.cloudflare.com" -ForegroundColor White
        Write-Host "  2. Selecione o domínio: virtusinvestimentos.com.br" -ForegroundColor White
        Write-Host "  3. Vá em DNS > Add Record" -ForegroundColor White
        Write-Host "  4. Configure:" -ForegroundColor White
        Write-Host "     Tipo: A" -ForegroundColor Yellow
        Write-Host "     Nome: dashboard" -ForegroundColor Yellow
        Write-Host "     IPv4: [SEU IP PÚBLICO]" -ForegroundColor Yellow
        Write-Host "     Proxy: ON (nuvem laranja)" -ForegroundColor Yellow
        Write-Host "  5. Em SSL/TLS > Overview:" -ForegroundColor White
        Write-Host "     Modo: Flexible" -ForegroundColor Yellow
        Write-Host ""
    }
    'backend' { Deploy-Backend }
    'frontend' { Deploy-Frontend }
    'nginx' { Deploy-Nginx; Install-NginxService }
    'status' { Show-Status }
    'logs' { Show-Logs }
}

Write-Host ""
