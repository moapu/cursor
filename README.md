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
| Resize | Gunko-inspired charcoal folded ribbons, double-ended and rotated to match the resize axis |
| Move | Compass |
| Precision | Sogeking's scope |

## Linux

```sh
ln -s "$PWD/OnePiece" ~/.icons/OnePiece
```

Then set the theme to `OnePiece`, e.g. `XCURSOR_THEME=OnePiece` / `hyprctl setcursor OnePiece 24`.
On Linux the pointer, text and grab cursors are drawn 1.5x and the link cursor 2x the nominal size.

## Windows

No background helper, login startup, GlazeWM or Zebar required. All cursors use native Windows `.cur` / `.ani` files.

### Right-click install

1. Download and extract **`OnePiece-Windows.zip`** completely.
2. Open `OnePiece-Windows`, right-click **`install.inf`** → **Install** (under **Show more options** if needed).
3. Approve the administrator prompt. If the cursors do not change immediately, open **Mouse Properties → Pointers**,
   select **One Piece**, and click **Apply**.

This installs into `%WINDIR%\Cursors\OnePiece`. To switch away, select another cursor scheme in Mouse Properties.
The INF installer does not back up your previous selection and is not managed by the PowerShell uninstaller.

### Existing helper installations

Before switching an older helper-based installation to the INF installer, run the updated **`install.ps1`** once
(**Run with PowerShell**), or `src/windows/install.ps1` in a Git checkout. It stops the old helper and removes its
matching login startup entry. Installing an INF alone does not stop an already-running helper.

### Optional administrator-free installer

Windows PowerShell 5.1 users can instead right-click **`install.ps1`** → **Run with PowerShell**. It installs into
`%LOCALAPPDATA%\Cursors\OnePiece`, registers and activates the scheme, then exits. No administrator rights are needed.
Windows may require a trust confirmation for downloaded scripts; only run a package from a source you trust.

Run **`install.ps1`** again to update this installation. It preserves the original pre-installation backup and keeps
old helper file records for cleanup by the uninstaller; nothing restarts or runs in the background.

To undo the PowerShell installation, right-click **`uninstall.ps1`** → **Run with PowerShell** and confirm. It is also
available in `%LOCALAPPDATA%\Cursors\OnePiece`. It restores previous settings and pre-existing files, removes files
introduced by this installation, and preserves later manual edits. It does not remove an INF installation.

### Resize cursors

Four static, double-ended ribbons cover horizontal, vertical and both diagonal resize axes. Opposite edges share a
cursor, as Windows normally expects. The ribbons use the same charcoal shading, dark outline and soft shadow as
Yoru, with a pale ribbon edge for contrast. No per-edge cursor switching or helper is needed.

## Build

Needs `xcursorgen`, `rsvg-convert` (librsvg) and Python with Pillow. With Nix:

```sh
nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
```

This rewrites `OnePiece/`, `OnePiece-Windows/` and `src/preview.png`, and creates the self-contained
`OnePiece-Windows.zip` release package. The ZIP includes `install.inf`, all Windows cursor assets and the optional
PowerShell installer/uninstaller; users do not need Python or the rest of this repository.
