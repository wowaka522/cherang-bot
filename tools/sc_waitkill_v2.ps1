param(
  [Parameter(Mandatory=$true)][string]$Exe,
  [Parameter(Mandatory=$true)][string]$GamePath,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][string]$LogBase,
  [Parameter(Mandatory=$true)][string]$Lang,
  [Parameter(Mandatory=$true)][string[]]$Sheets,
  [Parameter(Mandatory=$true)][string[]]$ExpectedCsv,
  [int]$TimeoutMinutes = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-Stable([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $a = (Get-Item -LiteralPath $Path).Length
  Start-Sleep -Milliseconds 600
  $b = (Get-Item -LiteralPath $Path).Length
  return ($a -eq $b)
}

if ([string]::IsNullOrWhiteSpace($OutDir)) { Write-Host "OutDir is empty"; exit 98 }
if (-not (Test-Path -LiteralPath $GamePath)) { Write-Host "Need data! The path '$GamePath' doesn't exist."; exit 97 }

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$logOut = $LogBase
$logErr = "$LogBase.err"

# Build SaintCoinach args safely as an array (no quoting issues)
$args = @(
  $GamePath,
  '--no-update',
  '--lang', $Lang,
  '--out',  $OutDir,
  '--exd'
) + $Sheets

$p = Start-Process -FilePath $Exe -ArgumentList $args -PassThru -NoNewWindow `
  -RedirectStandardOutput $logOut -RedirectStandardError $logErr

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
$ok = $false

while ((Get-Date) -lt $deadline) {
  $ok = $true
  foreach ($f in $ExpectedCsv) {
    $full = Join-Path $OutDir $f
    if (-not (Test-Stable $full)) { $ok = $false; break }
  }
  if ($ok) { break }
  Start-Sleep -Seconds 1
}

if (-not $ok) {
  try { if (-not $p.HasExited) { $p.Kill() } } catch {}
  Write-Host "CSV not ready within timeout. See logs: $logOut / $logErr"
  exit 1
}

# Kill if it's stuck at 'Press any key...'
try { if (-not $p.HasExited) { $p.Kill() } } catch {}

exit 0
