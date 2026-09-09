$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $projectRoot '.data'
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$vitePath = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'

if (!(Test-Path -LiteralPath $pythonPath) -or !(Test-Path -LiteralPath $vitePath)) {
    throw 'Install the README prerequisites first: npm ci and the Python virtual environment.'
}
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null

function Existing-Listener([int]$Port, [string]$ExpectedCommand) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (!$listener) { return $null }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    # A Windows venv may use a base-Python child; its still-running parent owns
    # the project-specific venv path. Check both rather than trusting a PID file.
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)" -ErrorAction SilentlyContinue
    $commands = (($process.CommandLine, $parent.CommandLine) -join ' ').Replace('/', '\')
    $isProject = $commands.IndexOf($projectRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
    if (!$process.CommandLine -or !$isProject -or !$process.CommandLine.Contains($ExpectedCommand)) {
        throw "Port $Port belongs to another or unrecognized process. Nothing was stopped. Resolve that port conflict before restarting this workspace."
    }
    return $listener.OwningProcess
}

Push-Location $projectRoot
try {
    # This helper always starts a loopback-only preview with paid AI disabled.
    $env:SH_ENV = 'development'
    $env:SH_ORIGIN = 'http://127.0.0.1:5180'
    $env:SH_DATA_DIR = $runtimePath
    $env:SH_AI_ENABLED = '0'
    if (!(Test-Path -LiteralPath (Join-Path $runtimePath 'preview-login.json'))) {
        & $pythonPath -m server.manage local-preview
        if ($LASTEXITCODE -ne 0) { throw 'Preview account initialization failed.' }
    }
    $apiProcessId = Existing-Listener 8080 'server.main:app'
    $webProcessId = Existing-Listener 5180 'vite'
    if (!$apiProcessId) {
        $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn server.main:app --host 127.0.0.1 --port 8080' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'api.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'api.stderr.log') -PassThru
        $apiProcessId = $apiProcess.Id
    }
    if (!$webProcessId) {
        $nodePath = (Get-Command node.exe).Source
        $webProcess = Start-Process -FilePath $nodePath -ArgumentList @(('"{0}"' -f $vitePath), '--host', '127.0.0.1', '--port', '5180', '--strictPort') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'web.stdout.log') -RedirectStandardError (Join-Path $runtimePath 'web.stderr.log') -PassThru
        $webProcessId = $webProcess.Id
    }
    @{ api = $apiProcessId; web = $webProcessId } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'processes.json')
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:5180/api/health' -TimeoutSec 2
            $page = Invoke-WebRequest 'http://127.0.0.1:5180/' -UseBasicParsing -TimeoutSec 2
            if ($health.status -eq 'ok' -and $page.Content.Contains('Sausage Health')) { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$ready) { throw 'The preview did not become ready. Check the API and web logs in .data.' }
    Write-Output 'Sausage Health is ready: http://127.0.0.1:5180/'
    Write-Output 'Existing records were preserved. The local login is in .data/preview-login.json (never commit this file).'
} finally {
    Pop-Location
}
