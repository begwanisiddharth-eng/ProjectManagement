$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$runDir = Join-Path $repoRoot ".run"
$pidFile = Join-Path $runDir "server.pid"
$envFile = Join-Path $repoRoot ".env"
$stdoutLog = Join-Path $runDir "server.out.log"
$stderrLog = Join-Path $runDir "server.err.log"
$healthUrl = "http://127.0.0.1:8000/api/health"
$serverCommandPattern = 'uvicorn(?:\.exe)?["\s]+backend\.main:app'

if (-not (Test-Path (Join-Path $repoRoot "frontend\out\index.html"))) {
    throw "Static frontend build not found. Run 'npm run build' from frontend/ first."
}

New-Item -ItemType Directory -Force -Path $runDir | Out-Null

if (Test-Path $pidFile) {
    $existingPid = [int](Get-Content $pidFile -Raw)
    $existingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $existingPid"
    if ($null -ne $existingProcess -and $existingProcess.CommandLine -match $serverCommandPattern) {
        try {
            $null = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            Write-Output "Server is already running (PID $existingPid)."
            return
        } catch {
            throw "Server process $existingPid exists but the health endpoint is not responding."
        }
    }
    if ($null -ne $existingProcess) {
        throw "PID $existingPid is in use by another process; refusing to remove it or start another server."
    }
    Remove-Item $pidFile
}

$existingListener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($null -ne $existingListener) {
    throw "Port 8000 is already in use; refusing to start a second server."
}

$arguments = @(
    "run",
    "--project",
    "`"$backendDir`""
)
if (Test-Path $envFile) {
    $arguments += @("--env-file", ".env")
}
$arguments += @("uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000")
$server = Start-Process -FilePath "uv" -ArgumentList $arguments -WorkingDirectory $repoRoot `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru -WindowStyle Hidden
$server.Id | Set-Content -Path $pidFile

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $healthy = $false
    try {
        $null = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        $healthy = $true
    } catch {
        $healthy = $false
    }
    if ($healthy) {
        $listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        $listenerProcess = if ($null -ne $listener) {
            Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)"
        } else {
            $null
        }
        if ($null -eq $listenerProcess -or $listenerProcess.CommandLine -notmatch $serverCommandPattern) {
            throw "Health endpoint responded, but the listener is not the server started by this script."
        }
        $listenerProcess.ProcessId | Set-Content -Path $pidFile
        Write-Output "Server started at $healthUrl (PID $($listenerProcess.ProcessId))."
        return
    }

    $server.Refresh()
    if ($server.HasExited) {
        Remove-Item $pidFile -ErrorAction SilentlyContinue
        $stdout = if (Test-Path $stdoutLog) { Get-Content $stdoutLog -Raw } else { "" }
        $stderr = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw } else { "" }
        throw "Server exited during startup.`n$stdout`n$stderr"
    }
    Start-Sleep -Seconds 1
}

Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match $serverCommandPattern -and
    $_.CommandLine.IndexOf($backendDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
} | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
Remove-Item $pidFile -ErrorAction SilentlyContinue
$stderr = if (Test-Path $stderrLog) { Get-Content $stderrLog -Raw } else { "" }
throw "Server did not become healthy within 30 seconds.`n$stderr"
