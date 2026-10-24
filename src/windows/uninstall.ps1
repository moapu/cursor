[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param()

. (Join-Path $PSScriptRoot 'common.ps1')
$mutex = [Threading.Mutex]::new($false, 'Local\OnePiece.CursorInstall')
$locked = $false
try {
    try { $locked = $mutex.WaitOne(10000) }
    catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { throw 'Another cursor installation is running.' }
    if (-not (Test-Path -LiteralPath $stateFile)) {
        Write-Output 'No installation snapshot was found. Nothing was removed.'
        return
    }
    $state = [IO.File]::ReadAllText($stateFile) | ConvertFrom-Json
    if ($state.version -ne 1) { throw 'Unknown installation snapshot; refusing to remove files.' }
    $prefix = [IO.Path]::GetFullPath($installDir).TrimEnd('\') + '\'
    if (-not $state.backupDir -or -not [IO.Path]::GetFullPath($state.backupDir).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Installation backup path is outside the cursor directory.'
    }
    foreach ($file in $state.files) {
        if (-not [IO.Path]::GetFullPath($file.path).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Installation snapshot contains a path outside the cursor directory.'
        }
        if ($file.existed -and (-not [IO.Path]::GetFullPath($file.backup).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath $file.backup -PathType Leaf))) { throw "Missing original file backup: $($file.path)" }
    }
    if (-not $PSCmdlet.ShouldProcess('One Piece cursors and saved installation files', 'Uninstall and restore previous settings')) { return }

    Stop-LegacyHelper
    # Do not overwrite settings the user changed after installation.
    Undo-Values $cursorKey $state.expected.cursors $state.original.cursors
    Undo-Values "$cursorKey\Schemes" $state.expected.scheme $state.original.scheme
    $previousRun = @($state.original.run | Where-Object { -not (Test-LegacyStartup $_.data) })
    Undo-Values $runKey $state.expected.run $previousRun
    $references = @(Asset-References)
    $preserved = $false
    foreach ($file in $state.files) {
        $exists = Test-Path -LiteralPath $file.path
        if (-not $file.existed -and $file.path -in $references) {
            Write-Warning "Preserving a cursor file still referenced by another selection/scheme: $($file.path)"
            $preserved = $true
            continue
        }
        if ($exists -and (Get-FileHash -LiteralPath $file.path).Hash -ne $file.hash) {
            Write-Warning "Preserving a file modified after installation: $($file.path)"
            $preserved = $true
            continue
        }
        if ($file.existed) { Copy-Verified $file.backup $file.path }
        elseif ($exists) { Remove-Item -LiteralPath $file.path -Force }
    }
    Reload-Cursors
    Remove-Item -LiteralPath $stateFile -Force
    if ($preserved) { Write-Warning "Original file backups remain in $($state.backupDir)" }
    else {
        foreach ($file in $state.files) {
            if ($file.existed) { Remove-Item -LiteralPath $file.backup -Force }
        }
        if ($state.backupDir -and (Test-Path -LiteralPath $state.backupDir) -and -not @(Get-ChildItem -LiteralPath $state.backupDir -Force).Count) {
            Remove-Item -LiteralPath $state.backupDir -Force
        }
    }
    foreach ($directory in @($legacyDir, $installDir)) {
        if ((Test-Path -LiteralPath $directory) -and -not @(Get-ChildItem -LiteralPath $directory -Force).Count) {
            Remove-Item -LiteralPath $directory -Force
        }
    }
    Write-Output 'Installation undone. Previous cursor/startup settings and pre-existing files were restored.'
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
