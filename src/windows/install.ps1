param([switch]$Startup, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$target = Join-Path $env:LOCALAPPDATA 'Cursors\OnePiece\DirectionalResize'
$exe = Join-Path $target 'DirectionalResize.exe'
function Stop-Helper([string]$Path) {
    $running = @(Get-Process -Name DirectionalResize -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Path })
    if (-not $running.Count) { return }
    $signal = [Threading.EventWaitHandle]::OpenExisting('Local\OnePiece.DirectionalResize.Stop')
    try { $signal.Set() | Out-Null } finally { $signal.Dispose() }
    foreach ($process in $running) {
        if (-not $process.WaitForExit(5000)) { throw 'Close DirectionalResize from its tray menu before reinstalling.' }
    }
}
function Invoke-Helper([string]$Path, [string]$Argument, [string]$Failure) {
    $process = Start-Process -FilePath $Path -ArgumentList $Argument -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw $Failure }
}
Stop-Helper $exe
if ($Stop) {
    if (Test-Path $exe) { Invoke-Helper $exe '--restore' 'The normal cursor scheme could not be restored.' }
    Write-Output 'Directional resize stopped; the normal cursor scheme is restored.'
    return
}

$compiler = Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) 'csc.exe'
if (-not (Test-Path $compiler)) { throw 'The .NET Framework C# compiler was not found.' }
$assets = Join-Path $root 'OnePiece-Windows'
$directions = @('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw')
foreach ($direction in $directions) {
    if (-not (Test-Path (Join-Path $assets "resize-$direction.cur"))) {
        throw 'Build the eight directional cursor assets with src/build.py first.'
    }
}
$current = Get-ItemProperty 'HKCU:\Control Panel\Cursors'
foreach ($role in @('SizeNS', 'SizeWE', 'SizeNWSE', 'SizeNESW')) {
    $path = [Environment]::ExpandEnvironmentVariables($current.$role)
    if (-not $path -or (Split-Path (Split-Path $path -Parent) -Leaf) -ne 'OnePiece') {
        throw 'Select the One Piece cursor scheme before starting the directional helper.'
    }
}
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($direction in $directions) {
    $file = "resize-$direction.cur"
    $source = Join-Path $assets $file
    $destination = Join-Path $target $file
    $hash = (Get-FileHash $source).Hash
    if ((Test-Path $destination) -and (Get-FileHash $destination).Hash -eq $hash) { continue }
    Copy-Item $source $destination -Force
    if ((Get-FileHash $destination).Hash -ne $hash) {
        throw "Copy verification failed: $file"
    }
}
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "/out:$exe" (Join-Path $PSScriptRoot 'DirectionalResize.cs')
if ($LASTEXITCODE -ne 0) { throw 'Directional resize helper compilation failed.' }
Invoke-Helper $exe '--self-test' 'Directional resize helper self-test failed.'
if ($Startup) {
    New-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'OnePieceDirectionalResize' -PropertyType String -Value ('"' + $exe + '"') -Force | Out-Null
}
$process = Start-Process -FilePath $exe -PassThru
Start-Sleep -Milliseconds 500
$process.Refresh()
if ($process.HasExited) { throw 'Directional resize helper exited during startup.' }
Write-Output "Eight-direction resize enabled. PID: $($process.Id)"
Write-Output 'Tray menu: Pause / Resume / Exit (restores the normal scheme).'
if ($Startup) { Write-Output 'Enabled automatic startup for this Windows user.' }
