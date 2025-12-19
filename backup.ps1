# ============================================================================
# VIRTUS - Script de Backup Automático
# ============================================================================
# 
# Faz backup de:
# - Banco de dados SQLite
# - Configurações
# - Logs importantes
# - Estado dos bots
#
# Uso:
#   .\backup.ps1                    # Backup completo
#   .\backup.ps1 -Type db           # Apenas banco de dados
#   .\backup.ps1 -Type config       # Apenas configurações
#   .\backup.ps1 -Destination D:\   # Backup para destino específico
#
# ============================================================================

param(
    [ValidateSet("all", "db", "config", "logs", "state")]
    [string]$Type = "all",
    
    [string]$Destination = "",
    
    [int]$KeepDays = 30,
    
    [switch]$Compress = $true
)

# Cores
$colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
}

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $color = $colors[$Type]
    $prefix = switch($Type) {
        "Success" { "✅" }
        "Warning" { "⚠️" }
        "Error" { "❌" }
        default { "📋" }
    }
    Write-Host "$prefix $Message" -ForegroundColor $color
}

# Diretórios
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$brainDir = Join-Path $scriptDir "brain"
$dataDir = Join-Path $brainDir "data"
$configDir = Join-Path $brainDir "config"
$logsDir = Join-Path $dataDir "logs"

# Destino do backup
if ([string]::IsNullOrEmpty($Destination)) {
    $backupRoot = Join-Path $scriptDir "backups"
} else {
    $backupRoot = $Destination
}

# Cria pasta de backup com timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupDir = Join-Path $backupRoot "backup_$timestamp"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🗄️  VIRTUS - Backup Automático" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📅 Data: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"
Write-Host "📁 Destino: $backupDir"
Write-Host "📦 Tipo: $Type"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Cria estrutura de pastas
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# ============================================================================
# BACKUP DO BANCO DE DADOS
# ============================================================================
if ($Type -eq "all" -or $Type -eq "db") {
    Write-Status "Iniciando backup do banco de dados..."
    
    $dbFiles = @(
        (Join-Path $dataDir "brain" "virtus.db"),
        (Join-Path $dataDir "brain" "brain.db"),
        (Join-Path $dataDir "virtus.db")
    )
    
    $dbBackupDir = Join-Path $backupDir "database"
    New-Item -ItemType Directory -Path $dbBackupDir -Force | Out-Null
    
    $dbCount = 0
    foreach ($db in $dbFiles) {
        if (Test-Path $db) {
            $dbName = Split-Path -Leaf $db
            Copy-Item $db -Destination (Join-Path $dbBackupDir $dbName) -Force
            $size = (Get-Item $db).Length / 1MB
            Write-Status "  $dbName (${size:N2} MB)" -Type "Success"
            $dbCount++
        }
    }
    
    if ($dbCount -eq 0) {
        Write-Status "Nenhum banco de dados encontrado" -Type "Warning"
    } else {
        Write-Status "Backup de $dbCount banco(s) concluído" -Type "Success"
    }
    Write-Host ""
}

# ============================================================================
# BACKUP DAS CONFIGURAÇÕES
# ============================================================================
if ($Type -eq "all" -or $Type -eq "config") {
    Write-Status "Iniciando backup das configurações..."
    
    $configBackupDir = Join-Path $backupDir "config"
    
    if (Test-Path $configDir) {
        Copy-Item $configDir -Destination $configBackupDir -Recurse -Force
        $configCount = (Get-ChildItem $configBackupDir -Recurse -File).Count
        Write-Status "  $configCount arquivos de configuração" -Type "Success"
    } else {
        Write-Status "Pasta de configuração não encontrada" -Type "Warning"
    }
    Write-Host ""
}

# ============================================================================
# BACKUP DOS LOGS
# ============================================================================
if ($Type -eq "all" -or $Type -eq "logs") {
    Write-Status "Iniciando backup dos logs..."
    
    $logsBackupDir = Join-Path $backupDir "logs"
    New-Item -ItemType Directory -Path $logsBackupDir -Force | Out-Null
    
    if (Test-Path $logsDir) {
        # Copia apenas logs dos últimos 7 dias para economizar espaço
        $recentLogs = Get-ChildItem $logsDir -File | Where-Object {
            $_.LastWriteTime -gt (Get-Date).AddDays(-7)
        }
        
        foreach ($log in $recentLogs) {
            Copy-Item $log.FullName -Destination $logsBackupDir -Force
        }
        
        Write-Status "  $($recentLogs.Count) arquivos de log (últimos 7 dias)" -Type "Success"
    } else {
        Write-Status "Pasta de logs não encontrada" -Type "Warning"
    }
    Write-Host ""
}

# ============================================================================
# BACKUP DO ESTADO DOS BOTS
# ============================================================================
if ($Type -eq "all" -or $Type -eq "state") {
    Write-Status "Iniciando backup do estado..."
    
    $stateBackupDir = Join-Path $backupDir "state"
    New-Item -ItemType Directory -Path $stateBackupDir -Force | Out-Null
    
    $stateFiles = @(
        "bot_state.json",
        "notifications.json",
        "users.json"
    )
    
    foreach ($file in $stateFiles) {
        $filePath = Join-Path $dataDir $file
        if (Test-Path $filePath) {
            Copy-Item $filePath -Destination $stateBackupDir -Force
            Write-Status "  $file" -Type "Success"
        }
    }
    
    # Backup de dados de bots
    $botsDataDir = Join-Path $dataDir "bots"
    if (Test-Path $botsDataDir) {
        Copy-Item $botsDataDir -Destination (Join-Path $stateBackupDir "bots") -Recurse -Force
        Write-Status "  Dados dos bots" -Type "Success"
    }
    Write-Host ""
}

# ============================================================================
# COMPRESSÃO
# ============================================================================
if ($Compress) {
    Write-Status "Comprimindo backup..."
    
    $zipFile = "$backupDir.zip"
    
    try {
        Compress-Archive -Path $backupDir -DestinationPath $zipFile -Force
        $zipSize = (Get-Item $zipFile).Length / 1MB
        
        # Remove pasta não comprimida
        Remove-Item $backupDir -Recurse -Force
        
        Write-Status "Backup comprimido: ${zipSize:N2} MB" -Type "Success"
        $finalBackup = $zipFile
    } catch {
        Write-Status "Erro ao comprimir: $_" -Type "Error"
        $finalBackup = $backupDir
    }
} else {
    $finalBackup = $backupDir
}

# ============================================================================
# LIMPEZA DE BACKUPS ANTIGOS
# ============================================================================
Write-Status "Verificando backups antigos..."

$oldBackups = Get-ChildItem $backupRoot -Filter "backup_*" | Where-Object {
    $_.CreationTime -lt (Get-Date).AddDays(-$KeepDays)
}

if ($oldBackups.Count -gt 0) {
    foreach ($old in $oldBackups) {
        Remove-Item $old.FullName -Recurse -Force
    }
    Write-Status "  Removidos $($oldBackups.Count) backup(s) antigo(s)" -Type "Success"
} else {
    Write-Status "  Nenhum backup antigo para remover" -Type "Info"
}

# ============================================================================
# RESUMO
# ============================================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "✅ BACKUP CONCLUÍDO COM SUCESSO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "📁 Arquivo: $finalBackup"
Write-Host "📅 Data: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')"

if (Test-Path $finalBackup) {
    if ($finalBackup -like "*.zip") {
        $size = (Get-Item $finalBackup).Length / 1MB
    } else {
        $size = (Get-ChildItem $finalBackup -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    }
    Write-Host "📦 Tamanho: ${size:N2} MB"
}

Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

# Cria arquivo de manifesto
$manifest = @{
    timestamp = $timestamp
    type = $Type
    destination = $finalBackup
    created = Get-Date -Format "o"
    system = @{
        hostname = $env:COMPUTERNAME
        user = $env:USERNAME
    }
}

$manifestPath = Join-Path $backupRoot "last_backup.json"
$manifest | ConvertTo-Json | Out-File $manifestPath -Encoding UTF8

Write-Status "Manifesto salvo em: $manifestPath" -Type "Info"
