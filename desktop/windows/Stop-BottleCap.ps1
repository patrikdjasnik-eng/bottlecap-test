$ErrorActionPreference = 'Stop'
$stateFile = Join-Path (Join-Path $env:LOCALAPPDATA 'BottleCapRHAR') 'processes.json'

if (-not (Test-Path -LiteralPath $stateFile)) {
  Write-Host 'No BottleCap process record found.' -ForegroundColor Yellow
  exit 0
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json

foreach ($kind in @('chat', 'llama')) {
  if ($kind -eq 'chat') {
    $processId = [int] $state.chatPid
    $expected = [string] $state.appPath
  } else {
    $processId = [int] $state.llamaPid
    $expected = [string] $state.llamaExe
  }

  $running = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
  if (-not $running) {
    continue
  }

  $matches = if ($kind -eq 'chat') {
    $running.CommandLine -and $running.CommandLine.Contains($expected)
  } else {
    $running.ExecutablePath -and ($running.ExecutablePath -ieq $expected)
  }

  if ($matches) {
    Stop-Process -Id $processId -ErrorAction Stop
    Write-Host "Stopped BottleCap $kind (PID $processId)." -ForegroundColor Green
  } else {
    Write-Warning "PID $processId no longer belongs to BottleCap $kind. Leaving it untouched."
  }
}

Remove-Item -LiteralPath $stateFile -Force
Write-Host 'BottleCap launch state cleared.'
