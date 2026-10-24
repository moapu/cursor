[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
$mutex = [Threading.Mutex]::new($false, 'Local\OnePiece.CursorInstall')
$locked = $false
$stage = $null
$keepStage = $false
$runRemoved = $false
try {
    try { $locked = $mutex.WaitOne(10000) }
    catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another cursor installation is running.' }
    foreach ($file in @($roles.Values)) {
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
    $before = Read-Values $cursorKey $names
    $beforeScheme = Read-Values "$cursorKey\Schemes" @('One Piece')
    $beforeRun = Read-Values $runKey @($runName)
    $beforeState = if ($existing) { [IO.File]::ReadAllText($stateFile) } else { $null }
    if (-not $state) {
        $state = @{ version=1; files=@(); backupDir=(Join-Path $installDir ('.previous-' + [Guid]::NewGuid().ToString('N'))); expected=@{ cursors=@(); scheme=@(); run=@() }; original=@{
            cursors=@(Pack-Values $before); scheme=@(Pack-Values $beforeScheme); run=@(Pack-Values $beforeRun)
        } }
    }
    $previousDir = $state.backupDir
    $prefix = [IO.Path]::GetFullPath($installDir).TrimEnd('\') + '\'
    if (-not $previousDir -or -not [IO.Path]::GetFullPath($previousDir).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Installation backup path is outside the cursor directory.'
    }
    $stage = Join-Path $installDir ('.install-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($stage) | Out-Null
    $copied = @()
    try {
        Stop-LegacyHelper
        $copies = @($roles.Values | ForEach-Object { @{ source=(Join-Path $assets $_); destination=(Join-Path $installDir $_) } })
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
        # Updates preserve the original pre-installation snapshot, including legacy file records.
        $desired = @{}
        foreach ($role in $roles.Keys) { $desired[$role] = @{ data=(Join-Path $installDir $roles[$role]); kind=[Microsoft.Win32.RegistryValueKind]::ExpandString } }
        $desired[''] = @{ data='One Piece'; kind=[Microsoft.Win32.RegistryValueKind]::String }
        $state.expected.cursors = @(Pack-Values $desired)
        $state.expected.scheme = @(@{ name='One Piece'; data=(@($roles.Values | ForEach-Object { Join-Path $installDir $_ }) -join ','); kind=2 })
        $state.expected.run = @($state.expected.run | Where-Object { $_.missing })
        $runRemoved = Disable-LegacyStartup
        if ($runRemoved) { $state.expected.run = @(@{ name=$runName; missing=$true }) }
        Save-InstallState $state
        Register-Scheme
        Reload-Cursors
    } catch {
        $failure = $_
        try {
            [Array]::Reverse($copied)
            foreach ($copy in $copied) {
                if ($copy.exists) { Copy-Verified $copy.backup $copy.destination }
                elseif (Test-Path -LiteralPath $copy.destination) { Remove-Item -LiteralPath $copy.destination -Force }
            }
            Restore-Values $cursorKey $names $before
            Restore-Values "$cursorKey\Schemes" @('One Piece') $beforeScheme
            if ($runRemoved) { Restore-Values $runKey @($runName) $beforeRun }
            if ($existing) { [IO.File]::WriteAllText($stateFile, $beforeState, [Text.UTF8Encoding]::new($false)) }
            elseif (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile -Force }
            Reload-Cursors
        } catch {
            $keepStage = $true
            Write-Warning "Rollback failed. Recovery files remain in $stage"
        }
        throw $failure
    }
    Write-Output 'One Piece cursors installed and activated. No background helper or login startup required.'
    if ($runRemoved) { Write-Output 'The older directional helper startup entry was removed.' }
    Write-Output "To undo this installation, run $installDir\uninstall.ps1"
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($stage -and -not $keepStage -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage -Recurse -Force }
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
