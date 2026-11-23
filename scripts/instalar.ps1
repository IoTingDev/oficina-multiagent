# Instalador de la Oficina Virtual IoTing Dev (Windows)
# Uso (PowerShell, en la carpeta del repo):
#   powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
# Instala: ffmpeg, Python (si falta), faster-whisper, Node.js (si falta), Codex CLI,
# y conecta Codex a Claude Code como servidor MCP.

$ErrorActionPreference = "Stop"
function Paso($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Refrescar-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}
function Existe($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Instalar-Winget($id) {
  winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
  Refrescar-Path
}

Paso "ffmpeg"
if (Existe ffmpeg) { Write-Host "ya instalado" } else { Instalar-Winget "Gyan.FFmpeg" }

Paso "Python"
if (Existe python) { python --version } else { Instalar-Winget "Python.Python.3.12" }

Paso "faster-whisper (transcripción local)"
python -m pip install --upgrade pip
python -m pip install -r "$PSScriptRoot\video\requirements.txt"

Paso "Node.js"
if (Existe node) { node --version } else { Instalar-Winget "OpenJS.NodeJS.LTS" }

Paso "Codex CLI"
npm install -g @openai/codex@0.150.0  # fijada: versiones >=0.160 ya no incluyen "codex mcp-server"
Refrescar-Path
codex --version

Paso "Conectar Codex a Claude Code (MCP)"
if (Existe claude) {
  cmd /c "claude mcp remove codex -s user >nul 2>&1"
  claude mcp add codex -s user -- codex mcp-server
  claude mcp list
} else {
  Write-Host "No encontré el comando 'claude' en la terminal. Ejecuta luego:" -ForegroundColor Yellow
  Write-Host "  claude mcp add codex -s user -- codex mcp-server"
}

Paso "Verificación"
ffmpeg -version | Select-Object -First 1
python -c "import faster_whisper; print('faster-whisper', faster_whisper.__version__)"

Write-Host "`nListo. Falta un paso manual: ejecuta  codex login  e inicia sesión con tu cuenta ChatGPT Plus." -ForegroundColor Green
