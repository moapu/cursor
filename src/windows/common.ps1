$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$assets = Join-Path $root 'OnePiece-Windows'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'pointer.ani')) { $assets = $PSScriptRoot }
$installDir = Join-Path $env:LOCALAPPDATA 'Cursors\OnePiece'
# Only used to retire an older directional-helper installation.
$legacyDir = Join-Path $installDir 'DirectionalResize'
$legacyExe = Join-Path $legacyDir 'DirectionalResize.exe'
$stateFile = Join-Path $installDir 'install-state.json'
$cursorKey = 'Control Panel\Cursors'
$runKey = 'Software\Microsoft\Windows\CurrentVersion\Run'
$runName = 'OnePieceDirectionalResize'
$roles = [ordered]@{
    Arrow='pointer.ani'; Help='help.cur'; AppStarting='working.ani'; Wait='busy.ani'; Crosshair='precision.cur'
    IBeam='text.cur'; NWPen='handwriting.cur'; No='unavailable.ani'; SizeNS='vert.cur'; SizeWE='horz.cur'
    SizeNWSE='dgn1.cur'; SizeNESW='dgn2.cur'; SizeAll='move.cur'; UpArrow='alternate.cur'; Hand='link.cur'
    Pin='pin.ani'; Person='person.cur'
}
$names = @('') + @($roles.Keys)

function Stop-LegacyHelper {
    $running = @(Get-Process -Name DirectionalResize -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $legacyExe })
    if (-not $running.Count) { return }
    $signal = [Threading.EventWaitHandle]::OpenExisting('Local\OnePiece.DirectionalResize.Stop')
    try { $signal.Set() | Out-Null } finally { $signal.Dispose() }
    foreach ($process in $running) {
        if (-not $process.WaitForExit(5000)) { throw 'Close DirectionalResize from its tray menu before continuing.' }
    }
}
function Test-LegacyStartup([string]$Value) {
    return [Environment]::ExpandEnvironmentVariables($Value).Trim('"') -ieq $legacyExe
}
function Disable-LegacyStartup {
    $values = Read-Values $runKey @($runName)
    if (-not $values.ContainsKey($runName) -or -not (Test-LegacyStartup $values[$runName].data)) { return $false }
    Restore-Values $runKey @($runName) @{}
    return $true
}
function Read-Values([string]$Path, [string[]]$Names) {
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($Path)
    $values = @{}
    if (-not $key) { return $values }
    try {
        foreach ($name in $Names) {
            if ($name -notin $key.GetValueNames()) { continue }
            $values[$name] = @{ data=$key.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames); kind=$key.GetValueKind($name) }
        }
    } finally { $key.Dispose() }
    return $values
}
function Restore-Values([string]$Path, [string[]]$Names, $Values) {
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($Path)
    try {
        foreach ($name in $Names) {
            if ($Values.ContainsKey($name)) { $key.SetValue($name, $Values[$name].data, $Values[$name].kind) }
            else { $key.DeleteValue($name, $false) }
        }
    } finally { $key.Dispose() }
}
function Pack-Values($Values) {
    @($Values.GetEnumerator() | ForEach-Object { @{ name=$_.Key; data=$_.Value.data; kind=[int]$_.Value.kind } })
}
function Unpack-Values($Entries) {
    $values = @{}
    foreach ($entry in $Entries) { $values[[string]$entry.name] = @{ data=$entry.data; kind=[Microsoft.Win32.RegistryValueKind]$entry.kind } }
    return $values
}
function Undo-Values([string]$Path, $Expected, $Previous) {
    $before = Unpack-Values $Previous
    $current = Read-Values $Path @($Expected | ForEach-Object { $_.name })
    foreach ($entry in $Expected) {
        $name = [string]$entry.name
        if ($entry.missing) {
            if ($current.ContainsKey($name)) { continue }
        } elseif (-not $current.ContainsKey($name) -or $current[$name].data -cne $entry.data) { continue }
        Restore-Values $Path @($name) $before
    }
}
function Asset-References {
    foreach ($path in @($cursorKey, "$cursorKey\Schemes")) {
        $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
        if (-not $key) { continue }
        try {
            $selected = if ($path -eq $cursorKey) { @($roles.Keys) } else { @($key.GetValueNames()) }
            foreach ($name in $selected) {
                foreach ($file in ([string]$key.GetValue($name, '', [Microsoft.Win32.RegistryValueOptions]::None)).Split(',')) {
                    if ($file) { [Environment]::ExpandEnvironmentVariables($file) }
                }
            }
        } finally { $key.Dispose() }
    }
}

function Copy-Verified([string]$Source, [string]$Destination) {
    [IO.Directory]::CreateDirectory((Split-Path $Destination -Parent)) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    if ((Get-FileHash -LiteralPath $Source).Hash -ne (Get-FileHash -LiteralPath $Destination).Hash) {
        throw "Copy verification failed: $Destination"
    }
}
function Register-Scheme {
    $paths = @($roles.Values | ForEach-Object { Join-Path $installDir $_ })
    $scheme = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("$cursorKey\Schemes")
    try { $scheme.SetValue('One Piece', ($paths -join ','), [Microsoft.Win32.RegistryValueKind]::ExpandString) }
    finally { $scheme.Dispose() }
    $current = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($cursorKey)
    try {
        foreach ($role in $roles.Keys) {
            $current.SetValue($role, (Join-Path $installDir $roles[$role]), [Microsoft.Win32.RegistryValueKind]::ExpandString)
        }
        $current.SetValue('', 'One Piece', [Microsoft.Win32.RegistryValueKind]::String)
    } finally { $current.Dispose() }
}
function Reload-Cursors {
    # One-shot SPI_SETCURSORS call; no resident process or helper executable.
    if (-not ('OnePieceInstall.Native' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
namespace OnePieceInstall {
    public static class Native {
        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SystemParametersInfoW(uint action, uint param, IntPtr value, uint flags);
        public static void Reload() {
            if (!SystemParametersInfoW(0x57, 0, IntPtr.Zero, 0))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }
    }
}
'@
    }
    [OnePieceInstall.Native]::Reload()
}

function Save-InstallState($State) {
    [IO.File]::WriteAllText($stateFile, ($State | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
}
