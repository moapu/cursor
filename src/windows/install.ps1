[CmdletBinding()]
param([switch]$Startup, [switch]$NoStartup, [switch]$Stop)

. (Join-Path $PSScriptRoot 'common.ps1')
$mutex = [Threading.Mutex]::new($false, 'Local\OnePiece.CursorInstall')
$locked = $false
$stage = $null
$keepStage = $false
try {
    try { $locked = $mutex.WaitOne(10000) }
    catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another cursor installation is running.' }
    if ($Stop) {
        Stop-Helper
        if (Test-Path -LiteralPath $exe) { Invoke-Helper $exe '--restore' }
        Write-Output 'Directional resize stopped; the normal cursor scheme is restored.'
        return
    }
    if ($Startup -and $NoStartup) { throw 'Choose either -Startup or -NoStartup, not both.' }
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'This installer requires 64-bit Windows.' }
    $compiler = Join-Path ([Runtime.InteropServices.RuntimeEnvironment]::GetRuntimeDirectory()) 'csc.exe'
    $source = Join-Path $PSScriptRoot 'DirectionalResize.cs'
    if (-not (Test-Path -LiteralPath $compiler) -or -not (Test-Path -LiteralPath $source)) {
        throw 'The complete cursor package and .NET Framework 4.x are required.'
    }
    $hookFiles = @('n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw' | ForEach-Object { "resize-$_.cur" })
    foreach ($file in @($roles.Values) + $hookFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $assets $file) -PathType Leaf)) {
            throw "Extract the complete OnePiece-Windows.zip first. Missing asset: $file"
        }
    }
    foreach ($file in @('uninstall.ps1', 'common.ps1')) {
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $file))) { throw "Incomplete installer: $file" }
    }
    $existing = Test-Path -LiteralPath $stateFile
    $state = if ($existing) { [IO.File]::ReadAllText($stateFile) | ConvertFrom-Json } else { $null }
    if ($existing -and $state.version -ne 1) { throw 'Unknown installation state; refusing to overwrite its backup.' }

    $stage = Join-Path $installDir ('.install-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    foreach ($file in $hookFiles) { Copy-Verified (Join-Path $assets $file) (Join-Path $stage $file) }
    $stagedExe = Join-Path $stage 'DirectionalResize.exe'
    & $compiler /nologo /target:winexe /platform:x64 /optimize+ /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "/out:$stagedExe" $source
    if ($LASTEXITCODE -ne 0) { throw 'Directional resize helper compilation failed.' }

    $wasRunning = @(Running-Helper).Count -gt 0
    $before = Read-Values $cursorKey $names
    $beforeScheme = Read-Values "$cursorKey\Schemes" @('One Piece')
    $beforeRun = Read-Values $runKey @($runName)
    $beforeState = if ($existing) { [IO.File]::ReadAllText($stateFile) } else { $null }
    if (-not $state) {
        $state = @{ version=1; files=@(); backupDir=(Join-Path $installDir ('.previous-' + [Guid]::NewGuid().ToString('N'))); expected=@{ cursors=@(); scheme=@(); run=@() }; original=@{
            cursors=@(Pack-Values $before); scheme=@(Pack-Values $beforeScheme); run=@(Pack-Values $beforeRun); helperRunning=$wasRunning
        } }
    }
    $previousDir = $state.backupDir
    if (-not $previousDir) { throw 'Installation backup metadata is missing.' }
    $copied = @()
    Stop-Helper
    try {
        Invoke-Helper $stagedExe '--self-test'
        $copies = @($roles.Values | ForEach-Object { @{ source=(Join-Path $assets $_); destination=(Join-Path $installDir $_) } })
        $copies += @($hookFiles | ForEach-Object { @{ source=(Join-Path $stage $_); destination=(Join-Path $target $_) } })
        $copies += @{ source=$stagedExe; destination=$exe }
        $copies += @('uninstall.ps1', 'common.ps1' | ForEach-Object { @{ source=(Join-Path $PSScriptRoot $_); destination=(Join-Path $installDir $_) } })
        foreach ($copy in $copies) {
            $backup = Join-Path $stage ("backup\$($copied.Count)")
            $exists = Test-Path -LiteralPath $copy.destination
            if ($exists) { Copy-Verified $copy.destination $backup }
            $record = @($state.files | Where-Object { $_.path -eq $copy.destination }) | Select-Object -First 1
            if (-not $record) {
                $saved = Join-Path $previousDir ([string]@($state.files).Count)
                if ($exists) { Copy-Verified $copy.destination $saved }
                $record = @{ path=$copy.destination; existed=$exists; backup=$saved; hash='' }
                $state.files += $record
            }
            $copied += @{ destination=$copy.destination; backup=$backup; exists=$exists }
            Copy-Verified $copy.source $copy.destination
            $record.hash = (Get-FileHash -LiteralPath $copy.destination).Hash
        }
        # Persist the original snapshot before activation; updates never replace that baseline.
        $desired = @{}
        foreach ($role in $roles.Keys) { $desired[$role] = @{ data=(Join-Path $installDir $roles[$role]); kind=[Microsoft.Win32.RegistryValueKind]::ExpandString } }
        $desired[''] = @{ data='One Piece'; kind=[Microsoft.Win32.RegistryValueKind]::String }
        $state.expected.cursors = @(Pack-Values $desired)
        $state.expected.scheme = @(@{ name='One Piece'; data=(@($roles.Values | ForEach-Object { Join-Path $installDir $_ }) -join ','); kind=2 })
        if (-not $NoStartup) { $state.expected.run = @(@{ name=$runName; data=('"' + $exe + '"'); kind=1 }) }
        Save-InstallState $state
        Register-Scheme
        Invoke-Helper $exe '--restore'
        if (-not $NoStartup) {
            $run = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($runKey)
            try { $run.SetValue($runName, ('"' + $exe + '"'), [Microsoft.Win32.RegistryValueKind]::String) }
            finally { $run.Dispose() }
        }
        $pidInstalled = Start-Helper
    } catch {
        $failure = $_
        try {
            Stop-Helper
            [Array]::Reverse($copied)
            foreach ($copy in $copied) {
                if ($copy.exists) { Copy-Verified $copy.backup $copy.destination }
                elseif (Test-Path -LiteralPath $copy.destination) { Remove-Item -LiteralPath $copy.destination -Force }
            }
            Restore-Values $cursorKey $names $before
            Restore-Values "$cursorKey\Schemes" @('One Piece') $beforeScheme
            Restore-Values $runKey @($runName) $beforeRun
            if ($existing) { [IO.File]::WriteAllText($stateFile, $beforeState, [Text.UTF8Encoding]::new($false)) }
            elseif (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile -Force }
            if (Test-Path -LiteralPath $exe) { Invoke-Helper $exe '--restore' }
            if ($wasRunning) { Start-Helper | Out-Null }
        } catch {
            $keepStage = $true
            Write-Warning "Rollback failed. Recovery files remain in $stage"
        }
        throw $failure
    }
    Write-Output "One Piece cursors installed and activated. Directional helper PID: $pidInstalled"
    Write-Output 'No GlazeWM or Zebar required. Tray menu: Pause / Resume / Exit.'
    Write-Output "To undo this installation, run $installDir\uninstall.ps1"
    if (-not $NoStartup) { Write-Output 'The helper starts automatically at Windows login.' }
    else { Write-Output 'Startup registration skipped; any existing startup preference is unchanged.' }
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($stage -and -not $keepStage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Recurse -Force }
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
