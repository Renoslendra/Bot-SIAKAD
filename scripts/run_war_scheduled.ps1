$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDir "scheduled_war.log"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment tidak ditemukan: $python"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location -LiteralPath $projectRoot

# --lead 0 prevents an early submit when the KRS page is already visible.
"[{0:yyyy-MM-dd HH:mm:ss}] Scheduled war started." -f (Get-Date) |
    Out-File -FilePath $logPath -Encoding utf8
& $python main.py --war --at 08:00 --lead 0 --headless *>> $logPath

exit $LASTEXITCODE
