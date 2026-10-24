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

Windows uses native `.cur` / `.ani` files. No background process, PowerShell scripts or ZIP required.

1. In your checkout, open **`OnePiece-Windows`**, right-click **`install.inf`** → **Install**
   (under **Show more options** if needed).
2. Approve the administrator prompt.
3. Open **Mouse Properties → Pointers**, select **One Piece**, and click **Apply**.

Files install into `%WINDIR%\Cursors\OnePiece`. To update, install the INF again. To switch away, select another
cursor scheme in Mouse Properties; the installer does not back up your previous selection.

If you previously installed the directional helper, exit it from its tray menu and disable
**OnePieceDirectionalResize** in **Windows Settings → Apps → Startup** once. The INF does not stop an old helper.

### Resize cursors

Four static, double-ended ribbons cover horizontal, vertical and both diagonal resize axes. Opposite edges share a
cursor, as Windows normally expects. The ribbons use the same charcoal shading, dark outline and soft shadow as
Yoru, with a pale ribbon edge for contrast. No per-edge cursor switching or helper is needed.

## Build

Needs `xcursorgen`, `rsvg-convert` (librsvg) and Python with Pillow. With Nix:

```sh
nix shell --impure --expr 'with builtins.getFlake "nixpkgs"; with legacyPackages.${builtins.currentSystem}; [ xcursorgen librsvg (python3.withPackages (p: [ p.pillow ])) ]' -c python3 src/build.py
```

This regenerates `OnePiece/`, `OnePiece-Windows/` (including `install.inf`) and `src/preview.png`.
The generated themes are ready to install; Python and the build tools are not needed for installation.
