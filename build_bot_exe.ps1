# Script para empacotar o bot principal do Virtus em um executável
# Requisitos: PyInstaller instalado no ambiente Python
# Execute este script na raiz do projeto

# Caminho do main.py do bot
$mainPy = "C:\Users\Administrator\Desktop\Virtus\brain\main.py"

# Caminho de saída para o executável
$outDir = "C:\Users\Administrator\Desktop\Virtus\dist_bot"

# Garante que a pasta de saída existe
if (!(Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

# Comando do PyInstaller
$pyinstallerCmd = "pyinstaller --onefile --distpath '$outDir' --workpath '$outDir\build' --specpath '$outDir' '$mainPy'"

# Executa o comando
Invoke-Expression $pyinstallerCmd

Write-Host "Executável gerado em: $outDir"