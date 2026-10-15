$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $repoRoot ".run\server.pid"
$serverCommandPattern = 'uvicorn(?:\.exe)?["\s]+backend\.main:app'

if (-not (Test-Path $pidFile)) {
    Write-Output "No server PID file found; server is not running."
    return
}

$serverPid = [int](Get-Content $pidFile -Raw)
$server = Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid"
if ($null -eq $server) {
    Remove-Item $pidFile
    Write-Output "Removed stale server PID file."
    return
}

if ($server.CommandLine -notmatch $serverCommandPattern) {
    throw "PID $serverPid is not the Kanban Studio server; refusing to stop it."
}

Stop-Process -Id $serverPid
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $server = Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid"
    if ($null -eq $server) {
        Remove-Item $pidFile
        Write-Output "Server stopped."
        return
    }
    Start-Sleep -Seconds 1
}

throw "Server process $serverPid did not stop within 30 seconds."
