# One Piece cursors

One Piece cursor theme for Linux (XCursor) and Windows (`.cur` / `.ani`), generated from one script.

![preview](src/preview.png)

| Cursor | Look |
| --- | --- |
| Normal | Mihawk's Yoru, a shine runs down the blade |
| Working | Yoru coated in Haki |
| Busy | Gear 5 Luffy orbiting in a Haki ring |
| Link | Chibi Luffy pointing |
| Text | Meat on the bone |
| Grab / grabbing | Gear 3 giant hand |
| Not allowed | Jolly Roger shaking "no" |
| Resize | Crocodile's gold hook, rotated to match the resize axis |
| Move | Compass |
| Precision | Sogeking's scope |

## Linux

```sh
ln -s "$PWD/OnePiece" ~/.icons/OnePiece
```

Then set the theme to `OnePiece`, e.g. `XCURSOR_THEME=OnePiece` / `hyprctl setcursor OnePiece 24`.
On Linux the pointer, text and grab cursors are drawn 1.5x and the link cursor 2x the nominal size.

## Windows

Requires Windows x64, Windows PowerShell 5.1 and .NET Framework 4.x. No administrator rights, GlazeWM or Zebar required.

1. Download and extract **`OnePiece-Windows.zip`** completely.
2. Open `OnePiece-Windows`, right-click **`install.ps1`** → **Run with PowerShell**.

The installer copies all cursor assets into `%LOCALAPPDATA%\Cursors\OnePiece`, registers and activates the **One Piece**
scheme, compiles/starts the directional resize helper, and enables its startup at Windows login. No file copying,
Mouse settings changes or follow-up commands are needed. Windows may require a trust confirmation for downloaded
scripts; only run a package from a source you trust.

For a Git checkout, use `src/windows/install.ps1` instead. The generated `install.inf` remains a **static-cursors-only**
legacy option; it does not install the directional helper.

### Updates and uninstall

To update, extract the newer package and run **`install.ps1`** again. It refreshes every managed cursor/helper file at
the same paths, gracefully restarts the helper, and retains the original pre-installation backup.

To undo the installation, right-click **`uninstall.ps1`** → **Run with PowerShell** and confirm. It is also available in
`%LOCALAPPDATA%\Cursors\OnePiece` if you deleted the downloaded package. Uninstall restores the previous cursor/startup
settings and pre-existing files, removes files introduced by this installation, and preserves later manual edits.
It does not remove a separate older installation made through `install.inf`.

### Eight-direction resize hooks

Windows normally shares four resize cursors between opposite edges/corners. The included tray helper places the
wrist outside each dragged edge/corner, with the hook facing into the window. It starts automatically at login,
pauses when another cursor theme is selected, and resumes when One Piece is selected again.

The tray menu provides **Pause**, **Resume**, **Restore current scheme**, and **Exit**. Manual pause lasts until you
resume or restart the helper. Client-area splitters, custom app cursors, and inaccessible/elevated windows retain
the normal four-angle cursors. The helper locks the chosen orientation while dragging.

Advanced options from the repository root:

```powershell
# Skip adding login startup; leave an existing startup preference unchanged.
powershell -NoProfile -File .\src\windows\install.ps1 -NoStartup

# Stop only the runtime helper; keep the installed theme and startup preference.
powershell -NoProfile -File .\src\windows\install.ps1 -Stop
```

Startup can also be disabled through Windows Settings → Apps → Startup → **OnePieceDirectionalResize**.

## Build

Needs `xcursorgen`, `rsvg-convert` (librsvg) and Python with Pillow. With Nix:

```sh
nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
```

This rewrites `OnePiece/`, `OnePiece-Windows/` and `src/preview.png`, and creates the self-contained
`OnePiece-Windows.zip` release package. The ZIP includes the installer, uninstaller, shared PowerShell functions,
existing helper source and all Windows cursor assets; users do not need Python or the rest of this repository.
