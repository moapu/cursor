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

Copy `OnePiece-Windows` to the PC, right-click `install.inf` → **Install**, then pick the **One Piece** scheme in
Mouse settings → Pointers.

### Eight-direction resize hooks

Windows normally shares four resize cursors between opposite edges/corners. The optional tray helper places the
wrist outside each dragged edge/corner, with the hook facing into the window. Install and start it without administrator rights:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\src\windows\install.ps1
```

It requires Windows x64 and .NET Framework 4.x, installs under `%LOCALAPPDATA%\Cursors\OnePiece\DirectionalResize`,
and leaves your saved scheme unchanged. Add `-Startup` to opt into starting it at login; startup is off by default.
The tray menu provides **Pause**, **Resume**, **Restore current scheme**, and **Exit**.

Client-area splitters, custom app cursors, and inaccessible/elevated windows retain the normal four-angle cursors.
The helper locks the chosen orientation while dragging and pauses when you switch cursor schemes.
If it is forcibly terminated, restore the normal scheme with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\src\windows\install.ps1 -Stop
```

The installer checks all eight assets and tests native replacement/restoration before starting the helper.

## Build

Needs `xcursorgen`, `rsvg-convert` (librsvg) and Python with Pillow. With Nix:

```sh
nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
```

This rewrites `OnePiece/`, `OnePiece-Windows/` and `src/preview.png`.
