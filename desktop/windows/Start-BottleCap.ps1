param(
  [switch] $NoBrowser
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$chatApp = Join-Path $repositoryRoot 'mobile\termux\app.py'
$chatPage = Join-Path $repositoryRoot 'mobile\termux\index.html'
$runtime = Join-Path $env:LOCALAPPDATA 'BottleCapRHAR'
$llamaFolder = Join-Path $runtime 'llama-b11414'
$modelFolder = Join-Path $runtime 'models'
$model = Join-Path $modelFolder 'Qwen3-0.6B-Q4_0.gguf'
$stateFile = Join-Path $runtime 'processes.json'

$llamaRelease = 'b11414'
$llamaArchive = "llama-$llamaRelease-bin-win-cpu-x64.zip"
$llamaUrl = "https://github.com/ggml-org/llama.cpp/releases/download/$llamaRelease/$llamaArchive"
$llamaSha256 = '6d665084c3f5c97230a7dffc2cfd03e500f048899f350808c5969d53e4c77493'
$modelUrl = 'https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_0.gguf'
$modelSha256 = 'da2572f16c06133561ce56accaa822216f2391ef4d37fba427801cd6736417d4'

$llamaPort = 18080
$chatPort = 8765
$llamaProcess = $null
$chatProcess = $null

function Confirm-FileHash([string] $Path, [string] $Expected) {
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Missing file: $Path"
  }
  $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne $Expected) {
    throw "Checksum mismatch: $Path (actual: $actual)"
  }
}

function Download-Verified([string] $Url, [string] $Destination, [string] $Hash) {
  $partial = "$Destination.partial"
  if (Test-Path -LiteralPath $partial) {
    Remove-Item -LiteralPath $partial -Force
  }
  try {
    Write-Host "Downloading: $Url" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $Url -OutFile $partial -UseBasicParsing
    Confirm-FileHash $partial $Hash
    Move-Item -LiteralPath $partial -Destination $Destination -Force
  } finally {
    if (Test-Path -LiteralPath $partial) {
      Remove-Item -LiteralPath $partial -Force
    }
  }
}

function Confirm-PortFree([int] $Port) {
  $listening = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
  if ($listening) {
    throw "Port $Port is occupied. Stop the other service before running BottleCap."
  }
}

function Wait-ForService([string] $Url, [System.Diagnostics.Process] $Process, [int] $Attempts) {
  for ($i = 0; $i -lt $Attempts; $i++) {
    $Process.Refresh()
    if ($Process.HasExited) {
      throw "Service exited with code $($Process.ExitCode): $Url"
    }
    try {
      $null = Invoke-RestMethod -Uri $Url -TimeoutSec 2
      return
    } catch {
      Start-Sleep -Seconds 1
    }
  }
  throw "Service did not become ready: $Url"
}

try {
  if (-not [Environment]::Is64BitOperatingSystem) {
    throw 'Windows x64 is required.'
  }
  if (-not (Test-Path -LiteralPath $chatApp) -or -not (Test-Path -LiteralPath $chatPage)) {
    throw 'BottleCap chat files are missing. Check out the complete GitHub prototype branch.'
  }

  $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
  if (-not $pythonCommand) {
    throw 'Python 3 is not available in PATH. Install Python and reopen PowerShell.'
  }
  $pythonExe = $pythonCommand.Source
  $pythonVersion = & $pythonExe --version 2>&1
  if ($LASTEXITCODE -ne 0 -or "$pythonVersion" -notmatch '^Python 3\.') {
    throw 'Python 3 could not be started. Check your Windows Python installation.'
  }

  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  New-Item -ItemType Directory -Path $runtime, $llamaFolder, $modelFolder -Force | Out-Null

  Confirm-PortFree $llamaPort
  Confirm-PortFree $chatPort

  $llamaExecutable = Get-ChildItem -LiteralPath $llamaFolder -Filter 'llama-server.exe' -Recurse -File |
    Select-Object -First 1
  if (-not $llamaExecutable) {
    $archive = Join-Path $runtime $llamaArchive
    if (Test-Path -LiteralPath $archive) {
      Confirm-FileHash $archive $llamaSha256
    } else {
      Download-Verified $llamaUrl $archive $llamaSha256
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $llamaFolder -Force
    $llamaExecutable = Get-ChildItem -LiteralPath $llamaFolder -Filter 'llama-server.exe' -Recurse -File |
      Select-Object -First 1
    if (-not $llamaExecutable) {
      throw 'The downloaded llama.cpp release did not contain llama-server.exe.'
    }
  }

  if (Test-Path -LiteralPath $model) {
    Confirm-FileHash $model $modelSha256
  } else {
    Download-Verified $modelUrl $model $modelSha256
  }

  $modelArgument = '"' + $model + '"'
  $llamaStdout = Join-Path $runtime 'llama.stdout.log'
  $llamaStderr = Join-Path $runtime 'llama.stderr.log'
  $chatStdout = Join-Path $runtime 'chat.stdout.log'
  $chatStderr = Join-Path $runtime 'chat.stderr.log'

  Write-Host 'Starting Qwen3-0.6B (CPU) on 127.0.0.1:18080...' -ForegroundColor Cyan
  $llamaArgs = @('-m', $modelArgument, '-c', '2048', '-t', '4', '-ngl', '0',
    '--host', '127.0.0.1', '--port', "$llamaPort")
  $llamaLaunch = @{
    FilePath = $llamaExecutable.FullName
    ArgumentList = $llamaArgs
    WorkingDirectory = $llamaExecutable.DirectoryName
    PassThru = $true
    RedirectStandardOutput = $llamaStdout
    RedirectStandardError = $llamaStderr
  }
  $llamaProcess = Start-Process @llamaLaunch
  Wait-ForService "http://127.0.0.1:$llamaPort/health" $llamaProcess 90

  Write-Host 'Starting BottleCap research UI on 127.0.0.1:8765...' -ForegroundColor Cyan
  $env:BOTTLECAP_LLAMA_PORT = "$llamaPort"
  $chatArgs = @('"' + $chatApp + '"', '--port', "$chatPort")
  $chatLaunch = @{
    FilePath = $pythonExe
    ArgumentList = $chatArgs
    WorkingDirectory = (Split-Path -Path $chatApp -Parent)
    PassThru = $true
    RedirectStandardOutput = $chatStdout
    RedirectStandardError = $chatStderr
  }
  $chatProcess = Start-Process @chatLaunch
  Wait-ForService "http://127.0.0.1:$chatPort/health" $chatProcess 20

  [pscustomobject]@{
    llamaPid = $llamaProcess.Id
    chatPid = $chatProcess.Id
    llamaExe = $llamaExecutable.FullName
    appPath = $chatApp
    llamaRelease = $llamaRelease
    llamaSha256 = $llamaSha256
    modelSha256 = $modelSha256
    modelPath = $model
    runtime = 'llama.cpp / Q4_0 / CPU'
    startedUtc = [DateTime]::UtcNow.ToString('o')
  } | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

  Write-Host ''
  Write-Host 'BottleCap RHAR is running: http://127.0.0.1:8765' -ForegroundColor Green
  Write-Host 'Stop it with .\desktop\windows\Stop-BottleCap.ps1'
  if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$chatPort"
  }
} catch {
  Write-Host "BottleCap startup failed: $($_.Exception.Message)" -ForegroundColor Red
  if ($chatProcess) {
    Stop-Process -Id $chatProcess.Id -ErrorAction SilentlyContinue
  }
  if ($llamaProcess) {
    Stop-Process -Id $llamaProcess.Id -ErrorAction SilentlyContinue
  }
  if (Test-Path -LiteralPath $stateFile) {
    Remove-Item -LiteralPath $stateFile -Force
  }
  Write-Host "Logs, if available: $runtime" -ForegroundColor Yellow
  exit 1
}
