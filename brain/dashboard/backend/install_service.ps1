# VIRTUS Dashboard - Script de Instalação do Serviço Windows
# ============================================================
# Execute como Administrador

param(
    [Parameter()]
    [ValidateSet('install', 'uninstall', 'start', 'stop', 'restart', 'status')]
    [string]$Action = 'install'
)

$ErrorActionPreference = "Stop"

# Configurações
$ServiceName = "VirtusDashboard"
$ServiceDisplayName = "VIRTUS Dashboard Backend"
$ServiceDescription = "Serviço de backend para o Dashboard VIRTUS com notícias em áudio"
$BackendPath = "C:\Users\Administrator\Desktop\Virtus\brain\dashboard\backend"
$PythonPath = "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
$ScriptPath = "$BackendPath\windows_service.py"
$NssmPath = "$BackendPath\nssm.exe"
$NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
$LogPath = "C:\Users\Administrator\Desktop\Virtus\brain\data\logs"

# Funções auxiliares
function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $color = switch ($Type) {
        "Success" { "Green" }
        "Error" { "Red" }
        "Warning" { "Yellow" }
        default { "Cyan" }
    }
    Write-Host "[$Type] $Message" -ForegroundColor $color
}

function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-NSSM {
    if (Test-Path $NssmPath) {
        Write-Status "NSSM já existe" "Success"
        return $true
    }
    
    Write-Status "Baixando NSSM..."
    $zipPath = "$env:TEMP\nssm.zip"
    
    try {
        Invoke-WebRequest -Uri $NssmUrl -OutFile $zipPath
        Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\nssm" -Force
        Copy-Item "$env:TEMP\nssm\nssm-2.24\win64\nssm.exe" $NssmPath
        Remove-Item $zipPath -Force
        Remove-Item "$env:TEMP\nssm" -Recurse -Force
        Write-Status "NSSM instalado com sucesso" "Success"
        return $true
    }
    catch {
        Write-Status "Erro ao baixar NSSM: $_" "Error"
        return $false
    }
}

function Install-Service {
    Write-Status "Instalando serviço $ServiceName..."
    
    # Verifica se já existe
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Status "Serviço já existe. Removendo..." "Warning"
        Uninstall-Service
    }
    
    # Garante que NSSM existe
    if (-not (Get-NSSM)) {
        Write-Status "Não foi possível obter NSSM" "Error"
        return
    }
    
    # Cria diretório de logs
    if (-not (Test-Path $LogPath)) {
        New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
    }
    
    # Instala o serviço usando NSSM
    & $NssmPath install $ServiceName $PythonPath $ScriptPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Status "Erro ao instalar serviço" "Error"
        return
    }
    
    # Configurações do serviço
    & $NssmPath set $ServiceName DisplayName $ServiceDisplayName
    & $NssmPath set $ServiceName Description $ServiceDescription
    & $NssmPath set $ServiceName AppDirectory $BackendPath
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START
    
    # Configuração de restart automático
    & $NssmPath set $ServiceName AppExit Default Restart
    & $NssmPath set $ServiceName AppRestartDelay 5000
    & $NssmPath set $ServiceName AppThrottle 10000
    
    # Logs
    & $NssmPath set $ServiceName AppStdout "$LogPath\dashboard_stdout.log"
    & $NssmPath set $ServiceName AppStderr "$LogPath\dashboard_stderr.log"
    & $NssmPath set $ServiceName AppStdoutCreationDisposition 4
    & $NssmPath set $ServiceName AppStderrCreationDisposition 4
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateBytes 10485760
    
    Write-Status "Serviço instalado com sucesso!" "Success"
    Write-Status "Use: .\install_service.ps1 -Action start" "Info"
}

function Uninstall-Service {
    Write-Status "Removendo serviço $ServiceName..."
    
    # Para o serviço primeiro
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    
    if (Test-Path $NssmPath) {
        & $NssmPath remove $ServiceName confirm
    }
    else {
        sc.exe delete $ServiceName
    }
    
    Write-Status "Serviço removido" "Success"
}

function Start-DashboardService {
    Write-Status "Iniciando serviço $ServiceName..."
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    $service = Get-Service -Name $ServiceName
    if ($service.Status -eq "Running") {
        Write-Status "Serviço iniciado com sucesso!" "Success"
    }
    else {
        Write-Status "Falha ao iniciar serviço" "Error"
    }
}

function Stop-DashboardService {
    Write-Status "Parando serviço $ServiceName..."
    Stop-Service -Name $ServiceName -Force
    Write-Status "Serviço parado" "Success"
}

function Restart-DashboardService {
    Stop-DashboardService
    Start-Sleep -Seconds 2
    Start-DashboardService
}

function Get-ServiceStatus {
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    
    if ($service) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  VIRTUS Dashboard Service Status" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Nome:        $($service.Name)" -ForegroundColor White
        Write-Host "  Display:     $($service.DisplayName)" -ForegroundColor White
        Write-Host "  Status:      $($service.Status)" -ForegroundColor $(if ($service.Status -eq "Running") { "Green" } else { "Red" })
        Write-Host "  Start Type:  $($service.StartType)" -ForegroundColor White
        Write-Host ""
        
        # Mostra últimas linhas do log
        $logFile = "$LogPath\dashboard_service.log"
        if (Test-Path $logFile) {
            Write-Host "  Últimas entradas do log:" -ForegroundColor Yellow
            Get-Content $logFile -Tail 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
    }
    else {
        Write-Status "Serviço não encontrado" "Warning"
    }
}

# Verifica privilégios de administrador
if (-not (Test-Admin)) {
    Write-Status "Este script precisa ser executado como Administrador!" "Error"
    Write-Host "Clique com o botão direito no PowerShell e selecione 'Executar como administrador'"
    exit 1
}

# Executa a ação solicitada
switch ($Action) {
    'install' { Install-Service }
    'uninstall' { Uninstall-Service }
    'start' { Start-DashboardService }
    'stop' { Stop-DashboardService }
    'restart' { Restart-DashboardService }
    'status' { Get-ServiceStatus }
}
