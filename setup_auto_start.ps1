# Script para criar atalhos de inicialização automática do backend e frontend do Virtus
# Salve este arquivo como setup_auto_start.ps1 e execute como Administrador

# Caminhos dos scripts/backend/frontend
$backendBat = "C:\Users\Administrator\Desktop\Virtus\brain\dashboard\backend\start_backend.bat"
$frontendBat = "C:\Users\Administrator\Desktop\Virtus\brain\dashboard\frontend\start_frontend.bat"

# Pasta de inicialização do usuário atual
$startupFolder = [Environment]::GetFolderPath('Startup')

# Criar atalho para o backend
$backendShortcut = Join-Path $startupFolder "Virtus_Backend.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($backendShortcut)
$shortcut.TargetPath = $backendBat
$shortcut.WorkingDirectory = (Split-Path $backendBat)
$shortcut.Save()

# Criar atalho para o frontend (se existir o script)
if (Test-Path $frontendBat) {
    $frontendShortcut = Join-Path $startupFolder "Virtus_Frontend.lnk"
    $shortcut2 = $WshShell.CreateShortcut($frontendShortcut)
    $shortcut2.TargetPath = $frontendBat
    $shortcut2.WorkingDirectory = (Split-Path $frontendBat)
    $shortcut2.Save()
}

Write-Host "Atalhos criados na inicialização do Windows. O backend e o frontend do Virtus iniciarão automaticamente ao ligar o computador."